"""
Orchestrator Agent

The main coordinator that:
1. Runs data collection agents
2. Runs analysis agents
3. Aggregates signals
4. Makes final trading decisions
5. Sends decisions to execution agents
"""
import anthropic
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional
from sqlalchemy import text
import json

from agents.base_agent import BaseAgent, AgentType, SignalType
from agents.data_collectors.price_collector import PriceCollectorAgent
from agents.analysts.technical_analyst import TechnicalAnalystAgent
from agents.analysts.sentiment_analyst import SentimentAnalystAgent
from config.config import config
from trading.paper_trading_engine import PaperTradingEngine, OrderType, OrderSide, PositionSide


class OrchestratorAgent(BaseAgent):
    """
    Main orchestrator agent that coordinates all trading system activities

    Responsibilities:
    - Run data collection on schedule
    - Trigger analysis when new data is available
    - Aggregate signals from multiple analysts
    - Use Claude AI to make final trading decisions
    - Send execution orders (in paper trading mode for now)
    - Monitor system health
    """

    def __init__(self, enable_sentiment: bool = True):
        super().__init__(
            agent_name="Orchestrator",
            agent_type=AgentType.ORCHESTRATOR,
            version="1.0.0"
        )

        # Initialize sub-agents
        self.price_collector = PriceCollectorAgent()
        self.technical_analyst = TechnicalAnalystAgent()

        # Initialize sentiment analyst (optional - may not have API keys)
        self.sentiment_analyst = None
        if enable_sentiment:
            try:
                self.sentiment_analyst = SentimentAnalystAgent()
                self.logger.info("Sentiment analyst enabled")
            except Exception as e:
                self.logger.warning(f"Sentiment analyst disabled: {e}")

        # Initialize Claude AI client
        self.claude = anthropic.Anthropic(api_key=config.anthropic_api_key)

        # Initialize paper trading engine for portfolio snapshots
        self.paper_trading_engine = PaperTradingEngine(
            initial_capital=config.initial_capital,
            db=self.db
        )

        active_analysts = ["technical"]
        if self.sentiment_analyst:
            active_analysts.append("sentiment")

        # Cache for optimized weights (refreshed periodically)
        self.optimized_weights = None
        self.weights_last_loaded = None

        self.logger.info(f"Orchestrator initialized with analysts: {', '.join(active_analysts)}")

    def run(self) -> Dict[str, Any]:
        """
        Main orchestration cycle

        Returns:
            Dict with execution results
        """
        results = {
            'cycle_start': datetime.now(timezone.utc).isoformat(),
            'steps_completed': [],
            'trading_decisions': [],
            'errors': []
        }

        # Step 1: Collect latest price data
        self.logger.info("Step 1: Collecting price data...")
        try:
            price_result = self.price_collector.execute()
            results['steps_completed'].append('price_collection')
            results['price_collection'] = {
                'success': price_result['success'],
                'candles_collected': price_result.get('candles_collected', 0)
            }
            self.logger.info(
                f"Price collection: {price_result.get('candles_collected', 0)} candles"
            )
        except Exception as e:
            error_msg = f"Price collection failed: {e}"
            self.logger.error(error_msg, exc_info=True)
            results['errors'].append(error_msg)

        # Step 2: Run technical analysis
        self.logger.info("Step 2: Running technical analysis...")
        try:
            analysis_result = self.technical_analyst.execute()
            results['steps_completed'].append('technical_analysis')
            results['technical_analysis'] = {
                'success': analysis_result['success'],
                'pairs_analyzed': analysis_result.get('pairs_analyzed', 0),
                'signals_generated': analysis_result.get('signals_generated', 0),
                'buy_signals': analysis_result.get('buy_signals', 0),
                'sell_signals': analysis_result.get('sell_signals', 0)
            }
            self.logger.info(
                f"Technical analysis: {analysis_result.get('pairs_analyzed', 0)} pairs, "
                f"{analysis_result.get('signals_generated', 0)} signals"
            )
        except Exception as e:
            error_msg = f"Technical analysis failed: {e}"
            self.logger.error(error_msg, exc_info=True)
            results['errors'].append(error_msg)

        # Step 2b: Run sentiment analysis (if enabled)
        if self.sentiment_analyst:
            self.logger.info("Step 2b: Running sentiment analysis...")
            try:
                sentiment_result = self.sentiment_analyst.execute()
                results['steps_completed'].append('sentiment_analysis')
                results['sentiment_analysis'] = {
                    'success': sentiment_result['success'],
                    'symbols_analyzed': sentiment_result.get('symbols_analyzed', 0),
                    'signals_generated': sentiment_result.get('signals_generated', 0),
                    'bullish_signals': sentiment_result.get('bullish_signals', 0),
                    'bearish_signals': sentiment_result.get('bearish_signals', 0)
                }
                self.logger.info(
                    f"Sentiment analysis: {sentiment_result.get('symbols_analyzed', 0)} symbols, "
                    f"{sentiment_result.get('signals_generated', 0)} signals "
                    f"({sentiment_result.get('bullish_signals', 0)} bullish, "
                    f"{sentiment_result.get('bearish_signals', 0)} bearish)"
                )
            except Exception as e:
                error_msg = f"Sentiment analysis failed: {e}"
                self.logger.error(error_msg, exc_info=True)
                results['errors'].append(error_msg)

        # Step 3: Make trading decisions
        self.logger.info("Step 3: Making trading decisions...")
        try:
            decisions = self._make_trading_decisions()
            results['steps_completed'].append('trading_decisions')
            results['trading_decisions'] = decisions
            self.logger.info(f"Made {len(decisions)} trading decisions")
        except Exception as e:
            error_msg = f"Trading decisions failed: {e}"
            self.logger.error(error_msg, exc_info=True)
            results['errors'].append(error_msg)

        # Step 3b: Save portfolio snapshot
        self.logger.info("Step 3b: Saving portfolio snapshot...")
        try:
            self.paper_trading_engine.save_portfolio_snapshot()
            results['steps_completed'].append('portfolio_snapshot')
            self.logger.info("Portfolio snapshot saved")
        except Exception as e:
            error_msg = f"Portfolio snapshot failed: {e}"
            self.logger.error(error_msg, exc_info=True)
            results['errors'].append(error_msg)

        # Step 4: System health check
        self.logger.info("Step 4: System health check...")
        try:
            health = self._check_system_health()
            results['steps_completed'].append('health_check')
            results['system_health'] = health
        except Exception as e:
            error_msg = f"Health check failed: {e}"
            self.logger.error(error_msg, exc_info=True)
            results['errors'].append(error_msg)

        results['cycle_end'] = datetime.now(timezone.utc).isoformat()
        results['success'] = len(results['errors']) == 0

        return results

    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze system state and provide recommendations

        Args:
            data: Input data (optional)

        Returns:
            Dict with system analysis and recommendations
        """
        return {
            'system_health': self._check_system_health(),
            'latest_signals': self._get_latest_signals(),
            'portfolio_status': self._get_portfolio_status()
        }

    def _make_trading_decisions(self) -> List[Dict[str, Any]]:
        """
        Make trading decisions based on aggregated signals

        Uses Claude AI to analyze signals and make intelligent decisions

        Returns:
            List of trading decisions
        """
        decisions = []

        # Get latest signals for each pair
        for symbol in config.trading_pairs:
            try:
                # Get all recent signals for this symbol
                signals = self._get_recent_signals(symbol, hours=1)

                if not signals:
                    self.logger.debug(f"No recent signals for {symbol}")
                    continue

                # Get current market data
                market_data = self._get_market_context(symbol)

                # Make decision based on signals (Claude AI disabled for now)
                decision = self._make_decision_from_signals(symbol, signals, market_data)

                if decision:
                    decisions.append(decision)

                    # Log decision
                    decision_id = self._log_decision(decision)

                    # Execute trading decisions
                    if decision['decision'] == 'BUY' and decision_id:
                        self._execute_buy_decision(decision, decision_id)
                    elif decision['decision'] == 'SELL' and decision_id:
                        self._execute_sell_decision(decision, decision_id)

            except Exception as e:
                self.logger.error(f"Error making decision for {symbol}: {e}", exc_info=True)

        return decisions

    def _get_recent_signals(self, symbol: str, hours: int = 1) -> List[Dict[str, Any]]:
        """
        Get recent signals for a symbol from all agents

        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT' or 'BTC')
            hours: Number of hours to look back

        Returns:
            List of signal dicts, grouped by agent (most recent from each)
        """
        try:
            # Handle both 'BTC/USDT' and 'BTC' formats
            symbol_base = symbol.split('/')[0] if '/' in symbol else symbol

            with self.db.get_session() as session:
                # Get most recent signal from each agent within the time window
                query = text("""
                    WITH ranked_signals AS (
                        SELECT
                            agent_name,
                            signal,
                            confidence,
                            reasoning,
                            metadata,
                            time,
                            ROW_NUMBER() OVER (PARTITION BY agent_name ORDER BY time DESC) as rn
                        FROM agent_signals
                        WHERE (symbol = :symbol OR symbol = :symbol_base)
                            AND time >= NOW() - INTERVAL '1 hour' * :hours
                    )
                    SELECT
                        agent_name,
                        signal,
                        confidence,
                        reasoning,
                        metadata,
                        time
                    FROM ranked_signals
                    WHERE rn = 1
                    ORDER BY time DESC
                """)

                results = session.execute(query, {
                    'symbol': symbol,
                    'symbol_base': symbol_base,
                    'hours': hours
                }).fetchall()

                return [
                    {
                        'agent_name': row[0],
                        'signal': row[1],
                        'confidence': float(row[2]),
                        'reasoning': row[3],
                        'metadata': row[4],
                        'time': row[5].isoformat()
                    }
                    for row in results
                ]

        except Exception as e:
            self.logger.error(f"Error getting recent signals: {e}")
            return []

    def _get_market_context(self, symbol: str) -> Dict[str, Any]:
        """
        Get current market context for a symbol

        Args:
            symbol: Trading pair symbol

        Returns:
            Dict with market context
        """
        context = {
            'symbol': symbol,
            'current_price': None,
            'indicators': None,
            'volume_24h': None
        }

        try:
            # Get latest price
            price_data = self.get_latest_price(symbol)
            if price_data:
                context['current_price'] = price_data['close']
                context['volume_24h'] = price_data.get('volume')

            # Get latest indicators
            with self.db.get_session() as session:
                query = text("""
                    SELECT
                        ema_9, ema_21, ema_50, ema_200,
                        rsi_14, macd, macd_signal,
                        bb_upper, bb_middle, bb_lower,
                        atr
                    FROM technical_indicators
                    WHERE symbol = :symbol
                    ORDER BY time DESC
                    LIMIT 1
                """)

                result = session.execute(query, {'symbol': symbol}).fetchone()

                if result:
                    context['indicators'] = {
                        'ema_9': float(result[0]) if result[0] else None,
                        'ema_21': float(result[1]) if result[1] else None,
                        'ema_50': float(result[2]) if result[2] else None,
                        'ema_200': float(result[3]) if result[3] else None,
                        'rsi_14': float(result[4]) if result[4] else None,
                        'macd': float(result[5]) if result[5] else None,
                        'macd_signal': float(result[6]) if result[6] else None,
                        'bb_upper': float(result[7]) if result[7] else None,
                        'bb_middle': float(result[8]) if result[8] else None,
                        'bb_lower': float(result[9]) if result[9] else None,
                        'atr': float(result[10]) if result[10] else None
                    }

        except Exception as e:
            self.logger.error(f"Error getting market context: {e}")

        return context

    def _make_decision_from_signals(
        self,
        symbol: str,
        signals: List[Dict[str, Any]],
        market_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Make trading decision using multi-agent consensus

        Aggregates signals from multiple analysts with weighted voting:
        - Technical Analyst: 40% weight (for crypto)
        - Sentiment Analyst: 60% weight (for crypto - community-driven markets)

        Args:
            symbol: Trading pair symbol
            signals: List of signals from analysts (one per agent)
            market_data: Current market context

        Returns:
            Trading decision dict with combined reasoning
        """
        if not signals:
            return None

        # Group signals by agent
        agent_signals = {}
        for sig in signals:
            agent_name = sig['agent_name']
            agent_signals[agent_name] = sig

        # Load optimized weights from Weight Optimizer
        # Falls back to static weights if optimization not available
        weights = self._get_agent_weights(symbol)

        # Convert signals to scores and calculate weighted average
        signal_scores = []
        confidence_scores = []
        total_weight = 0

        for agent_name, sig in agent_signals.items():
            # Get weight for this agent (default 0.5 if not defined)
            weight = weights.get(agent_name, 0.5)

            # Convert signal to score (-100 to +100)
            signal_type = sig['signal'].upper()
            if signal_type == 'BUY':
                score = 100
            elif signal_type == 'SELL':
                score = -100
            else:  # HOLD
                score = 0

            # Check if metadata has a strength score
            if sig.get('metadata') and isinstance(sig['metadata'], dict):
                strength = sig['metadata'].get('strength')
                if strength is not None:
                    score = float(strength)  # Use the actual strength score

            # Apply weight
            weighted_score = score * weight
            signal_scores.append(weighted_score)

            # Apply weight to confidence
            confidence_scores.append(sig['confidence'] * weight)
            total_weight += weight

        # Calculate final aggregated score and confidence
        final_score = sum(signal_scores) / max(total_weight, 1)
        final_confidence = sum(confidence_scores) / max(total_weight, 1)

        # Determine decision based on final score
        # Require higher confidence threshold (65%) to reduce noise and improve quality
        MIN_CONFIDENCE_THRESHOLD = 0.65

        if final_score > 50 and final_confidence >= MIN_CONFIDENCE_THRESHOLD:
            decision = 'BUY'
            position_size_pct = min(final_confidence * 0.3, 0.3)  # Max 30%
            stop_loss_pct = 0.05  # 5% stop loss
        elif final_score < -50 and final_confidence >= MIN_CONFIDENCE_THRESHOLD:
            decision = 'SELL'
            position_size_pct = min(final_confidence * 0.3, 0.3)  # Max 30% for SHORT positions
            stop_loss_pct = 0.05  # 5% stop loss for SHORT
        else:
            decision = 'HOLD'
            position_size_pct = 0
            stop_loss_pct = 0

        # Build multi-agent reasoning
        if len(agent_signals) > 1:
            reasoning_parts = [f"Multi-agent consensus ({len(agent_signals)} agents):"]

            for agent_name, sig in agent_signals.items():
                weight = weights.get(agent_name, 0.5)
                weight_pct = int(weight * 100)

                # Extract score from metadata if available
                score_str = ""
                if sig.get('metadata') and isinstance(sig['metadata'], dict):
                    strength = sig['metadata'].get('strength')
                    if strength is not None:
                        score_str = f"Score {strength}/100, "

                reasoning_parts.append(
                    f"- {agent_name} ({weight_pct}% weight): {score_str}{sig['signal'].upper()}"
                )
                reasoning_parts.append(f"  {sig['reasoning']}")

            reasoning_parts.append(f"\nFinal: {int(final_score)}/100 - {decision} decision")
            reasoning = "\n".join(reasoning_parts)
        else:
            # Single agent fallback
            single_sig = list(agent_signals.values())[0]
            reasoning = f"Based on {single_sig['agent_name']} signal: {single_sig['reasoning']}"

        return {
            'symbol': symbol,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'decision': decision,
            'confidence': final_confidence,
            'reasoning': reasoning,
            'position_size_pct': position_size_pct,
            'stop_loss_pct': stop_loss_pct,
            'current_price': market_data.get('current_price'),
            'signals_considered': len(signals),
            'final_score': int(final_score),
            'trading_mode': config.trading_mode
        }

    def _consult_claude_for_decision(
        self,
        symbol: str,
        signals: List[Dict[str, Any]],
        market_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Use Claude AI to make trading decision

        Args:
            symbol: Trading pair symbol
            signals: List of signals from analysts
            market_data: Current market context

        Returns:
            Trading decision dict or None
        """
        try:
            # Prepare prompt for Claude
            prompt = self._build_decision_prompt(symbol, signals, market_data)

            # Call Claude API
            message = self.claude.messages.create(
                model=config.claude_model,
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            # Parse Claude's response
            response_text = message.content[0].text

            # Extract decision from response
            decision = self._parse_claude_decision(symbol, response_text, signals, market_data)

            return decision

        except Exception as e:
            self.logger.error(f"Error consulting Claude for {symbol}: {e}", exc_info=True)
            return None

    def _build_decision_prompt(
        self,
        symbol: str,
        signals: List[Dict[str, Any]],
        market_data: Dict[str, Any]
    ) -> str:
        """
        Build prompt for Claude to make trading decision

        Args:
            symbol: Trading pair symbol
            signals: List of signals
            market_data: Market context

        Returns:
            Prompt string
        """
        current_price = market_data.get('current_price', 'unknown')
        indicators = market_data.get('indicators', {})

        prompt = f"""You are an expert cryptocurrency trading advisor for an autonomous trading system.

TRADING PAIR: {symbol}
CURRENT PRICE: ${current_price}
TRADING MODE: Paper Trading (testing phase)

TECHNICAL INDICATORS:
- RSI: {indicators.get('rsi_14', 'N/A')}
- MACD: {indicators.get('macd', 'N/A')}
- EMA9: {indicators.get('ema_9', 'N/A')}
- EMA21: {indicators.get('ema_21', 'N/A')}
- EMA50: {indicators.get('ema_50', 'N/A')}
- Bollinger Bands: Upper={indicators.get('bb_upper', 'N/A')}, Middle={indicators.get('bb_middle', 'N/A')}, Lower={indicators.get('bb_lower', 'N/A')}
- ATR: {indicators.get('atr', 'N/A')}

ANALYST SIGNALS:
"""

        for signal in signals:
            prompt += f"\n- {signal['agent_name']}: {signal['signal'].upper()} (confidence: {signal['confidence']:.0%})"
            prompt += f"\n  Reasoning: {signal['reasoning']}"

        prompt += """

Based on the technical indicators and analyst signals, should the system:
1. BUY - Open a long position
2. SELL - Close existing position or short
3. HOLD - Do nothing

Please respond with:
1. Your decision: BUY, SELL, or HOLD
2. Confidence level: 0-100%
3. Brief reasoning (2-3 sentences)
4. Suggested position size: What % of available capital (if BUY)
5. Stop loss suggestion: % below entry (if BUY)

Format your response as:
DECISION: [BUY/SELL/HOLD]
CONFIDENCE: [0-100]%
REASONING: [your reasoning]
POSITION_SIZE: [0-100]%
STOP_LOSS: [0-100]%
"""

        return prompt

    def _parse_claude_decision(
        self,
        symbol: str,
        response: str,
        signals: List[Dict[str, Any]],
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Parse Claude's response into a trading decision

        Args:
            symbol: Trading pair symbol
            response: Claude's response text
            signals: Original signals
            market_data: Market context

        Returns:
            Trading decision dict
        """
        decision = {
            'symbol': symbol,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'decision': 'HOLD',
            'confidence': 0.5,
            'reasoning': response,
            'position_size_pct': 0,
            'stop_loss_pct': 0,
            'current_price': market_data.get('current_price'),
            'signals_considered': len(signals),
            'trading_mode': config.trading_mode
        }

        # Parse response lines
        for line in response.split('\n'):
            line = line.strip()

            if line.startswith('DECISION:'):
                decision['decision'] = line.split(':', 1)[1].strip().upper()

            elif line.startswith('CONFIDENCE:'):
                try:
                    conf_str = line.split(':', 1)[1].strip().replace('%', '')
                    decision['confidence'] = float(conf_str) / 100
                except:
                    pass

            elif line.startswith('POSITION_SIZE:'):
                try:
                    pos_str = line.split(':', 1)[1].strip().replace('%', '')
                    decision['position_size_pct'] = float(pos_str) / 100
                except:
                    pass

            elif line.startswith('STOP_LOSS:'):
                try:
                    sl_str = line.split(':', 1)[1].strip().replace('%', '')
                    decision['stop_loss_pct'] = float(sl_str) / 100
                except:
                    pass

        return decision

    def _get_agent_weights(self, symbol: str) -> Dict[str, float]:
        """
        Get optimized agent weights from Weight Optimizer

        Falls back to static weights if optimization not available

        Args:
            symbol: Trading pair symbol

        Returns:
            Dict of {agent_name: weight}
        """
        from datetime import datetime, timezone, timedelta

        # Refresh weights every hour
        should_refresh = (
            self.weights_last_loaded is None or
            (datetime.now(timezone.utc) - self.weights_last_loaded).total_seconds() > 3600
        )

        if should_refresh:
            try:
                # Try to load from Redis cache first (fastest)
                cached_weights = self.redis.get_json('agent_weights:current')

                if cached_weights:
                    self.optimized_weights = cached_weights
                    self.weights_last_loaded = datetime.now(timezone.utc)
                    self.logger.info(f"Loaded optimized weights from cache: {cached_weights}")
                else:
                    # Load from database
                    with self.db.get_session() as session:
                        query = text("""
                            SELECT agent_weights
                            FROM weight_history
                            ORDER BY timestamp DESC
                            LIMIT 1
                        """)

                        result = session.execute(query).fetchone()

                        if result and result[0]:
                            self.optimized_weights = result[0]  # JSONB field
                            self.weights_last_loaded = datetime.now(timezone.utc)
                            self.logger.info(f"Loaded optimized weights from DB: {self.optimized_weights}")
                        else:
                            self.logger.info("No optimized weights found, using static weights")
                            self.optimized_weights = None

            except Exception as e:
                self.logger.warning(f"Could not load optimized weights: {e}")
                self.optimized_weights = None

        # Use optimized weights if available
        if self.optimized_weights:
            return self.optimized_weights

        # Fallback to static weights based on asset class
        is_crypto = any(crypto in symbol for crypto in ['BTC', 'ETH', 'SOL', 'AVAX', 'MATIC'])

        if is_crypto:
            weights = {
                'TechnicalAnalyst': 0.4,
                'SentimentAnalyst': 0.6,
                'OnChainAnalyst': 0.5,  # If added later
                'NewsAnalyst': 0.3      # If added later
            }
        else:
            weights = {
                'TechnicalAnalyst': 0.5,
                'SentimentAnalyst': 0.3,
                'FundamentalAnalyst': 0.4,  # If added later
                'NewsAnalyst': 0.2           # If added later
            }

        return weights

    def _log_decision(self, decision: Dict[str, Any]) -> Optional[int]:
        """
        Log trading decision to database

        Args:
            decision: Trading decision dict

        Returns:
            decision_id if successful, None otherwise
        """
        try:
            with self.db.get_session() as session:
                query = text("""
                    INSERT INTO trading_decisions (
                        symbol,
                        decision,
                        confidence,
                        reasoning,
                        position_size_pct,
                        stop_loss_pct,
                        current_price,
                        signals_considered,
                        trading_mode,
                        timestamp
                    ) VALUES (
                        :symbol,
                        :decision,
                        :confidence,
                        :reasoning,
                        :position_size_pct,
                        :stop_loss_pct,
                        :current_price,
                        :signals_considered,
                        :trading_mode,
                        :timestamp
                    ) RETURNING id
                """)

                result = session.execute(query, decision)
                decision_id = result.fetchone()[0]
                session.commit()

                self.logger.info(f"Logged decision: {decision['decision']} {decision['symbol']}")
                return decision_id

        except Exception as e:
            # Create table if it doesn't exist
            self.logger.warning(f"Could not log decision (table may not exist): {e}")
            return None

    def _execute_buy_decision(self, decision: Dict[str, Any], decision_id: int):
        """
        Execute a BUY decision by placing an order

        Args:
            decision: The trading decision dict
            decision_id: The decision_id from the database
        """
        try:
            symbol = decision['symbol']
            current_price = decision['current_price']
            position_size_pct = decision.get('position_size_pct', 0)

            if not current_price or position_size_pct <= 0:
                self.logger.info(f"Skipping execution - price or position size not set for {symbol}")
                return

            # Get current portfolio value
            portfolio_value = self.paper_trading_engine.get_portfolio_value()
            available_capital = portfolio_value.cash_balance

            # Calculate order value and quantity
            order_value = available_capital * position_size_pct
            quantity = order_value / current_price

            # Determine asset class (all current symbols are crypto)
            asset_class = 'crypto'

            self.logger.info(
                f"Executing BUY for {symbol}: "
                f"{quantity:.8f} @ ${current_price:.2f} = ${order_value:.2f} "
                f"({position_size_pct*100:.1f}% of portfolio)"
            )

            # Execute the order
            order = self.paper_trading_engine.execute_order(
                symbol=symbol,
                asset_class=asset_class,
                order_type=OrderType.MARKET,
                side=OrderSide.BUY,
                quantity=quantity,
                decision_id=decision_id
            )

            if order:
                self.logger.info(f"✅ Order executed: {order.order_id} - {quantity:.8f} {symbol}")
            else:
                self.logger.warning(f"❌ Order execution failed for {symbol}")

        except Exception as e:
            self.logger.error(f"Error executing BUY decision for {decision.get('symbol')}: {e}", exc_info=True)

    def _execute_sell_decision(self, decision: Dict[str, Any], decision_id: int):
        """
        Execute a SELL decision - either close existing LONG position or open SHORT position

        Args:
            decision: The trading decision dict
            decision_id: The decision_id from the database
        """
        try:
            symbol = decision['symbol']
            current_price = decision['current_price']
            position_size_pct = decision.get('position_size_pct', 0)

            if not current_price:
                self.logger.info(f"Skipping execution - price not available for {symbol}")
                return

            # Check if we have an existing LONG position to close
            existing_position = None
            with self.db.get_session() as session:
                result = session.execute(text("""
                    SELECT position_id, quantity, entry_price, side, opened_at
                    FROM paper_positions
                    WHERE symbol = :symbol
                    LIMIT 1
                """), {'symbol': symbol}).fetchone()

                if result:
                    # Calculate hold duration
                    from datetime import datetime, timezone
                    opened_at = result[4]
                    hold_minutes = (datetime.now(timezone.utc) - opened_at).total_seconds() / 60

                    existing_position = {
                        'position_id': result[0],
                        'quantity': float(result[1]),
                        'entry_price': float(result[2]),
                        'side': result[3],
                        'hold_minutes': hold_minutes
                    }

            # Determine asset class (all current symbols are crypto)
            asset_class = 'crypto'

            if existing_position and existing_position['side'] == 'LONG':
                # Check minimum hold time (15 minutes)
                MIN_HOLD_TIME_MINUTES = 15
                hold_minutes = existing_position['hold_minutes']

                if hold_minutes < MIN_HOLD_TIME_MINUTES:
                    self.logger.info(
                        f"⏸️  Skipping SELL for {symbol} - position held for {hold_minutes:.1f}min "
                        f"(minimum: {MIN_HOLD_TIME_MINUTES}min)"
                    )
                    return

                # Check stop-loss and take-profit conditions
                entry_price = existing_position['entry_price']
                price_change_pct = ((current_price - entry_price) / entry_price) * 100

                # Stop-loss: -5% (only close if losing more than 5%)
                # Take-profit: +10% (only close if making more than 10%)
                STOP_LOSS_PCT = -5.0
                TAKE_PROFIT_PCT = 10.0

                should_close = False
                close_reason = ""

                if price_change_pct <= STOP_LOSS_PCT:
                    should_close = True
                    close_reason = f"Stop-loss triggered ({price_change_pct:.2f}%)"
                elif price_change_pct >= TAKE_PROFIT_PCT:
                    should_close = True
                    close_reason = f"Take-profit triggered ({price_change_pct:.2f}%)"
                elif decision['confidence'] >= 0.75:
                    # Only close on strong opposite signal (75%+ confidence)
                    should_close = True
                    close_reason = f"Strong SELL signal (confidence: {decision['confidence']:.1%})"

                if not should_close:
                    self.logger.info(
                        f"⏸️  Holding {symbol} position - change: {price_change_pct:+.2f}%, "
                        f"held: {hold_minutes:.1f}min, SELL confidence: {decision['confidence']:.1%}"
                    )
                    return

                # Close existing LONG position
                quantity = existing_position['quantity']
                self.logger.info(
                    f"Executing SELL to close LONG position for {symbol}: "
                    f"{quantity:.8f} @ ${current_price:.2f} | Reason: {close_reason}"
                )

                # Execute sell order
                order = self.paper_trading_engine.execute_order(
                    symbol=symbol,
                    asset_class=asset_class,
                    order_type=OrderType.MARKET,
                    side=OrderSide.SELL,
                    quantity=quantity,
                    decision_id=decision_id
                )

                if order:
                    self.logger.info(f"✅ LONG position closed: {order.order_id} - {quantity:.8f} {symbol}")
                else:
                    self.logger.warning(f"❌ Order execution failed for {symbol}")

            elif position_size_pct > 0:
                # Open new SHORT position
                portfolio_value = self.paper_trading_engine.get_portfolio_value()
                available_capital = portfolio_value.cash_balance

                # Calculate order value and quantity
                order_value = available_capital * position_size_pct
                quantity = order_value / current_price

                self.logger.info(
                    f"Executing SELL to open SHORT position for {symbol}: "
                    f"{quantity:.8f} @ ${current_price:.2f} = ${order_value:.2f} "
                    f"({position_size_pct*100:.1f}% of portfolio)"
                )

                # Execute short order (sell to open)
                order = self.paper_trading_engine.execute_order(
                    symbol=symbol,
                    asset_class=asset_class,
                    order_type=OrderType.MARKET,
                    side=OrderSide.SELL,
                    quantity=quantity,
                    decision_id=decision_id
                )

                if order:
                    self.logger.info(f"✅ SHORT position opened: {order.order_id} - {quantity:.8f} {symbol}")
                else:
                    self.logger.warning(f"❌ Order execution failed for {symbol}")
            else:
                self.logger.info(f"Skipping execution - no existing position and position size is 0 for {symbol}")

        except Exception as e:
            self.logger.error(f"Error executing SELL decision for {decision.get('symbol')}: {e}", exc_info=True)

    def _check_system_health(self) -> Dict[str, Any]:
        """
        Check overall system health

        Returns:
            Dict with health status
        """
        health = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'status': 'healthy',
            'issues': []
        }

        try:
            with self.db.get_session() as session:
                # Check data freshness
                query = text("""
                    SELECT
                        symbol,
                        MAX(time) as latest_data,
                        NOW() - MAX(time) as age
                    FROM price_data
                    GROUP BY symbol
                """)

                results = session.execute(query).fetchall()

                for row in results:
                    symbol, latest, age = row
                    age_minutes = age.total_seconds() / 60

                    if age_minutes > 120:  # Data older than 2 hours
                        health['issues'].append(
                            f"{symbol}: Data is {age_minutes:.0f} minutes old"
                        )

                # Check agent executions
                query = text("""
                    SELECT
                        agent_name,
                        COUNT(*) as executions,
                        SUM(CASE WHEN success THEN 1 ELSE 0 END) as successes,
                        MAX(end_time) as last_run
                    FROM agent_executions
                    WHERE start_time >= NOW() - INTERVAL '24 hours'
                    GROUP BY agent_name
                """)

                results = session.execute(query).fetchall()

                health['agent_stats'] = [
                    {
                        'agent': row[0],
                        'executions_24h': row[1],
                        'success_rate': float(row[2]) / float(row[1]) if row[1] > 0 else 0,
                        'last_run': row[3].isoformat() if row[3] else None
                    }
                    for row in results
                ]

                if health['issues']:
                    health['status'] = 'degraded'

        except Exception as e:
            health['status'] = 'error'
            health['issues'].append(f"Health check failed: {e}")

        return health

    def _get_latest_signals(self) -> List[Dict[str, Any]]:
        """Get latest signals from all analysts"""
        try:
            with self.db.get_session() as session:
                query = text("""
                    SELECT DISTINCT ON (symbol)
                        symbol,
                        signal,
                        confidence,
                        agent_name,
                        time
                    FROM agent_signals
                    ORDER BY symbol, time DESC
                """)

                results = session.execute(query).fetchall()

                return [
                    {
                        'symbol': row[0],
                        'signal': row[1],
                        'confidence': float(row[2]),
                        'agent': row[3],
                        'time': row[4].isoformat()
                    }
                    for row in results
                ]

        except Exception as e:
            self.logger.error(f"Error getting latest signals: {e}")
            return []

    def _get_portfolio_status(self) -> Dict[str, Any]:
        """Get current portfolio status"""
        try:
            with self.db.get_session() as session:
                query = text("""
                    SELECT
                        cash,
                        total_value,
                        positions,
                        open_positions
                    FROM portfolio_state
                    ORDER BY time DESC
                    LIMIT 1
                """)

                result = session.execute(query).fetchone()

                if result:
                    return {
                        'cash': float(result[0]),
                        'total_value': float(result[1]),
                        'positions': result[2],
                        'open_positions': result[3]
                    }

        except Exception as e:
            self.logger.error(f"Error getting portfolio status: {e}")

        return {
            'cash': config.initial_capital,
            'total_value': config.initial_capital,
            'positions': [],
            'open_positions': 0
        }


# Convenience function to run the orchestrator
def run_orchestrator():
    """Run the orchestrator agent"""
    orchestrator = OrchestratorAgent()
    return orchestrator.execute()


if __name__ == "__main__":
    import time
    import signal
    import sys

    # Handle graceful shutdown
    def signal_handler(sig, frame):
        print("\n\nShutting down orchestrator...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run orchestrator continuously
    print("Starting continuous orchestration (60 second cycles)...")
    print("Press Ctrl+C to stop\n")

    # Create orchestrator instance once to avoid Prometheus metric re-registration
    orchestrator = OrchestratorAgent()

    cycle_count = 0
    while True:
        try:
            cycle_count += 1
            print(f"\n{'='*80}")
            print(f"CYCLE #{cycle_count} - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
            print(f"{'='*80}\n")

            result = orchestrator.execute()

            # Print summary
            if result.get('success'):
                decisions = result.get('trading_decisions', [])
                print(f"\n✅ Cycle completed successfully")
                print(f"   Trading decisions: {len(decisions)}")

                # Show high-confidence decisions
                high_conf = [d for d in decisions if d.get('confidence', 0) >= 0.6]
                if high_conf:
                    print(f"   High confidence (≥60%): {len(high_conf)}")
                    for d in high_conf:
                        print(f"      {d['symbol']}: {d['decision']} ({d['confidence']*100:.1f}%)")
            else:
                print(f"\n❌ Cycle failed: {result.get('error', 'Unknown error')}")

            print(f"\n⏳ Waiting 60 seconds before next cycle...")
            time.sleep(60)

        except Exception as e:
            print(f"\n❌ Error in orchestration cycle: {e}")
            print(f"⏳ Waiting 60 seconds before retry...")
            time.sleep(60)

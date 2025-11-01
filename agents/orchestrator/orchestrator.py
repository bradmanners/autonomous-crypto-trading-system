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
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy import text
import json

from agents.base_agent import BaseAgent, AgentType, SignalType
from agents.data_collectors.price_collector import PriceCollectorAgent
from agents.analysts.technical_analyst import TechnicalAnalystAgent
from config.config import config


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

    def __init__(self):
        super().__init__(
            agent_name="Orchestrator",
            agent_type=AgentType.ORCHESTRATOR,
            version="1.0.0"
        )

        # Initialize sub-agents
        self.price_collector = PriceCollectorAgent()
        self.technical_analyst = TechnicalAnalystAgent()

        # Initialize Claude AI client
        self.claude = anthropic.Anthropic(api_key=config.anthropic_api_key)

        self.logger.info("Orchestrator initialized with sub-agents")

    def run(self) -> Dict[str, Any]:
        """
        Main orchestration cycle

        Returns:
            Dict with execution results
        """
        results = {
            'cycle_start': datetime.now().isoformat(),
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

        results['cycle_end'] = datetime.now().isoformat()
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
                    self._log_decision(decision)

            except Exception as e:
                self.logger.error(f"Error making decision for {symbol}: {e}", exc_info=True)

        return decisions

    def _get_recent_signals(self, symbol: str, hours: int = 1) -> List[Dict[str, Any]]:
        """
        Get recent signals for a symbol

        Args:
            symbol: Trading pair symbol
            hours: Number of hours to look back

        Returns:
            List of signal dicts
        """
        try:
            with self.db.get_session() as session:
                query = text("""
                    SELECT
                        agent_name,
                        signal,
                        confidence,
                        reasoning,
                        metadata,
                        time
                    FROM agent_signals
                    WHERE symbol = :symbol
                        AND time >= NOW() - INTERVAL ':hours hours'
                    ORDER BY time DESC
                """)

                results = session.execute(query, {
                    'symbol': symbol,
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
        Make trading decision based on analyst signals (without Claude AI)

        Args:
            symbol: Trading pair symbol
            signals: List of signals from analysts
            market_data: Current market context

        Returns:
            Trading decision dict or None
        """
        if not signals:
            return None

        # Get the most recent signal (they're ordered by time DESC)
        latest_signal = signals[0]

        signal_type = latest_signal['signal'].upper()
        confidence = latest_signal['confidence']

        # Only make BUY/SELL decisions if confidence is high enough
        if signal_type == 'BUY' and confidence >= 0.7:
            decision = 'BUY'
            position_size_pct = min(confidence * 0.3, 0.3)  # Max 30% of capital
            stop_loss_pct = 0.05  # 5% stop loss
        elif signal_type == 'SELL' and confidence >= 0.7:
            decision = 'SELL'
            position_size_pct = 0
            stop_loss_pct = 0
        else:
            decision = 'HOLD'
            position_size_pct = 0
            stop_loss_pct = 0

        reasoning = f"Based on {latest_signal['agent_name']} signal: {latest_signal['reasoning']}"

        return {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'decision': decision,
            'confidence': confidence,
            'reasoning': reasoning,
            'position_size_pct': position_size_pct,
            'stop_loss_pct': stop_loss_pct,
            'current_price': market_data.get('current_price'),
            'signals_considered': len(signals),
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
            'timestamp': datetime.now().isoformat(),
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

    def _log_decision(self, decision: Dict[str, Any]):
        """
        Log trading decision to database

        Args:
            decision: Trading decision dict
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
                    )
                """)

                session.execute(query, decision)
                session.commit()

                self.logger.info(f"Logged decision: {decision['decision']} {decision['symbol']}")

        except Exception as e:
            # Create table if it doesn't exist
            self.logger.warning(f"Could not log decision (table may not exist): {e}")

    def _check_system_health(self) -> Dict[str, Any]:
        """
        Check overall system health

        Returns:
            Dict with health status
        """
        health = {
            'timestamp': datetime.now().isoformat(),
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
    # Run orchestrator when executed directly
    result = run_orchestrator()
    print(f"Orchestration result: {result}")

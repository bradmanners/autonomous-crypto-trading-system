"""
Technical Analysis Agent

Calculates technical indicators and generates trading signals based on price patterns
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy import text

from agents.base_agent import BaseAgent, AgentType, SignalType, SignalStrength
from config.config import config


class TechnicalAnalystAgent(BaseAgent):
    """
    Agent responsible for technical analysis and signal generation

    Calculates:
    - Trend indicators: EMAs, MACD, ADX
    - Momentum indicators: RSI, Stochastic
    - Volatility indicators: Bollinger Bands, ATR
    - Volume indicators: OBV, VWAP

    Generates trading signals based on indicator combinations
    """

    def __init__(self):
        super().__init__(
            agent_name="Technical Analyst",
            agent_type=AgentType.ANALYST,
            version="1.0.0"
        )

        # Analysis parameters
        self.timeframe = '1h'  # Primary timeframe for analysis
        self.lookback_candles = 200  # Need 200 for EMA-200

        self.logger.info(
            f"Technical Analyst initialized for {len(config.trading_pairs)} pairs "
            f"on {self.timeframe} timeframe"
        )

    def run(self) -> Dict[str, Any]:
        """
        Main execution: analyze all trading pairs and generate signals

        Returns:
            Dict with execution results
        """
        results = {
            'pairs_analyzed': 0,
            'signals_generated': 0,
            'buy_signals': 0,
            'sell_signals': 0,
            'hold_signals': 0,
            'errors': []
        }

        for symbol in config.trading_pairs:
            try:
                # Analyze the symbol
                analysis = self.analyze_symbol(symbol)

                if analysis:
                    results['pairs_analyzed'] += 1

                    # Generate and save signal
                    signal = self._generate_signal(symbol, analysis)

                    if signal:
                        signal_id = self.save_signal(
                            symbol=symbol,
                            signal_type=signal['type'],
                            confidence=signal['confidence'],
                            reasoning=signal['reasoning'],
                            metadata=signal['metadata']
                        )

                        results['signals_generated'] += 1

                        if signal['type'] == SignalType.BUY:
                            results['buy_signals'] += 1
                        elif signal['type'] == SignalType.SELL:
                            results['sell_signals'] += 1
                        else:
                            results['hold_signals'] += 1

                        self.logger.info(
                            f"Generated {signal['type'].value} signal for {symbol} "
                            f"(confidence: {signal['confidence']:.2f}, id: {signal_id})"
                        )

            except Exception as e:
                error_msg = f"Error analyzing {symbol}: {e}"
                self.logger.error(error_msg, exc_info=True)
                results['errors'].append(error_msg)

        self.logger.info(
            f"Analysis complete: {results['pairs_analyzed']} pairs analyzed, "
            f"{results['signals_generated']} signals generated "
            f"(BUY: {results['buy_signals']}, SELL: {results['sell_signals']}, "
            f"HOLD: {results['hold_signals']})"
        )

        return results

    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze price data and calculate indicators

        Args:
            data: Dict containing 'symbol' and optional 'timeframe'

        Returns:
            Dict with analysis results
        """
        symbol = data.get('symbol')
        timeframe = data.get('timeframe', self.timeframe)

        return self.analyze_symbol(symbol, timeframe)

    def analyze_symbol(
        self,
        symbol: str,
        timeframe: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Perform complete technical analysis on a symbol

        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe to analyze (defaults to self.timeframe)

        Returns:
            Dict with all calculated indicators and metadata
        """
        if timeframe is None:
            timeframe = self.timeframe

        # Get price data
        df = self._get_price_dataframe(symbol, timeframe)

        if df is None or len(df) < 50:
            self.logger.warning(
                f"Insufficient data for {symbol} {timeframe}: {len(df) if df is not None else 0} candles"
            )
            return None

        # Calculate all indicators
        indicators = {}

        # Trend indicators
        indicators.update(self._calculate_ema(df))
        indicators.update(self._calculate_macd(df))

        # Momentum indicators
        indicators.update(self._calculate_rsi(df))
        indicators.update(self._calculate_stochastic(df))

        # Volatility indicators
        indicators.update(self._calculate_bollinger_bands(df))
        indicators.update(self._calculate_atr(df))

        # Volume indicators
        indicators.update(self._calculate_obv(df))
        indicators.update(self._calculate_vwap(df))

        # Current price info
        latest = df.iloc[-1]
        indicators['current_price'] = float(latest['close'])
        indicators['timestamp'] = latest.name.isoformat()

        # Store indicators in database
        self._store_indicators(symbol, timeframe, latest.name, indicators)

        return indicators

    def _get_price_dataframe(
        self,
        symbol: str,
        timeframe: str
    ) -> Optional[pd.DataFrame]:
        """
        Get price data as pandas DataFrame

        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe

        Returns:
            DataFrame with OHLCV data
        """
        try:
            with self.db.get_session() as session:
                query = text("""
                    SELECT
                        time, open, high, low, close, volume
                    FROM price_data
                    WHERE symbol = :symbol
                        AND timeframe = :timeframe
                    ORDER BY time ASC
                    LIMIT :limit
                """)

                result = session.execute(query, {
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'limit': self.lookback_candles
                }).fetchall()

                if not result:
                    return None

                # Convert to DataFrame
                df = pd.DataFrame(result, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
                df.set_index('time', inplace=True)

                # Convert to float
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = df[col].astype(float)

                return df

        except Exception as e:
            self.logger.error(f"Error getting price dataframe: {e}")
            return None

    # ==================== INDICATOR CALCULATIONS ====================

    def _calculate_ema(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate Exponential Moving Averages"""
        ema_periods = [9, 21, 50, 200]
        emas = {}

        for period in ema_periods:
            if len(df) >= period:
                emas[f'ema_{period}'] = float(df['close'].ewm(span=period, adjust=False).mean().iloc[-1])

        return emas

    def _calculate_macd(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate MACD (Moving Average Convergence Divergence)"""
        if len(df) < 26:
            return {}

        ema_12 = df['close'].ewm(span=12, adjust=False).mean()
        ema_26 = df['close'].ewm(span=26, adjust=False).mean()
        macd_line = ema_12 - ema_26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        histogram = macd_line - signal_line

        return {
            'macd': float(macd_line.iloc[-1]),
            'macd_signal': float(signal_line.iloc[-1]),
            'macd_histogram': float(histogram.iloc[-1])
        }

    def _calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> Dict[str, float]:
        """Calculate Relative Strength Index"""
        if len(df) < period + 1:
            return {}

        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        return {'rsi_14': float(rsi.iloc[-1])}

    def _calculate_stochastic(self, df: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> Dict[str, float]:
        """Calculate Stochastic Oscillator"""
        if len(df) < k_period:
            return {}

        low_min = df['low'].rolling(window=k_period).min()
        high_max = df['high'].rolling(window=k_period).max()

        stoch_k = 100 * (df['close'] - low_min) / (high_max - low_min)
        stoch_d = stoch_k.rolling(window=d_period).mean()

        return {
            'stoch_k': float(stoch_k.iloc[-1]),
            'stoch_d': float(stoch_d.iloc[-1])
        }

    def _calculate_bollinger_bands(self, df: pd.DataFrame, period: int = 20, std_dev: int = 2) -> Dict[str, float]:
        """Calculate Bollinger Bands"""
        if len(df) < period:
            return {}

        sma = df['close'].rolling(window=period).mean()
        std = df['close'].rolling(window=period).std()

        bb_upper = sma + (std * std_dev)
        bb_middle = sma
        bb_lower = sma - (std * std_dev)

        return {
            'bb_upper': float(bb_upper.iloc[-1]),
            'bb_middle': float(bb_middle.iloc[-1]),
            'bb_lower': float(bb_lower.iloc[-1])
        }

    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> Dict[str, float]:
        """Calculate Average True Range"""
        if len(df) < period + 1:
            return {}

        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())

        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean()

        return {'atr': float(atr.iloc[-1])}

    def _calculate_obv(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate On-Balance Volume"""
        if len(df) < 2:
            return {}

        obv = (np.sign(df['close'].diff()) * df['volume']).fillna(0).cumsum()

        return {'obv': float(obv.iloc[-1])}

    def _calculate_vwap(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate Volume Weighted Average Price"""
        if len(df) < 1:
            return {}

        typical_price = (df['high'] + df['low'] + df['close']) / 3
        vwap = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()

        return {'vwap': float(vwap.iloc[-1])}

    # ==================== SIGNAL GENERATION ====================

    def _generate_signal(
        self,
        symbol: str,
        indicators: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Generate trading signal based on technical indicators

        Uses a scoring system combining multiple indicators

        Args:
            symbol: Trading pair symbol
            indicators: Dict of calculated indicators

        Returns:
            Dict with signal details or None
        """
        score = 0  # -100 to +100 scale
        reasoning_parts = []
        current_price = indicators.get('current_price', 0)

        # 1. TREND ANALYSIS (EMA crossovers) - Weight: 30 points
        if 'ema_9' in indicators and 'ema_21' in indicators:
            ema_9 = indicators['ema_9']
            ema_21 = indicators['ema_21']

            if ema_9 > ema_21:
                score += 15
                reasoning_parts.append("EMA9 > EMA21 (short-term uptrend)")
            else:
                score -= 15
                reasoning_parts.append("EMA9 < EMA21 (short-term downtrend)")

        if 'ema_50' in indicators and current_price > 0:
            ema_50 = indicators['ema_50']

            if current_price > ema_50:
                score += 15
                reasoning_parts.append(f"Price above EMA50 (${ema_50:.2f})")
            else:
                score -= 15
                reasoning_parts.append(f"Price below EMA50 (${ema_50:.2f})")

        # 2. MOMENTUM ANALYSIS (RSI) - Weight: 25 points
        if 'rsi_14' in indicators:
            rsi = indicators['rsi_14']

            if rsi < 30:
                score += 25
                reasoning_parts.append(f"RSI oversold ({rsi:.1f})")
            elif rsi < 40:
                score += 15
                reasoning_parts.append(f"RSI approaching oversold ({rsi:.1f})")
            elif rsi > 70:
                score -= 25
                reasoning_parts.append(f"RSI overbought ({rsi:.1f})")
            elif rsi > 60:
                score -= 15
                reasoning_parts.append(f"RSI approaching overbought ({rsi:.1f})")
            else:
                reasoning_parts.append(f"RSI neutral ({rsi:.1f})")

        # 3. MACD ANALYSIS - Weight: 20 points
        if 'macd' in indicators and 'macd_signal' in indicators:
            macd = indicators['macd']
            macd_signal = indicators['macd_signal']
            macd_hist = indicators.get('macd_histogram', 0)

            if macd > macd_signal and macd_hist > 0:
                score += 20
                reasoning_parts.append("MACD bullish (above signal)")
            elif macd < macd_signal and macd_hist < 0:
                score -= 20
                reasoning_parts.append("MACD bearish (below signal)")

        # 4. BOLLINGER BANDS - Weight: 15 points
        if 'bb_upper' in indicators and 'bb_lower' in indicators:
            bb_upper = indicators['bb_upper']
            bb_lower = indicators['bb_lower']
            bb_middle = indicators['bb_middle']

            price_position = (current_price - bb_lower) / (bb_upper - bb_lower)

            if price_position < 0.2:
                score += 15
                reasoning_parts.append("Price near lower BB (potential bounce)")
            elif price_position > 0.8:
                score -= 15
                reasoning_parts.append("Price near upper BB (potential reversal)")

        # 5. STOCHASTIC - Weight: 10 points
        if 'stoch_k' in indicators and 'stoch_d' in indicators:
            stoch_k = indicators['stoch_k']
            stoch_d = indicators['stoch_d']

            if stoch_k < 20 and stoch_k > stoch_d:
                score += 10
                reasoning_parts.append("Stochastic oversold with bullish crossover")
            elif stoch_k > 80 and stoch_k < stoch_d:
                score -= 10
                reasoning_parts.append("Stochastic overbought with bearish crossover")

        # Convert score to signal type and confidence
        signal_type = SignalType.HOLD
        confidence = 0.0

        if score >= 40:
            signal_type = SignalType.BUY
            confidence = min(score / 100, 1.0)
        elif score <= -40:
            signal_type = SignalType.SELL
            confidence = min(abs(score) / 100, 1.0)
        else:
            signal_type = SignalType.HOLD
            confidence = 0.5

        reasoning = f"Score: {score}/100. " + "; ".join(reasoning_parts)

        return {
            'type': signal_type,
            'confidence': confidence,
            'reasoning': reasoning,
            'metadata': {
                'score': score,
                'indicators': indicators,
                'analysis_timeframe': self.timeframe
            }
        }

    def _store_indicators(
        self,
        symbol: str,
        timeframe: str,
        timestamp: datetime,
        indicators: Dict[str, Any]
    ):
        """
        Store calculated indicators in database

        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe
            timestamp: Timestamp for the indicators
            indicators: Dict of indicator values
        """
        try:
            with self.db.get_session() as session:
                query = text("""
                    INSERT INTO technical_indicators (
                        time, symbol, timeframe,
                        ema_9, ema_21, ema_50, ema_200,
                        macd, macd_signal, macd_histogram,
                        rsi_14, stoch_k, stoch_d,
                        bb_upper, bb_middle, bb_lower,
                        atr, obv, vwap
                    ) VALUES (
                        :time, :symbol, :timeframe,
                        :ema_9, :ema_21, :ema_50, :ema_200,
                        :macd, :macd_signal, :macd_histogram,
                        :rsi_14, :stoch_k, :stoch_d,
                        :bb_upper, :bb_middle, :bb_lower,
                        :atr, :obv, :vwap
                    )
                    ON CONFLICT (time, symbol, timeframe)
                    DO UPDATE SET
                        ema_9 = EXCLUDED.ema_9,
                        ema_21 = EXCLUDED.ema_21,
                        ema_50 = EXCLUDED.ema_50,
                        ema_200 = EXCLUDED.ema_200,
                        macd = EXCLUDED.macd,
                        macd_signal = EXCLUDED.macd_signal,
                        macd_histogram = EXCLUDED.macd_histogram,
                        rsi_14 = EXCLUDED.rsi_14,
                        stoch_k = EXCLUDED.stoch_k,
                        stoch_d = EXCLUDED.stoch_d,
                        bb_upper = EXCLUDED.bb_upper,
                        bb_middle = EXCLUDED.bb_middle,
                        bb_lower = EXCLUDED.bb_lower,
                        atr = EXCLUDED.atr,
                        obv = EXCLUDED.obv,
                        vwap = EXCLUDED.vwap
                """)

                session.execute(query, {
                    'time': timestamp,
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'ema_9': indicators.get('ema_9'),
                    'ema_21': indicators.get('ema_21'),
                    'ema_50': indicators.get('ema_50'),
                    'ema_200': indicators.get('ema_200'),
                    'macd': indicators.get('macd'),
                    'macd_signal': indicators.get('macd_signal'),
                    'macd_histogram': indicators.get('macd_histogram'),
                    'rsi_14': indicators.get('rsi_14'),
                    'stoch_k': indicators.get('stoch_k'),
                    'stoch_d': indicators.get('stoch_d'),
                    'bb_upper': indicators.get('bb_upper'),
                    'bb_middle': indicators.get('bb_middle'),
                    'bb_lower': indicators.get('bb_lower'),
                    'atr': indicators.get('atr'),
                    'obv': indicators.get('obv'),
                    'vwap': indicators.get('vwap')
                })

                session.commit()

        except Exception as e:
            self.logger.warning(f"Failed to store indicators: {e}")


# Convenience function to run the analyst
def run_technical_analyst():
    """Run the technical analyst agent"""
    analyst = TechnicalAnalystAgent()
    return analyst.execute()


if __name__ == "__main__":
    # Run analyst when executed directly
    result = run_technical_analyst()
    print(f"Analysis result: {result}")

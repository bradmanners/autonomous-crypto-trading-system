"""
Sentiment Analyst Agent

Analyzes social sentiment from Reddit, Twitter, and other sources
to generate trading signals based on market mood and community activity.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy import text

from agents.base_agent import BaseAgent, AgentType, SignalType
from data_sources.sentiment_collectors import RedditSentimentCollector, get_sentiment_collector
from utils.database import DatabaseManager


class SentimentAnalystAgent(BaseAgent):
    """
    Sentiment analysis agent that:
    1. Collects social sentiment data (Reddit, Twitter)
    2. Analyzes mention volume and sentiment scores
    3. Generates trading signals based on social activity
    4. Stores signals in database

    Signal Generation Rules:
    - High mention volume + bullish sentiment = BUY signal
    - High mention volume + bearish sentiment = SELL signal
    - Low mention volume or neutral sentiment = HOLD
    """

    def __init__(self):
        super().__init__(
            agent_name="SentimentAnalyst",
            agent_type=AgentType.ANALYST,
            version="1.0.0"
        )

        self.db = DatabaseManager()

        # Try to initialize Reddit collector (optional)
        self.reddit_collector = None
        try:
            self.reddit_collector = RedditSentimentCollector()
            self.logger.info("Reddit sentiment collector initialized")
        except Exception as e:
            self.logger.warning(f"Reddit collector not available: {e}")

        self.logger.info("Sentiment Analyst initialized")

    def run(self) -> Dict[str, Any]:
        """
        Main execution method (required by BaseAgent)
        Calls execute_analysis with default symbols from config
        """
        from config.config import config
        symbols = [pair.split('/')[0] for pair in config.trading_pairs]
        return self.execute_analysis(symbols)

    def execute_analysis(self, symbols: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Execute sentiment analysis for given symbols

        Args:
            symbols: List of symbols to analyze (e.g., ['BTC', 'ETH'])
                    If None, uses default trading pairs

        Returns:
            Dict with execution results
        """
        from config.config import config

        if symbols is None:
            # Extract base symbols from trading pairs
            symbols = [pair.split('/')[0] for pair in config.trading_pairs]

        results = {
            'timestamp': datetime.now().isoformat(),
            'symbols_analyzed': 0,
            'signals_generated': 0,
            'bullish_signals': 0,
            'bearish_signals': 0,
            'neutral_signals': 0,
            'errors': []
        }

        for symbol in symbols:
            try:
                signal = self.analyze_symbol_sentiment(symbol)

                if signal:
                    # Store signal in database
                    self._store_signal(signal)

                    results['signals_generated'] += 1
                    results['symbols_analyzed'] += 1

                    if signal['signal_type'] == SignalType.BUY.value:
                        results['bullish_signals'] += 1
                    elif signal['signal_type'] == SignalType.SELL.value:
                        results['bearish_signals'] += 1
                    else:
                        results['neutral_signals'] += 1

                    self.logger.info(
                        f"{symbol}: {signal['signal_type']} "
                        f"(score: {signal['strength']}, confidence: {signal['confidence']:.0%})"
                    )

            except Exception as e:
                error_msg = f"Error analyzing {symbol}: {e}"
                self.logger.error(error_msg)
                results['errors'].append(error_msg)

        results['success'] = len(results['errors']) == 0

        self.logger.info(
            f"Sentiment analysis complete: {results['symbols_analyzed']} symbols, "
            f"{results['signals_generated']} signals "
            f"({results['bullish_signals']} bullish, {results['bearish_signals']} bearish)"
        )

        return results

    def analyze_symbol_sentiment(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Analyze sentiment for a specific symbol

        Args:
            symbol: Trading symbol (e.g., 'BTC', 'ETH', 'GME')

        Returns:
            Dict with signal data or None if insufficient data
        """
        # Get sentiment from available sources
        sentiment_data = []

        # Try Reddit sentiment
        if self.reddit_collector:
            try:
                reddit_sentiment = self.reddit_collector.get_symbol_sentiment(
                    symbol,
                    lookback_hours=24
                )
                if reddit_sentiment:
                    sentiment_data.append({
                        'source': 'reddit',
                        'sentiment_score': reddit_sentiment.sentiment_score,
                        'mention_count': reddit_sentiment.mention_count,
                        'bullish_pct': reddit_sentiment.bullish_pct,
                        'bearish_pct': reddit_sentiment.bearish_pct
                    })
            except Exception as e:
                self.logger.debug(f"Reddit sentiment for {symbol} failed: {e}")

        # If no sentiment data, return None
        if not sentiment_data:
            self.logger.debug(f"No sentiment data available for {symbol}")
            return None

        # Aggregate sentiment from all sources
        aggregated = self._aggregate_sentiment(sentiment_data)

        # Generate signal from aggregated sentiment
        signal = self._generate_signal(symbol, aggregated)

        return signal

    def _aggregate_sentiment(self, sentiment_data: List[Dict]) -> Dict[str, Any]:
        """
        Aggregate sentiment from multiple sources

        Args:
            sentiment_data: List of sentiment data from different sources

        Returns:
            Aggregated sentiment metrics
        """
        if not sentiment_data:
            return {
                'avg_sentiment': 0.0,
                'total_mentions': 0,
                'bullish_pct': 0.0,
                'bearish_pct': 0.0,
                'confidence': 0.0
            }

        # Calculate weighted averages
        total_mentions = sum(d['mention_count'] for d in sentiment_data)

        # Weight sentiment by mention count
        weighted_sentiment = sum(
            d['sentiment_score'] * d['mention_count']
            for d in sentiment_data
        ) / max(total_mentions, 1)

        avg_bullish = sum(d['bullish_pct'] for d in sentiment_data) / len(sentiment_data)
        avg_bearish = sum(d['bearish_pct'] for d in sentiment_data) / len(sentiment_data)

        # Confidence based on sample size
        # More mentions = higher confidence
        if total_mentions >= 100:
            confidence = 0.8
        elif total_mentions >= 50:
            confidence = 0.7
        elif total_mentions >= 20:
            confidence = 0.6
        elif total_mentions >= 10:
            confidence = 0.5
        else:
            confidence = 0.4

        return {
            'avg_sentiment': weighted_sentiment,
            'total_mentions': total_mentions,
            'bullish_pct': avg_bullish,
            'bearish_pct': avg_bearish,
            'confidence': confidence,
            'sources': len(sentiment_data)
        }

    def _generate_signal(self, symbol: str, aggregated: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate trading signal from aggregated sentiment

        Args:
            symbol: Trading symbol
            aggregated: Aggregated sentiment metrics

        Returns:
            Signal dictionary
        """
        sentiment_score = aggregated['avg_sentiment']
        mention_count = aggregated['total_mentions']
        bullish_pct = aggregated['bullish_pct']
        bearish_pct = aggregated['bearish_pct']
        base_confidence = aggregated['confidence']

        # Calculate signal strength (-100 to +100)
        # Sentiment score is -1 to +1, scale to -100 to +100
        sentiment_strength = sentiment_score * 100

        # Boost strength for extreme sentiment
        if abs(sentiment_score) > 0.5:
            sentiment_strength *= 1.2  # 20% boost for strong sentiment

        # Apply volume factor
        # High mention volume increases signal strength
        if mention_count > 100:
            volume_multiplier = 1.3
        elif mention_count > 50:
            volume_multiplier = 1.2
        elif mention_count > 20:
            volume_multiplier = 1.1
        else:
            volume_multiplier = 1.0

        final_strength = sentiment_strength * volume_multiplier
        final_strength = max(-100, min(100, final_strength))  # Clamp to [-100, 100]

        # Determine signal type
        if final_strength > 30:
            signal_type = SignalType.BUY
        elif final_strength < -30:
            signal_type = SignalType.SELL
        else:
            signal_type = SignalType.HOLD

        # Adjust confidence based on signal strength
        if abs(final_strength) > 60:
            confidence = min(base_confidence * 1.2, 0.95)
        elif abs(final_strength) > 40:
            confidence = base_confidence * 1.1
        else:
            confidence = base_confidence

        # Build reasoning
        sentiment_description = "Very Bullish" if sentiment_score > 0.5 else \
                               "Bullish" if sentiment_score > 0.2 else \
                               "Slightly Bullish" if sentiment_score > 0 else \
                               "Neutral" if sentiment_score == 0 else \
                               "Slightly Bearish" if sentiment_score > -0.2 else \
                               "Bearish" if sentiment_score > -0.5 else \
                               "Very Bearish"

        volume_description = "High" if mention_count > 100 else \
                            "Moderate" if mention_count > 50 else \
                            "Low"

        reasoning = (
            f"Social Sentiment: {sentiment_description} ({sentiment_score:+.2f}); "
            f"Mention volume: {volume_description} ({mention_count} mentions); "
            f"Community: {bullish_pct:.0%} bullish, {bearish_pct:.0%} bearish; "
            f"Sources: {aggregated['sources']}"
        )

        return {
            'symbol': symbol,
            'signal_type': signal_type.value,
            'strength': int(final_strength),
            'confidence': confidence,
            'reasoning': reasoning,
            'metadata': {
                'sentiment_score': sentiment_score,
                'mention_count': mention_count,
                'bullish_pct': bullish_pct,
                'bearish_pct': bearish_pct,
                'volume_multiplier': volume_multiplier
            }
        }

    def _store_signal(self, signal: Dict[str, Any]) -> None:
        """Store signal in database"""
        # Add strength to metadata since it's not in the table schema
        metadata = signal.get('metadata', {})
        metadata['strength'] = signal['strength']
        metadata['signal_type'] = signal['signal_type']
        metadata['agent_type'] = self.agent_type.value

        with self.db.get_session() as session:
            session.execute(text("""
                INSERT INTO agent_signals (
                    symbol,
                    agent_name,
                    signal,
                    confidence,
                    reasoning,
                    metadata
                ) VALUES (
                    :symbol,
                    :agent_name,
                    :signal,
                    :confidence,
                    :reasoning,
                    CAST(:metadata AS jsonb)
                )
            """), {
                'symbol': signal['symbol'],
                'agent_name': self.agent_name,
                'signal': signal['signal_type'],
                'confidence': signal['confidence'],
                'reasoning': signal['reasoning'],
                'metadata': json.dumps(metadata)
            })
            session.commit()

    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze sentiment data (required by BaseAgent)

        Args:
            data: Input data (optional, can contain 'symbols' key)

        Returns:
            Analysis results
        """
        symbols = data.get('symbols') if data else None
        return self.execute_analysis(symbols)


if __name__ == "__main__":
    # Test the sentiment analyst
    import logging
    logging.basicConfig(level=logging.INFO)

    print("\n=== Sentiment Analyst Test ===\n")

    analyst = SentimentAnalystAgent()

    # Analyze a few symbols
    test_symbols = ['BTC', 'ETH', 'GME']

    print(f"Analyzing sentiment for: {', '.join(test_symbols)}\n")

    results = analyst.execute_analysis(symbols=test_symbols)

    print(f"\nResults:")
    print(f"  Symbols analyzed: {results['symbols_analyzed']}")
    print(f"  Signals generated: {results['signals_generated']}")
    print(f"  Bullish: {results['bullish_signals']}")
    print(f"  Bearish: {results['bearish_signals']}")
    print(f"  Neutral: {results['neutral_signals']}")

    if results['errors']:
        print(f"\nErrors:")
        for error in results['errors']:
            print(f"  - {error}")

    print("\n✅ Sentiment Analyst test complete!")

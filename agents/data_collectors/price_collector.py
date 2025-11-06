"""
Price Data Collector Agent

Collects OHLCV price data from Binance and stores in TimescaleDB
"""
import ccxt
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional
import time
from sqlalchemy import text

from agents.base_agent import BaseAgent, AgentType
from config.config import config


class PriceCollectorAgent(BaseAgent):
    """
    Agent responsible for collecting price data from exchanges

    Features:
    - Fetches OHLCV data for configured trading pairs
    - Stores data in TimescaleDB
    - Handles rate limiting and retries
    - Supports multiple timeframes
    """

    def __init__(self):
        super().__init__(
            agent_name="Price Collector",
            agent_type=AgentType.DATA_COLLECTOR,
            version="1.0.0"
        )

        # Initialize exchange
        self.exchange = self._init_exchange()

        # Timeframes to collect
        self.timeframes = ['1m', '5m', '15m', '1h', '4h', '1d']

        self.logger.info(
            f"Price Collector initialized for {len(config.trading_pairs)} pairs "
            f"on {len(self.timeframes)} timeframes"
        )

    def _init_exchange(self) -> ccxt.Exchange:
        """Initialize CCXT exchange connection"""
        exchange_params = {
            'enableRateLimit': True,  # Respect rate limits
            'options': {
                'defaultType': 'spot',
            }
        }

        # For price data collection, we only need public API
        # Don't use testnet or authentication for now
        # (Testnet keys are causing issues with public endpoints)

        self.logger.info("Using Binance mainnet (public API only)")

        exchange = ccxt.binance(exchange_params)

        return exchange

    def run(self) -> Dict[str, Any]:
        """
        Main execution: collect price data for all pairs and timeframes

        Returns:
            Dict with execution results
        """
        results = {
            'pairs_processed': 0,
            'candles_collected': 0,
            'errors': []
        }

        for symbol in config.trading_pairs:
            try:
                pair_candles = self._collect_pair_data(symbol)
                results['pairs_processed'] += 1
                results['candles_collected'] += pair_candles

            except Exception as e:
                error_msg = f"Error collecting data for {symbol}: {e}"
                self.logger.error(error_msg)
                results['errors'].append(error_msg)

        self.logger.info(
            f"Collection complete: {results['pairs_processed']} pairs, "
            f"{results['candles_collected']} candles, "
            f"{len(results['errors'])} errors"
        )

        return results

    def _collect_pair_data(self, symbol: str) -> int:
        """
        Collect data for a single trading pair across all timeframes

        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')

        Returns:
            Number of candles collected
        """
        total_candles = 0

        for timeframe in self.timeframes:
            try:
                candles = self._fetch_ohlcv(symbol, timeframe)

                if candles:
                    self._store_ohlcv(symbol, timeframe, candles)
                    total_candles += len(candles)

                    self.logger.debug(
                        f"Collected {len(candles)} candles for {symbol} {timeframe}"
                    )

                # Rate limiting
                time.sleep(0.1)

            except Exception as e:
                self.logger.error(f"Error collecting {symbol} {timeframe}: {e}")

        return total_candles

    def _fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 100
    ) -> List[List]:
        """
        Fetch OHLCV data from exchange

        Args:
            symbol: Trading pair
            timeframe: Candle timeframe (1m, 5m, 1h, etc.)
            limit: Number of candles to fetch

        Returns:
            List of OHLCV candles [[timestamp, open, high, low, close, volume], ...]
        """
        try:
            # Get the last stored candle time to avoid duplicates
            last_time = self._get_last_candle_time(symbol, timeframe)

            # Fetch from exchange
            params = {}
            if last_time:
                # Fetch only new candles since last stored
                params['startTime'] = int(last_time.timestamp() * 1000)

            ohlcv = self.exchange.fetch_ohlcv(
                symbol,
                timeframe,
                limit=limit,
                params=params
            )

            return ohlcv

        except ccxt.NetworkError as e:
            self.logger.warning(f"Network error fetching {symbol} {timeframe}: {e}")
            return []
        except ccxt.ExchangeError as e:
            self.logger.error(f"Exchange error fetching {symbol} {timeframe}: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error fetching {symbol} {timeframe}: {e}")
            return []

    def _get_last_candle_time(
        self,
        symbol: str,
        timeframe: str
    ) -> Optional[datetime]:
        """
        Get the timestamp of the last stored candle

        Args:
            symbol: Trading pair
            timeframe: Candle timeframe

        Returns:
            Datetime of last candle or None
        """
        try:
            with self.db.get_session() as session:
                query = text("""
                    SELECT MAX(time) as last_time
                    FROM price_data
                    WHERE symbol = :symbol
                        AND timeframe = :timeframe
                """)

                result = session.execute(query, {
                    'symbol': symbol,
                    'timeframe': timeframe
                }).fetchone()

                if result and result[0]:
                    return result[0]

        except Exception as e:
            self.logger.warning(f"Could not get last candle time: {e}")

        return None

    def _store_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        candles: List[List]
    ):
        """
        Store OHLCV data in database

        Args:
            symbol: Trading pair
            timeframe: Candle timeframe
            candles: List of OHLCV candles
        """
        if not candles:
            return

        try:
            with self.db.get_session() as session:
                # Use INSERT ... ON CONFLICT to avoid duplicates
                query = text("""
                    INSERT INTO price_data (
                        time, symbol, exchange, timeframe,
                        open, high, low, close, volume
                    ) VALUES (
                        :time, :symbol, :exchange, :timeframe,
                        :open, :high, :low, :close, :volume
                    )
                    ON CONFLICT (time, symbol, timeframe)
                    DO UPDATE SET
                        open = EXCLUDED.open,
                        high = EXCLUDED.high,
                        low = EXCLUDED.low,
                        close = EXCLUDED.close,
                        volume = EXCLUDED.volume
                """)

                for candle in candles:
                    timestamp, open_, high, low, close, volume = candle

                    session.execute(query, {
                        'time': datetime.fromtimestamp(timestamp / 1000),
                        'symbol': symbol,
                        'exchange': 'binance',
                        'timeframe': timeframe,
                        'open': float(open_),
                        'high': float(high),
                        'low': float(low),
                        'close': float(close),
                        'volume': float(volume)
                    })

                session.commit()

                # Update cache with latest price
                latest_candle = candles[-1]
                cache_key = f"price:latest:{symbol}"
                self.redis.set_json(cache_key, {
                    'open': float(latest_candle[1]),
                    'high': float(latest_candle[2]),
                    'low': float(latest_candle[3]),
                    'close': float(latest_candle[4]),
                    'volume': float(latest_candle[5]),
                    'timestamp': datetime.fromtimestamp(latest_candle[0] / 1000).isoformat()
                }, expiry=60)

        except Exception as e:
            self.logger.error(f"Failed to store OHLCV data: {e}")
            raise

    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Data collector doesn't perform analysis

        Args:
            data: Input data (unused)

        Returns:
            Empty dict
        """
        return {}

    def get_market_status(self) -> Dict[str, Any]:
        """
        Get current market status for all configured pairs

        Returns:
            Dict with market status information
        """
        status = {
            'exchange': 'binance',
            'pairs': {},
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

        for symbol in config.trading_pairs:
            try:
                ticker = self.exchange.fetch_ticker(symbol)

                status['pairs'][symbol] = {
                    'last_price': ticker.get('last'),
                    'bid': ticker.get('bid'),
                    'ask': ticker.get('ask'),
                    'volume_24h': ticker.get('quoteVolume'),
                    'change_24h_pct': ticker.get('percentage')
                }

            except Exception as e:
                self.logger.error(f"Error fetching ticker for {symbol}: {e}")
                status['pairs'][symbol] = {'error': str(e)}

        return status

    def backfill_historical_data(
        self,
        symbol: str,
        timeframe: str = '1h',
        days_back: int = 30
    ):
        """
        Backfill historical data for a symbol

        Args:
            symbol: Trading pair
            timeframe: Candle timeframe
            days_back: Number of days to backfill
        """
        self.logger.info(
            f"Starting backfill for {symbol} {timeframe} "
            f"({days_back} days)"
        )

        # Calculate start time
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=days_back)

        # Binance has a limit of 1000 candles per request
        # Calculate how many requests we need
        timeframe_minutes = {
            '1m': 1, '5m': 5, '15m': 15, '30m': 30,
            '1h': 60, '4h': 240, '1d': 1440
        }

        minutes_per_candle = timeframe_minutes.get(timeframe, 60)
        total_candles = (days_back * 24 * 60) // minutes_per_candle
        requests_needed = (total_candles // 1000) + 1

        self.logger.info(
            f"Need {requests_needed} requests to fetch {total_candles} candles"
        )

        current_time = start_time
        total_stored = 0

        for i in range(requests_needed):
            try:
                since = int(current_time.timestamp() * 1000)

                candles = self.exchange.fetch_ohlcv(
                    symbol,
                    timeframe,
                    since=since,
                    limit=1000
                )

                if not candles:
                    break

                self._store_ohlcv(symbol, timeframe, candles)
                total_stored += len(candles)

                # Update current_time to last candle time
                last_candle_time = candles[-1][0]
                current_time = datetime.fromtimestamp(last_candle_time / 1000)

                self.logger.info(
                    f"Backfill progress: {i+1}/{requests_needed} "
                    f"({total_stored} candles stored)"
                )

                # Rate limiting
                time.sleep(1)

                # If we've reached current time, stop
                if current_time >= end_time:
                    break

            except Exception as e:
                self.logger.error(f"Backfill error: {e}")
                break

        self.logger.info(
            f"Backfill complete: {total_stored} candles stored for {symbol}"
        )


# Convenience function to run the collector
def run_price_collector():
    """Run the price collector agent"""
    collector = PriceCollectorAgent()
    return collector.execute()


if __name__ == "__main__":
    # Run collector when executed directly
    result = run_price_collector()
    print(f"Collection result: {result}")

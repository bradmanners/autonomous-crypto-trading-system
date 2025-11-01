"""
Database Connection and Utilities
"""
import logging
from contextlib import contextmanager
from typing import Generator, Optional, Dict, List, Any
from datetime import datetime

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
import redis
import pandas as pd

from config.config import config

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages PostgreSQL/TimescaleDB connections"""

    def __init__(self):
        self.engine = create_engine(
            config.database_url,
            poolclass=QueuePool,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,  # Verify connections before using
            echo=config.debug_mode
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        logger.info(f"Database engine created: {config.postgres_host}:{config.postgres_port}/{config.postgres_db}")

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Context manager for database sessions

        Usage:
            with db.get_session() as session:
                result = session.execute(...)
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()

    def execute_query(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
        """Execute a query and return results as list of dicts"""
        with self.get_session() as session:
            result = session.execute(text(query), params or {})
            columns = result.keys()
            return [dict(zip(columns, row)) for row in result.fetchall()]

    def execute_df(self, query: str, params: Optional[Dict] = None) -> pd.DataFrame:
        """Execute a query and return results as DataFrame"""
        return pd.read_sql(query, self.engine, params=params)

    def insert_price_data(self, symbol: str, exchange: str, timeframe: str, df: pd.DataFrame):
        """
        Insert OHLCV data into price_data table

        Args:
            symbol: Trading pair (e.g., BTC/USDT)
            exchange: Exchange name (e.g., binance)
            timeframe: Timeframe (e.g., 1h, 4h, 1d)
            df: DataFrame with columns: timestamp, open, high, low, close, volume
        """
        df = df.copy()
        df['symbol'] = symbol
        df['exchange'] = exchange
        df['timeframe'] = timeframe
        df = df.rename(columns={'timestamp': 'time'})

        df.to_sql(
            'price_data',
            self.engine,
            if_exists='append',
            index=False,
            method='multi'
        )
        logger.debug(f"Inserted {len(df)} rows of price data for {symbol} ({timeframe})")

    def get_latest_price(self, symbol: str, timeframe: str = '1h') -> Optional[Dict]:
        """Get the latest price data for a symbol"""
        query = """
        SELECT * FROM price_data
        WHERE symbol = :symbol AND timeframe = :timeframe
        ORDER BY time DESC
        LIMIT 1
        """
        results = self.execute_query(query, {'symbol': symbol, 'timeframe': timeframe})
        return results[0] if results else None

    def get_price_history(
        self,
        symbol: str,
        timeframe: str,
        start_time: datetime,
        end_time: Optional[datetime] = None
    ) -> pd.DataFrame:
        """Get historical price data"""
        query = """
        SELECT time, open, high, low, close, volume
        FROM price_data
        WHERE symbol = :symbol
            AND timeframe = :timeframe
            AND time >= :start_time
        """
        params = {
            'symbol': symbol,
            'timeframe': timeframe,
            'start_time': start_time
        }

        if end_time:
            query += " AND time <= :end_time"
            params['end_time'] = end_time

        query += " ORDER BY time ASC"

        return self.execute_df(query, params)

    def insert_sentiment_data(self, data: Dict[str, Any]):
        """Insert sentiment data"""
        with self.get_session() as session:
            query = text("""
                INSERT INTO sentiment_data
                (time, source, symbol, content, sentiment_score, magnitude, keywords, metadata)
                VALUES (:time, :source, :symbol, :content, :sentiment_score, :magnitude, :keywords, :metadata)
            """)
            session.execute(query, data)

    def insert_agent_signal(self, agent_name: str, symbol: str, signal: str, confidence: float, reasoning: str):
        """Insert agent signal"""
        with self.get_session() as session:
            query = text("""
                INSERT INTO agent_signals (agent_name, symbol, signal, confidence, reasoning)
                VALUES (:agent_name, :symbol, :signal, :confidence, :reasoning)
            """)
            session.execute(query, {
                'agent_name': agent_name,
                'symbol': symbol,
                'signal': signal,
                'confidence': confidence,
                'reasoning': reasoning
            })

    def get_portfolio_state(self) -> Optional[Dict]:
        """Get latest portfolio state"""
        query = "SELECT * FROM v_latest_portfolio"
        results = self.execute_query(query)
        return results[0] if results else None

    def update_portfolio_state(self, cash: float, total_value: float, positions: List[Dict],
                               portfolio_heat: float, daily_pnl: float, total_pnl: float):
        """Update portfolio state"""
        import json
        with self.get_session() as session:
            query = text("""
                INSERT INTO portfolio_state
                (time, cash, total_value, positions, portfolio_heat, open_positions, daily_pnl, total_pnl)
                VALUES (NOW(), :cash, :total_value, :positions, :portfolio_heat, :open_positions, :daily_pnl, :total_pnl)
            """)
            session.execute(query, {
                'cash': cash,
                'total_value': total_value,
                'positions': json.dumps(positions),
                'portfolio_heat': portfolio_heat,
                'open_positions': len(positions),
                'daily_pnl': daily_pnl,
                'total_pnl': total_pnl
            })

    def insert_prediction(self, symbol: str, model_name: str, horizon_hours: int,
                          predicted_return: float, predicted_direction: str,
                          confidence: float, predicted_price: float):
        """Insert model prediction"""
        with self.get_session() as session:
            query = text("""
                INSERT INTO predictions
                (symbol, model_name, horizon_hours, predicted_return, predicted_direction,
                 confidence, predicted_price)
                VALUES (:symbol, :model_name, :horizon_hours, :predicted_return,
                        :predicted_direction, :confidence, :predicted_price)
                RETURNING id
            """)
            result = session.execute(query, {
                'symbol': symbol,
                'model_name': model_name,
                'horizon_hours': horizon_hours,
                'predicted_return': predicted_return,
                'predicted_direction': predicted_direction,
                'confidence': confidence,
                'predicted_price': predicted_price
            })
            return result.fetchone()[0]


class RedisManager:
    """Manages Redis connections for caching and pub/sub"""

    def __init__(self):
        self.client = redis.Redis(
            host=config.redis_host,
            port=config.redis_port,
            password=config.redis_password,
            db=config.redis_db,
            decode_responses=True
        )
        logger.info(f"Redis client created: {config.redis_host}:{config.redis_port}")

    def set(self, key: str, value: str, expiry: Optional[int] = None):
        """Set a key-value pair with optional expiry (seconds)"""
        self.client.set(key, value, ex=expiry)

    def get(self, key: str) -> Optional[str]:
        """Get value by key"""
        return self.client.get(key)

    def publish(self, channel: str, message: str):
        """Publish message to a channel"""
        self.client.publish(channel, message)

    def subscribe(self, channel: str):
        """Subscribe to a channel (returns pubsub object)"""
        pubsub = self.client.pubsub()
        pubsub.subscribe(channel)
        return pubsub

    def set_json(self, key: str, value: dict, expiry: Optional[int] = None):
        """Set JSON data"""
        import json
        self.set(key, json.dumps(value), expiry)

    def get_json(self, key: str) -> Optional[dict]:
        """Get JSON data"""
        import json
        value = self.get(key)
        return json.loads(value) if value else None


# Global instances
db = DatabaseManager()
redis_client = RedisManager()

"""
Configuration Management for Trading System
"""
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class TradingConfig(BaseSettings):
    """Trading configuration"""
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    # Trading
    trading_mode: str = Field(default="paper", description="paper or live")
    initial_capital: float = Field(default=1000.0)
    max_positions: int = Field(default=3)
    risk_per_trade: float = Field(default=0.02)
    max_portfolio_heat: float = Field(default=0.06)
    daily_loss_limit: float = Field(default=0.05)
    max_drawdown_threshold: float = Field(default=0.15)
    emergency_stop_threshold: float = Field(default=0.25)

    # Assets
    crypto_pairs: str = Field(default="BTC/USDT,ETH/USDT,SOL/USDT")
    base_currency: str = Field(default="USDT")

    @property
    def trading_pairs(self) -> List[str]:
        return [pair.strip() for pair in self.crypto_pairs.split(',')]

    # Binance
    binance_api_key: str = Field(default="")
    binance_api_secret: str = Field(default="")
    binance_testnet: bool = Field(default=True)

    # Claude AI
    anthropic_api_key: str = Field(default="")
    claude_model: str = Field(default="claude-3-5-sonnet-20241022")

    # Database
    postgres_host: str = Field(default="localhost")
    postgres_port: int = Field(default=5432)
    postgres_db: str = Field(default="trading_system")
    postgres_user: str = Field(default="trading_user")
    postgres_password: str = Field(default="changeme")

    @property
    def database_url(self) -> str:
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    # Redis
    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379)
    redis_password: Optional[str] = Field(default=None)
    redis_db: int = Field(default=0)

    # Social Media APIs
    twitter_api_key: str = Field(default="")
    twitter_api_secret: str = Field(default="")
    twitter_bearer_token: str = Field(default="")
    twitter_access_token: str = Field(default="")
    twitter_access_secret: str = Field(default="")

    reddit_client_id: str = Field(default="")
    reddit_client_secret: str = Field(default="")
    reddit_user_agent: str = Field(default="TradingBot/1.0")

    # Data APIs
    cryptopanic_api_key: str = Field(default="")
    fear_greed_api_url: str = Field(default="https://api.alternative.me/fng/")
    alpha_vantage_api_key: str = Field(default="")
    glassnode_api_key: str = Field(default="")
    coingecko_api_key: str = Field(default="")
    news_api_key: str = Field(default="")

    # Email
    email_enabled: bool = Field(default=True)
    email_provider: str = Field(default="sendgrid")
    sendgrid_api_key: str = Field(default="")
    sendgrid_from_email: str = Field(default="")
    notification_email: str = Field(default="")

    smtp_host: str = Field(default="smtp.gmail.com")
    smtp_port: int = Field(default=587)
    smtp_username: str = Field(default="")
    smtp_password: str = Field(default="")
    smtp_from_email: str = Field(default="")

    # Logging
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json")

    # ML Config
    model_retrain_interval: int = Field(default=168)  # hours
    model_lookback_days: int = Field(default=365)
    model_validation_split: float = Field(default=0.2)
    use_gpu: bool = Field(default=False)

    xgboost_n_estimators: int = Field(default=100)
    xgboost_learning_rate: float = Field(default=0.1)
    xgboost_max_depth: int = Field(default=6)

    feature_window_hours: int = Field(default=168)

    # Agent Config
    data_collection_interval: int = Field(default=3600)  # seconds
    data_retention_days: int = Field(default=365)
    orchestrator_decision_threshold: float = Field(default=0.6)
    ci_proposal_interval: int = Field(default=86400)  # seconds
    ci_backtest_days: int = Field(default=30)

    # Risk Management
    stop_loss_atr_multiplier: float = Field(default=2.0)
    trailing_stop_enabled: bool = Field(default=True)
    take_profit_r_multiple: float = Field(default=2.0)
    kelly_fraction: float = Field(default=0.25)

    # Backtesting
    backtest_start_date: str = Field(default="2023-01-01")
    backtest_end_date: str = Field(default="2024-12-31")
    backtest_initial_capital: float = Field(default=1000.0)
    backtest_commission: float = Field(default=0.001)

    # System
    timezone: str = Field(default="UTC")
    debug_mode: bool = Field(default=False)
    environment: str = Field(default="development")

    # Feature Flags
    enable_sentiment_analysis: bool = Field(default=True)
    enable_onchain_analysis: bool = Field(default=True)
    enable_macro_analysis: bool = Field(default=True)
    enable_trump_monitoring: bool = Field(default=True)
    enable_ml_predictions: bool = Field(default=True)
    enable_continuous_improvement: bool = Field(default=True)

    # Trump/Political
    trump_twitter_accounts: str = Field(default="@realDonaldTrump,@POTUS,@WhiteHouse")
    political_keywords: str = Field(default="tariff,china,fed,federal reserve,crypto,bitcoin")
    geopolitical_keywords: str = Field(default="ukraine,russia,israel,iran,china,taiwan")

    @property
    def trump_accounts(self) -> List[str]:
        return [acc.strip() for acc in self.trump_twitter_accounts.split(',')]

    @property
    def political_keywords_list(self) -> List[str]:
        return [kw.strip() for kw in self.political_keywords.split(',')]


# Global config instance
config = TradingConfig()

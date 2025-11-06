-- ============================================
-- Multi-Asset Schema Extension
-- Extends existing database to support stocks, forex, commodities, etc.
-- ============================================

-- Add asset_class column to price_data if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'price_data' AND column_name = 'asset_class'
    ) THEN
        ALTER TABLE price_data ADD COLUMN asset_class VARCHAR(20) DEFAULT 'crypto';
        CREATE INDEX IF NOT EXISTS idx_price_data_asset_class ON price_data (asset_class, time DESC);
    END IF;
END $$;

-- Add asset_class to trading_decisions
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'trading_decisions' AND column_name = 'asset_class'
    ) THEN
        ALTER TABLE trading_decisions ADD COLUMN asset_class VARCHAR(20) DEFAULT 'crypto';
        CREATE INDEX IF NOT EXISTS idx_trading_decisions_asset_class ON trading_decisions (asset_class, timestamp DESC);
    END IF;
END $$;

-- Add asset_class to agent_signals
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'agent_signals' AND column_name = 'asset_class'
    ) THEN
        ALTER TABLE agent_signals ADD COLUMN asset_class VARCHAR(20) DEFAULT 'crypto';
        CREATE INDEX IF NOT EXISTS idx_agent_signals_asset_class ON agent_signals (asset_class, time DESC);
    END IF;
END $$;

-- Add asset_class to predictions
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'predictions' AND column_name = 'asset_class'
    ) THEN
        ALTER TABLE predictions ADD COLUMN asset_class VARCHAR(20) DEFAULT 'crypto';
        CREATE INDEX IF NOT EXISTS idx_predictions_asset_class ON predictions (asset_class, time DESC);
    END IF;
END $$;

-- Add asset_class to trades
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'trades' AND column_name = 'asset_class'
    ) THEN
        ALTER TABLE trades ADD COLUMN asset_class VARCHAR(20) DEFAULT 'crypto';
        CREATE INDEX IF NOT EXISTS idx_trades_asset_class ON trades (asset_class, entry_time DESC);
    END IF;
END $$;

-- ============================================
-- Asset Registry Table
-- ============================================
CREATE TABLE IF NOT EXISTS asset_registry (
    symbol VARCHAR(20) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    asset_class VARCHAR(20) NOT NULL,
    enabled BOOLEAN DEFAULT FALSE,
    exchange VARCHAR(50),
    min_trade_size NUMERIC(30, 8),
    price_precision INTEGER,
    volume_precision INTEGER,
    volatility_score INTEGER,
    leverage INTEGER,  -- For leveraged ETFs
    pip_value NUMERIC(10, 8),  -- For forex
    contract_size INTEGER,  -- For commodities/futures
    leading_indicators TEXT[],
    data_sources TEXT[],
    risk_parameters JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_asset_registry_class ON asset_registry (asset_class);
CREATE INDEX IF NOT EXISTS idx_asset_registry_enabled ON asset_registry (enabled, asset_class);

-- ============================================
-- Asset Class Configuration Table
-- ============================================
CREATE TABLE IF NOT EXISTS asset_class_config (
    asset_class VARCHAR(20) PRIMARY KEY,
    enabled BOOLEAN DEFAULT FALSE,
    max_allocation NUMERIC(5, 4) NOT NULL,  -- e.g., 0.40 = 40%
    default_position_size NUMERIC(5, 4) NOT NULL,
    max_positions INTEGER NOT NULL,
    risk_multiplier NUMERIC(5, 4) NOT NULL,
    phase_number INTEGER,
    activated_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert default asset class configs
INSERT INTO asset_class_config (asset_class, enabled, max_allocation, default_position_size, max_positions, risk_multiplier, phase_number)
VALUES
    ('crypto', TRUE, 1.0, 0.10, 5, 1.0, 0),
    ('stocks', FALSE, 0.40, 0.08, 5, 0.8, 1),
    ('leveraged_etfs', FALSE, 0.20, 0.05, 3, 0.5, 2),
    ('forex', FALSE, 0.30, 0.10, 4, 1.2, 3),
    ('commodities', FALSE, 0.25, 0.08, 3, 1.1, 5),
    ('meme_stocks', FALSE, 0.05, 0.02, 3, 0.3, 6)
ON CONFLICT (asset_class) DO NOTHING;

-- ============================================
-- Data Source Registry
-- ============================================
CREATE TABLE IF NOT EXISTS data_source_registry (
    source_name VARCHAR(50) PRIMARY KEY,
    source_type VARCHAR(30) NOT NULL,  -- stocks_options, forex, sentiment, etc.
    enabled BOOLEAN DEFAULT FALSE,
    api_key_configured BOOLEAN DEFAULT FALSE,
    cost_per_month NUMERIC(10, 2),
    rate_limit INTEGER,
    rate_limit_period VARCHAR(20),  -- second, minute, hour, day
    last_call TIMESTAMPTZ,
    call_count_today INTEGER DEFAULT 0,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert default data sources
INSERT INTO data_source_registry (source_name, source_type, enabled, cost_per_month, rate_limit, rate_limit_period)
VALUES
    ('ccxt_binance', 'crypto', TRUE, 0, 1200, 'minute'),
    ('glassnode', 'crypto', TRUE, 0, 10, 'minute'),
    ('polygon_io', 'stocks_options', FALSE, 250, 5, 'second'),
    ('alpha_vantage', 'stocks_forex', FALSE, 0, 5, 'minute'),
    ('oanda_api', 'forex_commodities', FALSE, 0, 100, 'second'),
    ('reddit_api', 'sentiment', FALSE, 0, 60, 'minute'),
    ('twitter_api', 'sentiment', FALSE, 0, 500, 'hour'),
    ('eia_api', 'energy_data', FALSE, 0, 1000, 'hour'),
    ('fred_api', 'economic_data', FALSE, 0, 120, 'minute')
ON CONFLICT (source_name) DO NOTHING;

-- ============================================
-- Phase Activation Log
-- ============================================
CREATE TABLE IF NOT EXISTS phase_activation_log (
    id SERIAL PRIMARY KEY,
    phase_name VARCHAR(50) NOT NULL,
    phase_number INTEGER NOT NULL,
    activated_at TIMESTAMPTZ DEFAULT NOW(),
    performance_metrics JSONB,  -- Metrics that triggered activation
    assets_activated TEXT[],
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_phase_activation_time ON phase_activation_log (activated_at DESC);

-- ============================================
-- Asset Performance Metrics
-- ============================================
CREATE TABLE IF NOT EXISTS asset_performance (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    asset_class VARCHAR(20) NOT NULL,
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    total_trades INTEGER,
    winning_trades INTEGER,
    losing_trades INTEGER,
    total_pnl NUMERIC(20, 8),
    win_rate NUMERIC(5, 4),
    avg_win NUMERIC(20, 8),
    avg_loss NUMERIC(20, 8),
    profit_factor NUMERIC(10, 4),
    sharpe_ratio NUMERIC(10, 4),
    max_drawdown NUMERIC(5, 4),
    volatility NUMERIC(10, 4),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_asset_perf_symbol ON asset_performance (symbol, period_end DESC);
CREATE INDEX IF NOT EXISTS idx_asset_perf_class ON asset_performance (asset_class, period_end DESC);

-- ============================================
-- Leading Indicators Data
-- ============================================
CREATE TABLE IF NOT EXISTS leading_indicators (
    id SERIAL PRIMARY KEY,
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    symbol VARCHAR(20),  -- NULL for market-wide indicators
    indicator_type VARCHAR(50) NOT NULL,  -- options_flow, sentiment, macro, etc.
    indicator_name VARCHAR(100) NOT NULL,
    value NUMERIC(20, 8),
    metadata JSONB,
    source VARCHAR(50)
);

CREATE INDEX IF NOT EXISTS idx_leading_indicators_time ON leading_indicators (time DESC);
CREATE INDEX IF NOT EXISTS idx_leading_indicators_symbol ON leading_indicators (symbol, time DESC);
CREATE INDEX IF NOT EXISTS idx_leading_indicators_type ON leading_indicators (indicator_type, time DESC);

-- Convert to hypertable for time-series performance
SELECT create_hypertable('leading_indicators', 'time', if_not_exists => TRUE);

-- ============================================
-- Social Sentiment Data (Reddit, Twitter)
-- ============================================
CREATE TABLE IF NOT EXISTS social_sentiment (
    id SERIAL PRIMARY KEY,
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    platform VARCHAR(20) NOT NULL,  -- reddit, twitter, stocktwits
    symbol VARCHAR(20),
    mention_count INTEGER,
    sentiment_score NUMERIC(5, 4),  -- -1 to +1
    volume_change_pct NUMERIC(10, 4),  -- % change in mentions
    top_keywords TEXT[],
    sentiment_distribution JSONB,  -- {bullish: 0.6, bearish: 0.2, neutral: 0.2}
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_social_sentiment_time ON social_sentiment (time DESC);
CREATE INDEX IF NOT EXISTS idx_social_sentiment_symbol ON social_sentiment (symbol, time DESC);
CREATE INDEX IF NOT EXISTS idx_social_sentiment_platform ON social_sentiment (platform, time DESC);

SELECT create_hypertable('social_sentiment', 'time', if_not_exists => TRUE);

-- ============================================
-- Options Flow Data (For stocks with options)
-- ============================================
CREATE TABLE IF NOT EXISTS options_flow (
    id SERIAL PRIMARY KEY,
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    symbol VARCHAR(20) NOT NULL,
    option_type VARCHAR(10) NOT NULL,  -- CALL or PUT
    strike NUMERIC(20, 2) NOT NULL,
    expiry DATE NOT NULL,
    volume INTEGER,
    open_interest INTEGER,
    implied_volatility NUMERIC(10, 4),
    flow_type VARCHAR(20),  -- unusual_activity, sweep, block
    premium_usd NUMERIC(20, 2),
    sentiment VARCHAR(10),  -- bullish, bearish, neutral
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_options_flow_time ON options_flow (time DESC);
CREATE INDEX IF NOT EXISTS idx_options_flow_symbol ON options_flow (symbol, time DESC);

SELECT create_hypertable('options_flow', 'time', if_not_exists => TRUE);

-- ============================================
-- Economic Calendar Events
-- ============================================
CREATE TABLE IF NOT EXISTS economic_calendar (
    id SERIAL PRIMARY KEY,
    event_time TIMESTAMPTZ NOT NULL,
    country VARCHAR(3) NOT NULL,  -- USD, EUR, GBP, etc.
    event_name VARCHAR(200) NOT NULL,
    importance VARCHAR(10),  -- low, medium, high
    actual_value NUMERIC(20, 4),
    forecast_value NUMERIC(20, 4),
    previous_value NUMERIC(20, 4),
    currency_impact VARCHAR(3),  -- Which currency primarily affected
    volatility_expected BOOLEAN,
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_econ_calendar_time ON economic_calendar (event_time DESC);
CREATE INDEX IF NOT EXISTS idx_econ_calendar_importance ON economic_calendar (importance, event_time DESC);

-- ============================================
-- Asset Correlation Matrix
-- ============================================
CREATE TABLE IF NOT EXISTS asset_correlations (
    id SERIAL PRIMARY KEY,
    calculated_at TIMESTAMPTZ DEFAULT NOW(),
    symbol_1 VARCHAR(20) NOT NULL,
    symbol_2 VARCHAR(20) NOT NULL,
    correlation NUMERIC(5, 4),  -- -1 to +1
    period_days INTEGER,  -- Lookback period
    data_points INTEGER,  -- Number of observations used
    UNIQUE(symbol_1, symbol_2, period_days)
);

CREATE INDEX IF NOT EXISTS idx_asset_corr_symbols ON asset_correlations (symbol_1, symbol_2);

-- ============================================
-- Phase Requirements Check View
-- ============================================
CREATE OR REPLACE VIEW v_phase_readiness AS
WITH crypto_performance AS (
    SELECT
        COUNT(DISTINCT DATE(timestamp)) as profitable_days,
        AVG(confidence) as avg_confidence,
        COUNT(*) as total_decisions
    FROM trading_decisions
    WHERE asset_class = 'crypto'
        AND timestamp >= NOW() - INTERVAL '60 days'
)
SELECT
    'phase_1_stocks' as phase_name,
    1 as phase_number,
    (SELECT profitable_days FROM crypto_performance) as crypto_profitable_days,
    0.0 as sharpe_ratio,  -- TODO: Calculate from trades table
    0.0 as max_drawdown,
    0.0 as win_rate,
    CASE
        WHEN (SELECT profitable_days FROM crypto_performance) >= 30 THEN TRUE
        ELSE FALSE
    END as requirements_met;

-- ============================================
-- Update trading_decisions table structure if needed
-- ============================================

-- Add exchange column if it doesn't exist (needed for stocks/forex)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'trading_decisions' AND column_name = 'exchange'
    ) THEN
        ALTER TABLE trading_decisions ADD COLUMN exchange VARCHAR(50);
    END IF;
END $$;

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Multi-asset schema extension completed successfully!';
    RAISE NOTICE 'Total asset classes configured: 6';
    RAISE NOTICE 'Current enabled classes: crypto';
    RAISE NOTICE 'Ready for Phase 1-6 expansion';
END $$;

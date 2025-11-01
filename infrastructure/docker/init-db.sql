-- ============================================
-- Autonomous Crypto Trading System - Database Schema
-- ============================================

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- ============================================
-- Price Data (OHLCV)
-- ============================================
CREATE TABLE IF NOT EXISTS price_data (
    time TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    exchange VARCHAR(20) NOT NULL,
    open NUMERIC(20, 8) NOT NULL,
    high NUMERIC(20, 8) NOT NULL,
    low NUMERIC(20, 8) NOT NULL,
    close NUMERIC(20, 8) NOT NULL,
    volume NUMERIC(30, 8) NOT NULL,
    timeframe VARCHAR(10) NOT NULL, -- 1m, 5m, 15m, 1h, 4h, 1d
    PRIMARY KEY (time, symbol, timeframe)
);

-- Convert to hypertable
SELECT create_hypertable('price_data', 'time', if_not_exists => TRUE);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_price_data_symbol_time ON price_data (symbol, time DESC);
CREATE INDEX IF NOT EXISTS idx_price_data_timeframe ON price_data (timeframe, time DESC);

-- ============================================
-- Sentiment Data
-- ============================================
CREATE TABLE IF NOT EXISTS sentiment_data (
    id SERIAL PRIMARY KEY,
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source VARCHAR(50) NOT NULL, -- twitter, reddit, news, fear_greed
    symbol VARCHAR(20), -- NULL for general market sentiment
    content TEXT,
    sentiment_score NUMERIC(5, 4), -- -1 to +1
    magnitude NUMERIC(5, 4), -- 0 to 1 (strength)
    keywords TEXT[],
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_sentiment_time ON sentiment_data (time DESC);
CREATE INDEX IF NOT EXISTS idx_sentiment_symbol_time ON sentiment_data (symbol, time DESC);
CREATE INDEX IF NOT EXISTS idx_sentiment_source ON sentiment_data (source, time DESC);

-- ============================================
-- On-Chain Data
-- ============================================
CREATE TABLE IF NOT EXISTS onchain_data (
    time TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    exchange_inflow NUMERIC(30, 8),
    exchange_outflow NUMERIC(30, 8),
    whale_transactions INTEGER,
    active_addresses INTEGER,
    network_hash_rate NUMERIC(30, 8),
    mvrv_ratio NUMERIC(10, 4),
    nvt_ratio NUMERIC(10, 4),
    metadata JSONB,
    PRIMARY KEY (time, symbol)
);

SELECT create_hypertable('onchain_data', 'time', if_not_exists => TRUE);

-- ============================================
-- Macro Economic Data
-- ============================================
CREATE TABLE IF NOT EXISTS macro_data (
    time TIMESTAMPTZ NOT NULL PRIMARY KEY,
    dxy NUMERIC(10, 4), -- Dollar Index
    vix NUMERIC(10, 4), -- Volatility Index
    sp500_close NUMERIC(12, 4),
    nasdaq_close NUMERIC(12, 4),
    gold_price NUMERIC(12, 4),
    oil_price NUMERIC(12, 4),
    us_10y_yield NUMERIC(6, 4),
    metadata JSONB
);

SELECT create_hypertable('macro_data', 'time', if_not_exists => TRUE);

-- ============================================
-- News & Events
-- ============================================
CREATE TABLE IF NOT EXISTS news_events (
    id SERIAL PRIMARY KEY,
    time TIMESTAMPTZ NOT NULL,
    source VARCHAR(100) NOT NULL,
    title TEXT NOT NULL,
    content TEXT,
    url TEXT,
    symbols VARCHAR(20)[],
    sentiment_score NUMERIC(5, 4),
    importance VARCHAR(20), -- low, medium, high, critical
    event_type VARCHAR(50), -- regulatory, economic, technical, political
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_news_time ON news_events (time DESC);
CREATE INDEX IF NOT EXISTS idx_news_symbols ON news_events USING GIN (symbols);
CREATE INDEX IF NOT EXISTS idx_news_importance ON news_events (importance, time DESC);

-- ============================================
-- Political Events (Trump, Government)
-- ============================================
CREATE TABLE IF NOT EXISTS political_events (
    id SERIAL PRIMARY KEY,
    time TIMESTAMPTZ NOT NULL,
    source VARCHAR(100) NOT NULL, -- twitter, official, news
    author VARCHAR(100), -- @realDonaldTrump, etc.
    content TEXT NOT NULL,
    event_type VARCHAR(50), -- tweet, announcement, policy, speech
    topics VARCHAR(50)[], -- crypto, fed, tariff, china, etc.
    sentiment_score NUMERIC(5, 4),
    market_impact_score NUMERIC(5, 4), -- predicted impact -1 to +1
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_political_time ON political_events (time DESC);
CREATE INDEX IF NOT EXISTS idx_political_topics ON political_events USING GIN (topics);

-- ============================================
-- Technical Indicators (Calculated)
-- ============================================
CREATE TABLE IF NOT EXISTS technical_indicators (
    time TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    -- Trend Indicators
    ema_9 NUMERIC(20, 8),
    ema_21 NUMERIC(20, 8),
    ema_50 NUMERIC(20, 8),
    ema_200 NUMERIC(20, 8),
    macd NUMERIC(20, 8),
    macd_signal NUMERIC(20, 8),
    macd_histogram NUMERIC(20, 8),
    adx NUMERIC(10, 4),
    -- Momentum Indicators
    rsi_14 NUMERIC(10, 4),
    stoch_k NUMERIC(10, 4),
    stoch_d NUMERIC(10, 4),
    roc NUMERIC(10, 4),
    -- Volatility Indicators
    bb_upper NUMERIC(20, 8),
    bb_middle NUMERIC(20, 8),
    bb_lower NUMERIC(20, 8),
    atr NUMERIC(20, 8),
    -- Volume Indicators
    obv NUMERIC(30, 8),
    vwap NUMERIC(20, 8),
    PRIMARY KEY (time, symbol, timeframe)
);

SELECT create_hypertable('technical_indicators', 'time', if_not_exists => TRUE);

-- ============================================
-- Features (ML Input)
-- ============================================
CREATE TABLE IF NOT EXISTS ml_features (
    time TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    feature_set VARCHAR(50) NOT NULL, -- v1, v2, etc.
    features JSONB NOT NULL, -- All features as JSON
    target NUMERIC(10, 8), -- Future return (for training)
    PRIMARY KEY (time, symbol, feature_set)
);

SELECT create_hypertable('ml_features', 'time', if_not_exists => TRUE);

-- ============================================
-- Agent Signals
-- ============================================
CREATE TABLE IF NOT EXISTS agent_signals (
    id SERIAL PRIMARY KEY,
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    agent_name VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    signal VARCHAR(20) NOT NULL, -- BUY, SELL, HOLD, SHORT
    confidence NUMERIC(5, 4) NOT NULL, -- 0 to 1
    reasoning TEXT,
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_signals_time ON agent_signals (time DESC);
CREATE INDEX IF NOT EXISTS idx_signals_agent_symbol ON agent_signals (agent_name, symbol, time DESC);

-- ============================================
-- Agent Executions (Logging)
-- ============================================
CREATE TABLE IF NOT EXISTS agent_executions (
    id SERIAL PRIMARY KEY,
    agent_name VARCHAR(50) NOT NULL,
    agent_type VARCHAR(30) NOT NULL,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    duration_seconds NUMERIC(10, 2) NOT NULL,
    success BOOLEAN NOT NULL,
    error_message TEXT,
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_agent_executions_time ON agent_executions (start_time DESC);
CREATE INDEX IF NOT EXISTS idx_agent_executions_agent ON agent_executions (agent_name, start_time DESC);
CREATE INDEX IF NOT EXISTS idx_agent_executions_success ON agent_executions (success, start_time DESC);

-- ============================================
-- Portfolio State
-- ============================================
CREATE TABLE IF NOT EXISTS portfolio_state (
    time TIMESTAMPTZ NOT NULL PRIMARY KEY,
    cash NUMERIC(20, 8) NOT NULL,
    total_value NUMERIC(20, 8) NOT NULL,
    positions JSONB NOT NULL, -- Array of position objects
    portfolio_heat NUMERIC(5, 4), -- Current total risk %
    open_positions INTEGER,
    daily_pnl NUMERIC(20, 8),
    total_pnl NUMERIC(20, 8)
);

SELECT create_hypertable('portfolio_state', 'time', if_not_exists => TRUE);

-- ============================================
-- Trades (Executed)
-- ============================================
CREATE TABLE IF NOT EXISTS trades (
    id SERIAL PRIMARY KEY,
    entry_time TIMESTAMPTZ NOT NULL,
    exit_time TIMESTAMPTZ,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL, -- LONG, SHORT
    entry_price NUMERIC(20, 8) NOT NULL,
    exit_price NUMERIC(20, 8),
    quantity NUMERIC(30, 8) NOT NULL,
    position_size NUMERIC(20, 8) NOT NULL, -- In USD
    stop_loss NUMERIC(20, 8),
    take_profit NUMERIC(20, 8),
    realized_pnl NUMERIC(20, 8),
    realized_pnl_pct NUMERIC(10, 4),
    fees NUMERIC(20, 8),
    status VARCHAR(20) NOT NULL, -- OPEN, CLOSED, STOPPED
    strategy VARCHAR(50),
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_trades_entry_time ON trades (entry_time DESC);
CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades (symbol, entry_time DESC);
CREATE INDEX IF NOT EXISTS idx_trades_status ON trades (status);

-- ============================================
-- Orders
-- ============================================
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(100) UNIQUE, -- Exchange order ID
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL, -- BUY, SELL
    order_type VARCHAR(20) NOT NULL, -- MARKET, LIMIT, STOP_LOSS
    quantity NUMERIC(30, 8) NOT NULL,
    price NUMERIC(20, 8),
    stop_price NUMERIC(20, 8),
    status VARCHAR(20) NOT NULL, -- PENDING, FILLED, PARTIAL, CANCELLED, REJECTED
    filled_quantity NUMERIC(30, 8),
    filled_price NUMERIC(20, 8),
    fees NUMERIC(20, 8),
    trade_id INTEGER REFERENCES trades(id),
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_orders_time ON orders (time DESC);
CREATE INDEX IF NOT EXISTS idx_orders_symbol ON orders (symbol, time DESC);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders (status);

-- ============================================
-- Predictions
-- ============================================
CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY,
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    symbol VARCHAR(20) NOT NULL,
    model_name VARCHAR(50) NOT NULL,
    model_version VARCHAR(20),
    horizon_hours INTEGER NOT NULL, -- Prediction horizon
    predicted_return NUMERIC(10, 8), -- Expected return %
    predicted_direction VARCHAR(10), -- UP, DOWN, NEUTRAL
    confidence NUMERIC(5, 4),
    predicted_price NUMERIC(20, 8),
    actual_return NUMERIC(10, 8), -- Filled after prediction horizon
    actual_price NUMERIC(20, 8),
    prediction_error NUMERIC(10, 8),
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_predictions_time ON predictions (time DESC);
CREATE INDEX IF NOT EXISTS idx_predictions_symbol ON predictions (symbol, time DESC);
CREATE INDEX IF NOT EXISTS idx_predictions_model ON predictions (model_name, time DESC);

-- ============================================
-- Model Performance
-- ============================================
CREATE TABLE IF NOT EXISTS model_performance (
    id SERIAL PRIMARY KEY,
    evaluation_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    model_name VARCHAR(50) NOT NULL,
    model_version VARCHAR(20) NOT NULL,
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    accuracy NUMERIC(5, 4),
    precision_score NUMERIC(5, 4),
    recall NUMERIC(5, 4),
    f1_score NUMERIC(5, 4),
    mae NUMERIC(10, 8), -- Mean Absolute Error
    rmse NUMERIC(10, 8), -- Root Mean Squared Error
    sharpe_ratio NUMERIC(10, 4),
    total_predictions INTEGER,
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_model_perf_time ON model_performance (evaluation_time DESC);
CREATE INDEX IF NOT EXISTS idx_model_perf_name ON model_performance (model_name, evaluation_time DESC);

-- ============================================
-- Continuous Improvement Proposals
-- ============================================
CREATE TABLE IF NOT EXISTS improvement_proposals (
    id SERIAL PRIMARY KEY,
    created_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    proposal_type VARCHAR(50) NOT NULL, -- strategy, parameter, feature, model
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    rationale TEXT,
    expected_impact TEXT,
    backtest_results JSONB,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING', -- PENDING, APPROVED, REJECTED, IMPLEMENTED
    reviewed_time TIMESTAMPTZ,
    reviewed_by VARCHAR(100),
    implementation_notes TEXT,
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_proposals_time ON improvement_proposals (created_time DESC);
CREATE INDEX IF NOT EXISTS idx_proposals_status ON improvement_proposals (status);

-- ============================================
-- System Metrics
-- ============================================
CREATE TABLE IF NOT EXISTS system_metrics (
    time TIMESTAMPTZ NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    value NUMERIC(20, 8) NOT NULL,
    unit VARCHAR(20),
    tags JSONB,
    PRIMARY KEY (time, metric_name)
);

SELECT create_hypertable('system_metrics', 'time', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_metrics_name ON system_metrics (metric_name, time DESC);

-- ============================================
-- Audit Log
-- ============================================
CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_type VARCHAR(50) NOT NULL,
    actor VARCHAR(100), -- agent name or user
    action VARCHAR(100) NOT NULL,
    details JSONB,
    success BOOLEAN DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_log (time DESC);
CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_log (event_type, time DESC);

-- ============================================
-- Views for Common Queries
-- ============================================

-- Latest portfolio state
CREATE OR REPLACE VIEW v_latest_portfolio AS
SELECT * FROM portfolio_state
ORDER BY time DESC
LIMIT 1;

-- Open positions
CREATE OR REPLACE VIEW v_open_trades AS
SELECT * FROM trades
WHERE status = 'OPEN'
ORDER BY entry_time DESC;

-- Recent performance (last 30 days)
CREATE OR REPLACE VIEW v_recent_performance AS
SELECT
    DATE(entry_time) as date,
    COUNT(*) as total_trades,
    SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
    SUM(CASE WHEN realized_pnl < 0 THEN 1 ELSE 0 END) as losing_trades,
    SUM(realized_pnl) as total_pnl,
    AVG(realized_pnl) as avg_pnl,
    SUM(CASE WHEN realized_pnl > 0 THEN realized_pnl ELSE 0 END) as total_wins,
    SUM(CASE WHEN realized_pnl < 0 THEN realized_pnl ELSE 0 END) as total_losses
FROM trades
WHERE entry_time > NOW() - INTERVAL '30 days'
    AND status = 'CLOSED'
GROUP BY DATE(entry_time)
ORDER BY date DESC;

-- Agent performance comparison
CREATE OR REPLACE VIEW v_agent_performance AS
SELECT
    agent_name,
    COUNT(*) as total_signals,
    AVG(confidence) as avg_confidence,
    COUNT(*) FILTER (WHERE signal IN ('BUY', 'SELL', 'SHORT')) as actionable_signals
FROM agent_signals
WHERE time > NOW() - INTERVAL '7 days'
GROUP BY agent_name;

-- Prediction accuracy by model
CREATE OR REPLACE VIEW v_prediction_accuracy AS
SELECT
    model_name,
    COUNT(*) as total_predictions,
    AVG(ABS(prediction_error)) as mae,
    SQRT(AVG(prediction_error * prediction_error)) as rmse,
    CORR(predicted_return, actual_return) as correlation
FROM predictions
WHERE actual_return IS NOT NULL
    AND time > NOW() - INTERVAL '30 days'
GROUP BY model_name;

-- ============================================
-- Functions
-- ============================================

-- Calculate Sharpe ratio for a date range
CREATE OR REPLACE FUNCTION calculate_sharpe_ratio(
    start_date TIMESTAMPTZ,
    end_date TIMESTAMPTZ
) RETURNS NUMERIC AS $$
DECLARE
    avg_return NUMERIC;
    std_return NUMERIC;
    sharpe NUMERIC;
BEGIN
    SELECT AVG(realized_pnl_pct), STDDEV(realized_pnl_pct)
    INTO avg_return, std_return
    FROM trades
    WHERE entry_time >= start_date
        AND entry_time <= end_date
        AND status = 'CLOSED';

    IF std_return > 0 THEN
        sharpe := (avg_return * SQRT(252)) / std_return; -- Annualized
    ELSE
        sharpe := 0;
    END IF;

    RETURN sharpe;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- Initial Data / Configuration
-- ============================================

-- Insert initial portfolio state
INSERT INTO portfolio_state (time, cash, total_value, positions, open_positions, total_pnl)
VALUES (NOW(), 1000.00, 1000.00, '[]'::jsonb, 0, 0.00)
ON CONFLICT (time) DO NOTHING;

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Trading system database initialized successfully!';
END $$;

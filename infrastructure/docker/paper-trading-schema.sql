-- Paper Trading Engine Schema
-- Manages simulated order execution, positions, and portfolio tracking

-- =====================================================
-- Paper Trading Orders
-- =====================================================
CREATE TABLE IF NOT EXISTS paper_orders (
    order_id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    asset_class VARCHAR(20) NOT NULL,
    order_type VARCHAR(10) NOT NULL,  -- MARKET, LIMIT
    side VARCHAR(10) NOT NULL,  -- BUY, SELL
    quantity NUMERIC(20, 8) NOT NULL,
    limit_price NUMERIC(20, 8),  -- For limit orders

    -- Execution details
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',  -- PENDING, FILLED, PARTIALLY_FILLED, CANCELLED
    filled_quantity NUMERIC(20, 8) DEFAULT 0,
    avg_fill_price NUMERIC(20, 8),

    -- Fees and costs
    commission NUMERIC(10, 2) DEFAULT 0,
    slippage NUMERIC(10, 2) DEFAULT 0,
    total_cost NUMERIC(20, 8),

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    filled_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,

    -- References
    decision_id INTEGER,  -- Link to trading_decisions
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_paper_orders_symbol ON paper_orders(symbol);
CREATE INDEX IF NOT EXISTS idx_paper_orders_status ON paper_orders(status);
CREATE INDEX IF NOT EXISTS idx_paper_orders_created ON paper_orders(created_at DESC);

-- =====================================================
-- Paper Trading Positions
-- =====================================================
CREATE TABLE IF NOT EXISTS paper_positions (
    position_id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    asset_class VARCHAR(20) NOT NULL,

    -- Position details
    side VARCHAR(10) NOT NULL,  -- LONG, SHORT
    quantity NUMERIC(20, 8) NOT NULL,
    entry_price NUMERIC(20, 8) NOT NULL,
    current_price NUMERIC(20, 8) NOT NULL,

    -- PnL tracking
    unrealized_pnl NUMERIC(20, 8) DEFAULT 0,
    unrealized_pnl_pct NUMERIC(10, 4) DEFAULT 0,

    -- Position sizing
    position_value NUMERIC(20, 8) NOT NULL,
    initial_margin NUMERIC(20, 8),

    -- Timestamps
    opened_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- References
    entry_order_id INTEGER REFERENCES paper_orders(order_id),
    metadata JSONB DEFAULT '{}'::jsonb,

    UNIQUE(symbol, side)  -- One long or short position per symbol
);

CREATE INDEX IF NOT EXISTS idx_paper_positions_symbol ON paper_positions(symbol);

-- =====================================================
-- Paper Trading Trade History (Closed Positions)
-- =====================================================
CREATE TABLE IF NOT EXISTS paper_trades (
    trade_id SERIAL,
    entry_time TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    asset_class VARCHAR(20) NOT NULL,

    -- Trade details
    side VARCHAR(10) NOT NULL,  -- LONG, SHORT
    quantity NUMERIC(20, 8) NOT NULL,
    entry_price NUMERIC(20, 8) NOT NULL,
    exit_price NUMERIC(20, 8) NOT NULL,

    -- PnL
    realized_pnl NUMERIC(20, 8) NOT NULL,
    realized_pnl_pct NUMERIC(10, 4) NOT NULL,
    gross_pnl NUMERIC(20, 8) NOT NULL,
    net_pnl NUMERIC(20, 8) NOT NULL,

    -- Costs
    total_commission NUMERIC(10, 2) DEFAULT 0,
    total_slippage NUMERIC(10, 2) DEFAULT 0,

    -- Duration
    exit_time TIMESTAMPTZ NOT NULL,
    hold_duration INTERVAL,

    -- References
    entry_order_id INTEGER REFERENCES paper_orders(order_id),
    exit_order_id INTEGER REFERENCES paper_orders(order_id),
    position_id INTEGER,

    -- Strategy attribution
    strategy VARCHAR(50),
    signal_confidence NUMERIC(5, 4),

    metadata JSONB DEFAULT '{}'::jsonb,

    -- Composite primary key including time column for hypertable
    PRIMARY KEY (trade_id, entry_time)
);

-- Make it a hypertable for time-series queries
SELECT create_hypertable('paper_trades', 'entry_time', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_paper_trades_symbol ON paper_trades(symbol);
CREATE INDEX IF NOT EXISTS idx_paper_trades_exit ON paper_trades(exit_time DESC);

-- =====================================================
-- Paper Trading Portfolio Snapshots
-- =====================================================
CREATE TABLE IF NOT EXISTS paper_portfolio_snapshots (
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Portfolio value
    total_value NUMERIC(20, 8) NOT NULL,
    cash_balance NUMERIC(20, 8) NOT NULL,
    positions_value NUMERIC(20, 8) NOT NULL,

    -- Performance metrics
    total_pnl NUMERIC(20, 8) DEFAULT 0,
    total_pnl_pct NUMERIC(10, 4) DEFAULT 0,
    daily_pnl NUMERIC(20, 8) DEFAULT 0,
    daily_pnl_pct NUMERIC(10, 4) DEFAULT 0,

    -- Position breakdown
    num_positions INTEGER DEFAULT 0,
    long_positions INTEGER DEFAULT 0,
    short_positions INTEGER DEFAULT 0,

    -- Risk metrics
    max_drawdown NUMERIC(10, 4) DEFAULT 0,
    max_drawdown_value NUMERIC(20, 8) DEFAULT 0,
    current_drawdown NUMERIC(10, 4) DEFAULT 0,

    -- Asset class allocation
    allocation JSONB DEFAULT '{}'::jsonb,  -- {crypto: 0.5, stocks: 0.3}

    metadata JSONB DEFAULT '{}'::jsonb
);

-- Make it a hypertable for time-series queries
SELECT create_hypertable('paper_portfolio_snapshots', 'time', if_not_exists => TRUE);

-- =====================================================
-- Paper Trading Configuration
-- =====================================================
CREATE TABLE IF NOT EXISTS paper_trading_config (
    config_id SERIAL PRIMARY KEY,

    -- Account settings
    initial_capital NUMERIC(20, 8) NOT NULL DEFAULT 10000,
    current_capital NUMERIC(20, 8) NOT NULL DEFAULT 10000,

    -- Trading parameters
    max_position_size NUMERIC(5, 4) DEFAULT 0.20,  -- 20% of portfolio per position
    max_portfolio_risk NUMERIC(5, 4) DEFAULT 0.50,  -- 50% max deployed

    -- Fee structure
    commission_pct NUMERIC(5, 4) DEFAULT 0.001,  -- 0.1% per trade
    commission_min NUMERIC(10, 2) DEFAULT 1.0,  -- $1 minimum

    -- Slippage model
    slippage_model VARCHAR(20) DEFAULT 'PERCENTAGE',  -- PERCENTAGE, FIXED, VOLATILITY_BASED
    slippage_pct NUMERIC(5, 4) DEFAULT 0.0005,  -- 0.05% default

    -- Risk management
    stop_loss_pct NUMERIC(5, 4),  -- Default stop loss
    take_profit_pct NUMERIC(5, 4),  -- Default take profit

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    metadata JSONB DEFAULT '{}'::jsonb
);

-- Insert default configuration
INSERT INTO paper_trading_config (
    initial_capital,
    current_capital,
    max_position_size,
    commission_pct,
    slippage_pct
) VALUES (
    10000.00,
    10000.00,
    0.20,
    0.001,
    0.0005
) ON CONFLICT DO NOTHING;

-- =====================================================
-- Helper Functions
-- =====================================================

-- Function to calculate unrealized PnL for a position
CREATE OR REPLACE FUNCTION calculate_position_pnl(
    p_entry_price NUMERIC,
    p_current_price NUMERIC,
    p_quantity NUMERIC,
    p_side VARCHAR
) RETURNS NUMERIC AS $$
DECLARE
    pnl NUMERIC;
BEGIN
    IF p_side = 'LONG' THEN
        pnl := (p_current_price - p_entry_price) * p_quantity;
    ELSE  -- SHORT
        pnl := (p_entry_price - p_current_price) * p_quantity;
    END IF;

    RETURN pnl;
END;
$$ LANGUAGE plpgsql;

-- Function to get current portfolio value
CREATE OR REPLACE FUNCTION get_portfolio_value()
RETURNS TABLE(
    total_value NUMERIC,
    cash_balance NUMERIC,
    positions_value NUMERIC,
    unrealized_pnl NUMERIC
) AS $$
DECLARE
    v_cash NUMERIC;
    v_positions_value NUMERIC;
    v_unrealized_pnl NUMERIC;
BEGIN
    -- Get current cash balance
    SELECT current_capital INTO v_cash
    FROM paper_trading_config
    ORDER BY config_id DESC
    LIMIT 1;

    -- Get total positions value and unrealized PnL
    SELECT
        COALESCE(SUM(pp.position_value + pp.unrealized_pnl), 0),
        COALESCE(SUM(pp.unrealized_pnl), 0)
    INTO v_positions_value, v_unrealized_pnl
    FROM paper_positions pp;

    RETURN QUERY SELECT
        v_cash + v_positions_value,
        v_cash,
        v_positions_value,
        v_unrealized_pnl;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- Views for Common Queries
-- =====================================================

-- Current portfolio overview
CREATE OR REPLACE VIEW v_paper_portfolio_overview AS
SELECT
    pv.total_value,
    pv.cash_balance,
    pv.positions_value,
    pv.unrealized_pnl,
    c.initial_capital,
    (pv.total_value - c.initial_capital) as total_pnl,
    ((pv.total_value - c.initial_capital) / c.initial_capital * 100) as total_return_pct,
    (SELECT COUNT(*) FROM paper_positions) as open_positions,
    (SELECT COUNT(*) FROM paper_trades WHERE exit_time >= NOW() - INTERVAL '24 hours') as trades_today
FROM get_portfolio_value() pv
CROSS JOIN (SELECT * FROM paper_trading_config ORDER BY config_id DESC LIMIT 1) c;

-- Open positions with current PnL
CREATE OR REPLACE VIEW v_paper_open_positions AS
SELECT
    position_id,
    symbol,
    asset_class,
    side,
    quantity,
    entry_price,
    current_price,
    unrealized_pnl,
    unrealized_pnl_pct,
    position_value,
    opened_at,
    (NOW() - opened_at) as hold_duration
FROM paper_positions
ORDER BY unrealized_pnl DESC;

-- Recent trade history with performance
CREATE OR REPLACE VIEW v_paper_recent_trades AS
SELECT
    trade_id,
    symbol,
    asset_class,
    side,
    quantity,
    entry_price,
    exit_price,
    realized_pnl,
    realized_pnl_pct,
    net_pnl,
    total_commission + total_slippage as total_fees,
    entry_time,
    exit_time,
    hold_duration,
    strategy,
    CASE
        WHEN realized_pnl > 0 THEN 'WIN'
        WHEN realized_pnl < 0 THEN 'LOSS'
        ELSE 'BREAKEVEN'
    END as outcome
FROM paper_trades
ORDER BY exit_time DESC
LIMIT 100;

-- Performance metrics
CREATE OR REPLACE VIEW v_paper_performance_metrics AS
WITH trade_stats AS (
    SELECT
        COUNT(*) as total_trades,
        SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
        SUM(CASE WHEN realized_pnl < 0 THEN 1 ELSE 0 END) as losing_trades,
        SUM(realized_pnl) as total_pnl,
        AVG(realized_pnl) as avg_pnl,
        STDDEV(realized_pnl) as pnl_stddev,
        MAX(realized_pnl) as max_win,
        MIN(realized_pnl) as max_loss,
        AVG(EXTRACT(EPOCH FROM hold_duration)/3600) as avg_hold_hours
    FROM paper_trades
    WHERE exit_time >= NOW() - INTERVAL '30 days'
)
SELECT
    total_trades,
    winning_trades,
    losing_trades,
    CASE WHEN total_trades > 0 THEN (winning_trades::NUMERIC / total_trades * 100) ELSE 0 END as win_rate,
    total_pnl,
    avg_pnl,
    pnl_stddev,
    CASE WHEN pnl_stddev > 0 THEN (avg_pnl / pnl_stddev) ELSE 0 END as sharpe_ratio,
    max_win,
    max_loss,
    avg_hold_hours
FROM trade_stats;

COMMENT ON TABLE paper_orders IS 'Paper trading order book with execution simulation';
COMMENT ON TABLE paper_positions IS 'Currently open paper trading positions';
COMMENT ON TABLE paper_trades IS 'Closed paper trading positions with realized PnL';
COMMENT ON TABLE paper_portfolio_snapshots IS 'Historical portfolio value snapshots';
COMMENT ON TABLE paper_trading_config IS 'Paper trading engine configuration';

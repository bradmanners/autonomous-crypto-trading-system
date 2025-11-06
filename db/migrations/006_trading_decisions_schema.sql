-- Migration 006: Add Trading Decisions Table
-- This table stores aggregated trading decisions from multiple agent signals
-- Date: 2025-11-07

-- =====================================================
-- Trading Decisions Table
-- =====================================================
CREATE TABLE IF NOT EXISTS trading_decisions (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    symbol VARCHAR(20) NOT NULL,
    asset_class VARCHAR(20) DEFAULT 'crypto',
    exchange VARCHAR(50),

    -- Decision details
    decision VARCHAR(10) NOT NULL,  -- BUY, SELL, HOLD
    confidence NUMERIC(5, 4) NOT NULL,  -- 0 to 1 (aggregated from agents)
    current_price NUMERIC(20, 8) NOT NULL,

    -- Reasoning
    reasoning TEXT,

    -- Agent consensus data
    num_agents_agreeing INTEGER,
    signal_distribution JSONB,  -- {BUY: 3, SELL: 1, HOLD: 2}

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    entry_metadata JSONB DEFAULT '{}'::jsonb  -- Technical indicators at entry
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_trading_decisions_timestamp ON trading_decisions(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_trading_decisions_symbol ON trading_decisions(symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_trading_decisions_asset_class ON trading_decisions(asset_class, timestamp DESC);

-- =====================================================
-- Add weight column to agent_signals if missing
-- =====================================================
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'agent_signals' AND column_name = 'weight'
    ) THEN
        ALTER TABLE agent_signals ADD COLUMN weight NUMERIC(5, 4) DEFAULT 1.0;
    END IF;
END $$;

-- =====================================================
-- Add timestamp alias to agent_signals for compatibility
-- =====================================================
CREATE OR REPLACE VIEW v_agent_signals_compat AS
SELECT
    id,
    time as timestamp,
    time,
    agent_name,
    symbol,
    signal,
    confidence,
    reasoning,
    metadata,
    COALESCE(weight, 1.0) as weight
FROM agent_signals;

COMMENT ON TABLE trading_decisions IS 'Aggregated trading decisions based on multiple agent signals';
COMMENT ON COLUMN trading_decisions.confidence IS 'Aggregated confidence score from all contributing agents';
COMMENT ON COLUMN trading_decisions.entry_metadata IS 'Technical indicators (RSI, MACD, etc.) at decision time';

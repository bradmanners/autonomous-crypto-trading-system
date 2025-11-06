-- Migration: Add price_forecasts table for AI price predictions
-- Date: 2025-11-07
-- Description: Stores price forecast data from AI models for visualization in Grafana

CREATE TABLE IF NOT EXISTS price_forecasts (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    forecast_time TIMESTAMPTZ NOT NULL,
    forecast_type VARCHAR(20) NOT NULL CHECK (forecast_type IN ('base', 'optimistic', 'pessimistic')),
    predicted_price NUMERIC(20, 8) NOT NULL,
    confidence FLOAT CHECK (confidence >= 0 AND confidence <= 1),
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    model_version VARCHAR(50),
    model_params JSONB,
    CONSTRAINT unique_forecast UNIQUE (symbol, forecast_time, forecast_type, generated_at)
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_price_forecasts_symbol_time
ON price_forecasts(symbol, forecast_time);

CREATE INDEX IF NOT EXISTS idx_price_forecasts_type
ON price_forecasts(forecast_type);

CREATE INDEX IF NOT EXISTS idx_price_forecasts_generated
ON price_forecasts(generated_at DESC);

-- Create view for latest forecasts
CREATE OR REPLACE VIEW v_latest_price_forecasts AS
SELECT DISTINCT ON (symbol, forecast_type)
    id,
    symbol,
    forecast_time,
    forecast_type,
    predicted_price,
    confidence,
    generated_at,
    model_version
FROM price_forecasts
ORDER BY symbol, forecast_type, generated_at DESC;

COMMENT ON TABLE price_forecasts IS 'AI-generated price forecasts for future time periods';
COMMENT ON COLUMN price_forecasts.forecast_type IS 'Type of forecast: base (most likely), optimistic (bullish), pessimistic (bearish)';
COMMENT ON COLUMN price_forecasts.confidence IS 'Model confidence in prediction (0-1)';
COMMENT ON COLUMN price_forecasts.model_params IS 'JSON parameters used for generating this forecast';

-- Migration 008: Prediction Accuracy Views
-- Track how accurate our predictions are vs actual outcomes

-- View: Decision accuracy tracking
-- Compares what we decided vs what actually happened to the price
CREATE OR REPLACE VIEW v_decision_accuracy AS
SELECT
    td.id as decision_id,
    td.symbol,
    td.decision,
    td.confidence,
    td.current_price as price_at_decision,
    td.timestamp as decision_time,

    -- Get price 1 hour later
    (SELECT close
     FROM price_data
     WHERE symbol = td.symbol
       AND time > td.timestamp
       AND timeframe = '1h'
     ORDER BY time ASC
     LIMIT 1) as price_1h_later,

    -- Get price 4 hours later
    (SELECT close
     FROM price_data
     WHERE symbol = td.symbol
       AND time > td.timestamp + INTERVAL '3 hours'
       AND timeframe = '1h'
     ORDER BY time ASC
     LIMIT 1) as price_4h_later,

    -- Get price 24 hours later
    (SELECT close
     FROM price_data
     WHERE symbol = td.symbol
       AND time > td.timestamp + INTERVAL '23 hours'
       AND timeframe = '1h'
     ORDER BY time ASC
     LIMIT 1) as price_24h_later,

    -- Calculate if prediction was correct
    CASE
        WHEN td.decision = 'BUY' THEN
            CASE
                WHEN (SELECT close FROM price_data WHERE symbol = td.symbol AND time > td.timestamp + INTERVAL '23 hours' AND timeframe = '1h' ORDER BY time ASC LIMIT 1) > td.current_price
                THEN 'CORRECT'
                ELSE 'WRONG'
            END
        WHEN td.decision = 'SELL' THEN
            CASE
                WHEN (SELECT close FROM price_data WHERE symbol = td.symbol AND time > td.timestamp + INTERVAL '23 hours' AND timeframe = '1h' ORDER BY time ASC LIMIT 1) < td.current_price
                THEN 'CORRECT'
                ELSE 'WRONG'
            END
        ELSE 'N/A'
    END as prediction_accuracy_24h,

    -- Track if order was executed
    EXISTS(SELECT 1 FROM paper_orders WHERE decision_id = td.id) as was_executed,

    -- Get agent signals that contributed to this decision
    (SELECT json_agg(json_build_object(
        'agent_name', agent_name,
        'signal', signal,
        'confidence', confidence,
        'weight', COALESCE(weight, 1.0)
    ))
     FROM agent_signals
     WHERE symbol = td.symbol
       AND time >= td.timestamp - INTERVAL '5 minutes'
       AND time <= td.timestamp
    ) as contributing_signals

FROM trading_decisions td
WHERE td.timestamp >= NOW() - INTERVAL '7 days'
ORDER BY td.timestamp DESC;


-- View: Agent signal accuracy
-- Track which agents produce the most accurate signals
CREATE OR REPLACE VIEW v_agent_signal_accuracy AS
SELECT
    ags.agent_name,
    ags.symbol,
    ags.signal,
    COUNT(*) as signal_count,

    -- Count correct predictions (where price moved in predicted direction)
    SUM(CASE
        WHEN ags.signal = 'BUY' AND
             (SELECT close FROM price_data WHERE symbol = ags.symbol AND time > ags.time + INTERVAL '23 hours' AND timeframe = '1h' ORDER BY time ASC LIMIT 1) >
             (SELECT close FROM price_data WHERE symbol = ags.symbol AND time >= ags.time AND timeframe = '1h' ORDER BY time ASC LIMIT 1)
        THEN 1
        WHEN ags.signal = 'SELL' AND
             (SELECT close FROM price_data WHERE symbol = ags.symbol AND time > ags.time + INTERVAL '23 hours' AND timeframe = '1h' ORDER BY time ASC LIMIT 1) <
             (SELECT close FROM price_data WHERE symbol = ags.symbol AND time >= ags.time AND timeframe = '1h' ORDER BY time ASC LIMIT 1)
        THEN 1
        ELSE 0
    END) as correct_predictions,

    AVG(ags.confidence) as avg_confidence,
    AVG(ags.weight) as avg_weight,

    -- Calculate accuracy percentage
    ROUND(
        100.0 * SUM(CASE
            WHEN ags.signal = 'BUY' AND
                 (SELECT close FROM price_data WHERE symbol = ags.symbol AND time > ags.time + INTERVAL '23 hours' AND timeframe = '1h' ORDER BY time ASC LIMIT 1) >
                 (SELECT close FROM price_data WHERE symbol = ags.symbol AND time >= ags.time AND timeframe = '1h' ORDER BY time ASC LIMIT 1)
            THEN 1
            WHEN ags.signal = 'SELL' AND
                 (SELECT close FROM price_data WHERE symbol = ags.symbol AND time > ags.time + INTERVAL '23 hours' AND timeframe = '1h' ORDER BY time ASC LIMIT 1) <
                 (SELECT close FROM price_data WHERE symbol = ags.symbol AND time >= ags.time AND timeframe = '1h' ORDER BY time ASC LIMIT 1)
            THEN 1
            ELSE 0
        END) / NULLIF(COUNT(*), 0),
    2) as accuracy_pct

FROM agent_signals ags
WHERE ags.time >= NOW() - INTERVAL '7 days'
  AND ags.signal IN ('BUY', 'SELL')
GROUP BY ags.agent_name, ags.symbol, ags.signal
HAVING COUNT(*) >= 5  -- Only include agents with at least 5 signals
ORDER BY accuracy_pct DESC;


-- View: Lead indicator correlation
-- Which data points correlate with profitable trades
CREATE OR REPLACE VIEW v_lead_indicator_performance AS
WITH trades_with_outcome AS (
    SELECT
        pt.*,
        po.decision_id,
        CASE
            WHEN pt.realized_pnl > 0 THEN 'WIN'
            WHEN pt.realized_pnl < 0 THEN 'LOSS'
            ELSE 'BREAKEVEN'
        END as outcome
    FROM paper_trades pt
    LEFT JOIN paper_orders po ON po.order_id = pt.entry_order_id
    WHERE pt.exit_time >= NOW() - INTERVAL '7 days'
)
SELECT
    pt.symbol,

    -- Average technical indicators for winning trades
    AVG(CASE WHEN pt.outcome = 'WIN' THEN (pt.metadata->>'rsi')::numeric END) as avg_rsi_winning,
    AVG(CASE WHEN pt.outcome = 'LOSS' THEN (pt.metadata->>'rsi')::numeric END) as avg_rsi_losing,

    AVG(CASE WHEN pt.outcome = 'WIN' THEN (pt.metadata->>'macd')::numeric END) as avg_macd_winning,
    AVG(CASE WHEN pt.outcome = 'LOSS' THEN (pt.metadata->>'macd')::numeric END) as avg_macd_losing,

    AVG(CASE WHEN pt.outcome = 'WIN' THEN (pt.metadata->>'volume_ratio')::numeric END) as avg_volume_winning,
    AVG(CASE WHEN pt.outcome = 'LOSS' THEN (pt.metadata->>'volume_ratio')::numeric END) as avg_volume_losing,

    -- Confidence levels
    AVG(CASE WHEN pt.outcome = 'WIN' THEN
        (SELECT confidence FROM trading_decisions WHERE id = pt.decision_id)
    END) as avg_confidence_winning,
    AVG(CASE WHEN pt.outcome = 'LOSS' THEN
        (SELECT confidence FROM trading_decisions WHERE id = pt.decision_id)
    END) as avg_confidence_losing,

    -- Agent agreement
    AVG(CASE WHEN pt.outcome = 'WIN' THEN
        (SELECT COUNT(DISTINCT agent_name)
         FROM agent_signals
         WHERE symbol = pt.symbol
           AND time >= pt.entry_time - INTERVAL '5 minutes'
           AND time <= pt.entry_time)
    END) as avg_agents_agreeing_winning,
    AVG(CASE WHEN pt.outcome = 'LOSS' THEN
        (SELECT COUNT(DISTINCT agent_name)
         FROM agent_signals
         WHERE symbol = pt.symbol
           AND time >= pt.entry_time - INTERVAL '5 minutes'
           AND time <= pt.entry_time)
    END) as avg_agents_agreeing_losing,

    COUNT(CASE WHEN pt.outcome = 'WIN' THEN 1 END) as winning_trades,
    COUNT(CASE WHEN pt.outcome = 'LOSS' THEN 1 END) as losing_trades

FROM trades_with_outcome pt
GROUP BY pt.symbol;


-- View: Prediction vs Reality Timeline
-- Show what we predicted vs what actually happened
CREATE OR REPLACE VIEW v_prediction_vs_reality AS
SELECT
    td.timestamp as prediction_time,
    td.symbol,
    td.decision as predicted_direction,
    td.confidence as prediction_confidence,
    td.current_price as price_at_prediction,

    -- Actual price movement after 1 hour
    ROUND(((
        (SELECT close FROM price_data WHERE symbol = td.symbol AND time > td.timestamp AND timeframe = '1h' ORDER BY time ASC LIMIT 1) -
        td.current_price
    ) / td.current_price * 100)::numeric, 2) as actual_change_1h_pct,

    -- Actual price movement after 4 hours
    ROUND(((
        (SELECT close FROM price_data WHERE symbol = td.symbol AND time > td.timestamp + INTERVAL '3 hours' AND timeframe = '1h' ORDER BY time ASC LIMIT 1) -
        td.current_price
    ) / td.current_price * 100)::numeric, 2) as actual_change_4h_pct,

    -- Actual price movement after 24 hours
    ROUND(((
        (SELECT close FROM price_data WHERE symbol = td.symbol AND time > td.timestamp + INTERVAL '23 hours' AND timeframe = '1h' ORDER BY time ASC LIMIT 1) -
        td.current_price
    ) / td.current_price * 100)::numeric, 2) as actual_change_24h_pct,

    -- Was prediction directionally correct?
    CASE
        WHEN td.decision = 'BUY' AND
             (SELECT close FROM price_data WHERE symbol = td.symbol AND time > td.timestamp + INTERVAL '23 hours' AND timeframe = '1h' ORDER BY time ASC LIMIT 1) > td.current_price
        THEN 'CORRECT'
        WHEN td.decision = 'SELL' AND
             (SELECT close FROM price_data WHERE symbol = td.symbol AND time > td.timestamp + INTERVAL '23 hours' AND timeframe = '1h' ORDER BY time ASC LIMIT 1) < td.current_price
        THEN 'CORRECT'
        WHEN td.decision = 'HOLD'
        THEN 'HOLD'
        ELSE 'WRONG'
    END as outcome,

    -- Did we execute this?
    EXISTS(SELECT 1 FROM paper_orders WHERE decision_id = td.id) as executed

FROM trading_decisions td
WHERE td.timestamp >= NOW() - INTERVAL '7 days'
  AND td.timestamp < NOW() - INTERVAL '1 day'  -- Only show decisions old enough to evaluate
ORDER BY td.timestamp DESC;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_agent_signals_symbol_time ON agent_signals(symbol, time);
CREATE INDEX IF NOT EXISTS idx_trading_decisions_symbol_time ON trading_decisions(symbol, timestamp);
CREATE INDEX IF NOT EXISTS idx_paper_orders_decision ON paper_orders(decision_id);

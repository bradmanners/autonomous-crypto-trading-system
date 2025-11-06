# Paper Trading Performance Dashboard - User Guide

## Quick Access

🔗 **Dashboard URL:** http://localhost:3000/d/paper-trading-performance/paper-trading-performance

**Login:** admin / admin

---

## Dashboard Overview

The Paper Trading Performance dashboard provides **real-time visualization** of all your trading metrics in one place. It auto-refreshes every 30 seconds.

---

## Panels Explained

### 📊 Top Row - Key Metrics (4 Stat Panels)

#### 1. Portfolio Value
- **What it shows:** Current total portfolio value
- **Color coding:**
  - 🔴 Red: < $9,000
  - 🟡 Yellow: $9,000 - $10,000
  - 🟢 Green: > $10,000 (profitable)
- **Includes:** Cash + open positions value

#### 2. Total PnL
- **What it shows:** Total profit/loss since start
- **Color coding:**
  - 🔴 Red: Negative (losing money)
  - 🟡 Yellow: $0 (breakeven)
  - 🟢 Green: Positive (making money)
- **Formula:** Current value - Initial capital ($10,000)

#### 3. Win Rate (Gauge)
- **What it shows:** Percentage of profitable trades
- **Target zones:**
  - 🔴 Red: < 50% (poor performance)
  - 🟡 Yellow: 50-55% (acceptable)
  - 🟢 Green: > 55% (good performance)
- **Goal:** Stay consistently above 55%

#### 4. Open Positions
- **What it shows:** Number of currently open trades
- **Purpose:** Monitor position exposure
- **Max recommended:** 5 positions (based on 20% max per position)

---

### 📈 Portfolio Value Trend (7 Days)

**Multi-line chart showing:**
- 🔵 **Blue line:** Total portfolio value (cash + positions)
- 🟢 **Green line:** Cash balance (available capital)
- 🟠 **Orange line:** Positions value (deployed capital)

**How to read:**
- Upward trend = making money ✅
- Flat line = sideways performance ➖
- Downward trend = losing money ⚠️

**Legend shows:**
- Last value
- Minimum over period
- Maximum over period

---

### 🥧 Trade Outcomes (30 Days)

**Pie chart showing:**
- 🟢 Winning Trades (PnL > 0)
- 🔴 Losing Trades (PnL < 0)
- 🟡 Breakeven (PnL = 0)

**Purpose:** Visual win/loss ratio
**Goal:** Green slice should be > 55% of total

---

### 💰 PnL Trend (7 Days)

**Line chart showing cumulative PnL over time**

**Features:**
- Shows if you're trending profitable
- Threshold line at $0 (breakeven)
- Shaded area shows PnL magnitude

**What to look for:**
- Steady upward slope = consistent profits ✅
- High volatility = risky trading ⚠️
- Downward slope = strategy needs adjustment 🛑

---

### 📋 Performance Metrics Table

**Single-row table with key statistics:**

| Metric | Description | Target |
|--------|-------------|--------|
| **Total Trades** | Number of closed trades | > 20 (for valid sample) |
| **Wins** | Number of profitable trades | - |
| **Losses** | Number of losing trades | - |
| **Win Rate %** | Wins / Total trades | > 55% |
| **Sharpe Ratio** | Risk-adjusted returns | > 1.5 |
| **Avg PnL** | Average profit per trade | > $0 |
| **Best Win** | Largest single profit | - |
| **Worst Loss** | Largest single loss | - |
| **Avg Hold (hrs)** | Average trade duration | - |

**Color coding:**
- 🟢 Green: Meeting targets
- 🟡 Yellow: Close to targets
- 🔴 Red: Below targets

---

### 📊 Open Positions Table

**Shows all currently open trades with:**

| Column | Description | Color Coding |
|--------|-------------|--------------|
| **Symbol** | Trading pair | - |
| **Asset Class** | crypto/stocks/etc | - |
| **Quantity** | Amount held | - |
| **Entry Price** | Price when bought | - |
| **Current Price** | Latest market price | - |
| **Unrealized PnL** | Current profit/loss | 🔴 Red (loss) / 🟡 Yellow (even) / 🟢 Green (profit) |
| **PnL %** | Percentage return | 🔴 Red (loss) / 🟡 Yellow (even) / 🟢 Green (profit) |
| **Hold Duration** | Time since entry | - |

**Sorted by:** Unrealized PnL (best performers at top)

**Purpose:** Monitor which positions are profitable

---

### 📜 Recent Trades Table (Last 20)

**Shows closed trades with:**

| Column | Description | Color Coding |
|--------|-------------|--------------|
| **Symbol** | Trading pair | - |
| **Quantity** | Amount traded | - |
| **Entry** | Entry price | - |
| **Exit** | Exit price | - |
| **Net PnL** | Profit after fees | 🔴 Red (loss) / 🟡 Yellow (even) / 🟢 Green (profit) |
| **PnL %** | Percentage return | 🔴 Red (loss) / 🟡 Yellow (even) / 🟢 Green (profit) |
| **Outcome** | Win/Loss/Even | ✅ WIN / ❌ LOSS / ➖ EVEN |
| **Duration** | Hold time | - |
| **Exit Time** | When closed | - |

**Sorted by:** Exit time (most recent at top)

**Purpose:** Review trade history and patterns

---

### 🎯 Recent Trading Decisions (24 Hours)

**Shows all trading decisions and execution status:**

| Column | Description | Color Coding |
|--------|-------------|--------------|
| **Symbol** | Trading pair | - |
| **Decision** | BUY/SELL/HOLD | 🟢 BUY / 🔴 SELL / 🟡 HOLD |
| **Confidence** | Agent confidence (0-1) | 🔴 < 60% / 🟡 60-75% / 🟢 > 75% |
| **Price** | Price at decision time | - |
| **Reasoning** | Why the decision was made | - |
| **Executed** | Was it traded? | ✅ Yes / ⏳ No (pending/skipped) |
| **Timestamp** | When decision was made | - |

**Sorted by:** Timestamp (most recent at top)

**Purpose:**
- Track what decisions are being made
- See which ones are being executed
- Understand decision reasoning

**Key insights:**
- Executed = Yes → Trade was executed by orchestrator
- Executed = No → Either pending or skipped (confidence too low)

---

## How to Use the Dashboard

### 1. Daily Monitoring Routine

**Every morning, check:**
1. ✅ Portfolio Value - trending up?
2. ✅ Total PnL - positive?
3. ✅ Win Rate - above 55%?
4. ✅ Open Positions - any big losers to close?
5. ✅ Recent Trades - what worked yesterday?

### 2. Weekly Performance Review

**Every week, analyze:**
1. 📈 Portfolio Value Trend - consistent growth?
2. 💰 PnL Trend - steady or volatile?
3. 📋 Performance Metrics - Sharpe ratio improving?
4. 🥧 Trade Outcomes - win rate stable?

### 3. Problem Detection

**Watch for these warning signs:**

⚠️ **Portfolio value dropping consistently**
- Check Recent Trades for pattern of losses
- Review Trading Decisions reasoning
- May need to adjust confidence threshold

⚠️ **Win rate below 50%**
- Strategy not working
- Review Performance Metrics for insights
- Consider pausing trading

⚠️ **Sharpe ratio below 1.0**
- Returns not worth the risk
- Too much volatility
- Need better risk management

⚠️ **Large unrealized losses in Open Positions**
- Consider closing losing positions
- Review entry prices and reasoning
- Adjust position sizing

---

## Dashboard Features

### Auto-Refresh
- **Rate:** Every 30 seconds
- **Purpose:** Real-time monitoring
- **Can be changed:** Top-right corner dropdown

### Time Range
- **Default:** Last 7 days
- **Can be changed:** Top-right corner time picker
- **Options:** Last hour, 6 hours, 12 hours, 24 hours, 7 days, 30 days

### Filtering
- No filters currently (all data shown)
- Future enhancement: Filter by symbol, asset class, strategy

### Export
- Click panel title → More → Export CSV
- Useful for external analysis in Excel/Python

---

## Key Metrics Explained

### Sharpe Ratio
**Formula:** (Average Return - Risk-Free Rate) / Standard Deviation

**What it means:**
- Measures risk-adjusted returns
- Higher = better (more return per unit of risk)
- < 1.0 = Poor (not worth the risk)
- 1.0 - 2.0 = Good
- \> 2.0 = Excellent

**Target:** > 1.5

### Win Rate
**Formula:** Winning Trades / Total Trades × 100

**What it means:**
- Percentage of trades that are profitable
- 50% = Random (coin flip)
- 55% = Good (edge over market)
- 60%+ = Excellent

**Target:** > 55%

**Note:** High win rate doesn't guarantee profit if average loss > average win

### Profit Factor
**Formula:** Total Winning Trades $ / Total Losing Trades $

**What it means:**
- How much you make per dollar lost
- 1.0 = Breakeven
- 1.5 = Good (make $1.50 for every $1 lost)
- 2.0+ = Excellent

**Not currently displayed** (future enhancement)

---

## Common Questions

### Q: Why is my portfolio value lower than initial capital?
**A:** You have unrealized losses in open positions. Check the "Open Positions" table to see which trades are losing money.

### Q: Why are some decisions not executed?
**A:** Decisions are only executed if:
1. Confidence >= 60% (configurable threshold)
2. Sufficient capital available
3. System is running (orchestrator must be active)

Check the "Recent Trading Decisions" table - executed ones show ✅.

### Q: How often does the data update?
**A:**
- Dashboard refreshes: Every 30 seconds
- Portfolio snapshots: Every trading cycle (60 seconds when orchestrator running)
- Position PnL: Updated every trading cycle

### Q: Can I see older data?
**A:** Yes! Change the time range in the top-right corner. Data is stored indefinitely in TimescaleDB.

### Q: Why are some panels empty?
**A:**
- No trades yet → Trade tables will be empty
- No open positions → Open Positions table will be empty
- System just started → Wait for first portfolio snapshot

---

## Troubleshooting

### Dashboard shows "No Data"
**Possible causes:**
1. Trading orchestrator not running → Start it
2. No trades executed yet → Wait for first trade
3. Database connection issue → Check Grafana datasource settings

**Fix:**
```bash
# Check if orchestrator is running
ps aux | grep trading_orchestrator

# If not running, start it:
cd "/path/to/project"
PYTHONPATH=. venv/bin/python trading/trading_orchestrator.py
```

### Metrics not updating
**Check:**
1. Dashboard refresh is on (top-right)
2. Orchestrator is running
3. Decisions are being made (check trading_decisions table)

### Wrong numbers displayed
**Verify:**
1. Time range is correct (top-right)
2. Database has latest data:
```sql
SELECT * FROM v_paper_portfolio_overview;
```

---

## Next Steps

### After reviewing the dashboard:

1. **If performance is good (win rate > 55%, Sharpe > 1.5):**
   - Continue paper trading for full 14 days
   - Monitor daily for consistency
   - Prepare for live trading launch

2. **If performance is poor:**
   - Review "Recent Trades" for patterns
   - Check "Trading Decisions" reasoning
   - Adjust confidence threshold or strategy
   - Consider pausing trading

3. **Track these daily:**
   - Screenshot portfolio value at market close
   - Note any unusual trades
   - Document strategy adjustments

---

## Advanced Usage

### Custom Queries

Access Grafana's Explore tab to run custom queries:

**Portfolio value history:**
```sql
SELECT time, total_value, total_pnl_pct
FROM paper_portfolio_snapshots
ORDER BY time DESC
LIMIT 100;
```

**Win rate by symbol:**
```sql
SELECT
  symbol,
  COUNT(*) as trades,
  ROUND(AVG(CASE WHEN realized_pnl > 0 THEN 1.0 ELSE 0.0 END) * 100, 1) as win_rate_pct
FROM paper_trades
WHERE exit_time >= NOW() - INTERVAL '7 days'
GROUP BY symbol
ORDER BY trades DESC;
```

**Best and worst trades:**
```sql
-- Best trades
SELECT symbol, realized_pnl, exit_time
FROM paper_trades
ORDER BY realized_pnl DESC
LIMIT 5;

-- Worst trades
SELECT symbol, realized_pnl, exit_time
FROM paper_trades
ORDER BY realized_pnl ASC
LIMIT 5;
```

---

## Dashboard Maintenance

### Backup Dashboard
```bash
# Export current dashboard configuration
curl -u admin:admin http://localhost:3000/api/dashboards/uid/paper-trading-performance \
  | jq '.dashboard' > paper-trading-backup.json
```

### Restore Dashboard
```bash
# Import from backup
curl -X POST http://localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -u admin:admin \
  -d @paper-trading-backup.json
```

---

## Summary

**The Paper Trading Performance Dashboard gives you:**
- ✅ Real-time portfolio monitoring
- ✅ Complete trade history
- ✅ Performance metrics tracking
- ✅ Decision execution visibility
- ✅ Win rate and PnL trends
- ✅ Open position monitoring

**Use it to:**
1. Monitor daily performance
2. Identify profitable patterns
3. Detect issues early
4. Validate strategy before live trading
5. Track progress toward targets

**Access:** http://localhost:3000/d/paper-trading-performance/paper-trading-performance

---

*Dashboard Version: 1.0*
*Last Updated: November 1, 2025*
*Auto-refresh: 30 seconds*

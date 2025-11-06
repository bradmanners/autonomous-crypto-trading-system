# System Monitoring & Health Dashboard

**Date:** November 3, 2025
**Status:** ✅ LIVE

---

## Overview

The Paper Trading Performance dashboard now includes comprehensive system monitoring to give you real-time visibility into the health and activity of your multi-agent trading system.

**Dashboard URL:** http://localhost:3000/d/paper-trading-performance/paper-trading-performance

---

## New Dashboard Features

### 1. 🚦 System Health (RAG Status)

**Location:** Top of dashboard (full width)

**What it shows:**
- Overall system status using Red/Amber/Green (RAG) indicators
- Real-time description of system state
- Key metrics at a glance

**Status Indicators:**

#### 🟢 **HEALTHY** - All Systems Operational
```
Criteria:
  - Orchestrator executed < 5 minutes ago
  - 2+ agents active
  - Trading decisions being made

Display:
  "All systems operational"
  Orchestrator: 2.3m ago | Agents: 2 active | Decisions: 5/hr | Signals: 15/hr
```

#### 🟡 **DEGRADED** - System Running but Issues
```
Criteria:
  - Orchestrator executed 5-15 minutes ago
  - 1+ agents active
  - Some activity present

Display:
  "System running but degraded"
  Orchestrator: 12.1m ago | Agents: 1 active | Decisions: 2/hr | Signals: 3/hr
```

#### 🔴 **DOWN** - System Stopped
```
Criteria:
  - Orchestrator last executed > 15 minutes ago
  - No recent agent activity
  - No decisions being made

Display:
  "Orchestrator stopped or stalled"
  Orchestrator: 2235.4m ago | Agents: 0 active | Decisions: 0/hr | Signals: 0/hr
```

---

### 2. 📋 System Activity Log

**Location:** Bottom of dashboard (full width)

**What it shows:**
- Last 15 actions from all system components
- Real-time feed of what the system is doing
- Color-coded status indicators

**Activity Types:**

#### AGENT_EXECUTION
```
Component: Agent Name (Technical Analyst, SentimentAnalyst, Orchestrator)
Status: SUCCESS / ERROR
Description: "analyst executed"
Details: Error message (if failed)

Example:
✅ SUCCESS | AGENT_EXECUTION | Technical Analyst
  analyst executed
```

#### SIGNAL_GENERATED
```
Component: Agent Name
Status: INFO
Description: "buy/sell/hold signal for BTC/USDT"
Details: "Confidence: 75%"

Example:
ℹ️ INFO | SIGNAL_GENERATED | SentimentAnalyst
  buy signal for BTC/USDT
  Confidence: 75%
```

#### TRADING_DECISION
```
Component: Orchestrator
Status: SUCCESS / WARNING / INFO
Description: "BUY/SELL/HOLD symbol"
Details: Confidence + reasoning summary

Status Levels:
- SUCCESS (green): Confidence ≥ 60% (will execute)
- WARNING (yellow): Confidence 50-59% (won't execute)
- INFO (blue): Confidence < 50%

Example:
✅ SUCCESS | TRADING_DECISION | Orchestrator
  BUY BTC/USDT
  Confidence: 61% - Multi-agent consensus (2 agents): Technical (40%): Score 50/100, BUY; Sentiment (60%): Score 28/100, HOLD
```

#### ORDER_EXECUTED
```
Component: Paper Trading
Status: SUCCESS / ERROR / INFO
Description: "BUY/SELL symbol"
Details: Quantity and price

Example:
✅ SUCCESS | ORDER_EXECUTED | Paper Trading
  BUY BTC/USDT
  Qty: 0.01 @ $110617.14
```

---

## Status Icons Legend

| Icon | Status | Color | Meaning |
|------|--------|-------|---------|
| ✅ | SUCCESS | Green | Action completed successfully |
| ❌ | ERROR | Red | Action failed or system error |
| ⚠️ | WARNING | Yellow | Action completed with warnings |
| ℹ️ | INFO | Blue | Informational action |

---

## How to Use System Monitoring

### Daily Health Check

**Every morning, check the RAG status:**

1. **🟢 Green = All Good**
   - System is running normally
   - Continue monitoring performance metrics
   - No action needed

2. **🟡 Amber = Investigate**
   - System may have slowed down
   - Check Activity Log for recent errors
   - Verify orchestrator is running
   - May need restart

3. **🔴 Red = Action Required**
   - Orchestrator has stopped
   - System not making decisions
   - **Action:** Restart orchestrator
     ```bash
     ./start_trading.sh
     ```

### Monitoring Activity

**Check the Activity Log for:**

1. **Trading Decisions Being Made**
   ```
   Look for: "TRADING_DECISION" entries every ~60 seconds
   Expected: 5-10 per hour when markets are active
   ```

2. **Agent Signals Generated**
   ```
   Look for: "SIGNAL_GENERATED" entries
   Expected: Technical + Sentiment signals before each decision
   ```

3. **Errors or Issues**
   ```
   Look for: ❌ ERROR status
   Action: Check error details and logs
   ```

4. **Trade Executions**
   ```
   Look for: "ORDER_EXECUTED" with SUCCESS status
   Expected: Only when confidence ≥ 60%
   ```

### Troubleshooting

#### Problem: System shows 🔴 RED status

**Diagnosis:**
```sql
SELECT * FROM v_system_health;
```

**Common Causes:**
1. Orchestrator not running
2. Database connection lost
3. System crashed or frozen

**Solution:**
```bash
# Check if orchestrator is running
ps aux | grep orchestrator

# Restart if needed
./start_trading.sh
```

#### Problem: No recent activity in log

**Diagnosis:**
- Check if orchestrator process is running
- Check last execution time in Activity Log
- Verify database connectivity

**Solution:**
- Restart orchestrator
- Check logs for errors
- Verify Docker containers are running

#### Problem: Only seeing errors in Activity Log

**Common ERROR types:**

1. **Database Connection Errors**
   ```
   Check: Docker postgres container running
   Fix: docker-compose up -d
   ```

2. **API Rate Limit Errors**
   ```
   Issue: Too many requests to exchange/Reddit
   Fix: System handles automatically, will retry
   ```

3. **Signal Generation Errors**
   ```
   Issue: Missing data or invalid symbols
   Fix: Check price data collection is working
   ```

---

## Database Views

### v_system_health

Calculates real-time system health status.

**Query:**
```sql
SELECT * FROM v_system_health;
```

**Output:**
```
status          | description                  | orchestrator_age_minutes | agents_active | ...
HEALTHY         | All systems operational      | 2.3                      | 2             | ...
```

**Columns:**
- `status` - HEALTHY / DEGRADED / DOWN
- `description` - Human-readable status message
- `orchestrator_age_minutes` - Minutes since last orchestrator execution
- `agents_active` - Number of agents that generated signals in last hour
- `decisions_last_hour` - Trading decisions made in last hour
- `signals_last_hour` - Signals generated in last hour
- `errors_last_hour` - Errors in last hour
- `last_activity` - Timestamp of most recent activity

### v_system_activity

Unified view of all system activity.

**Query:**
```sql
SELECT * FROM v_system_activity
ORDER BY timestamp DESC
LIMIT 10;
```

**Output:**
```
activity_type      | component         | status  | description           | timestamp           | details
TRADING_DECISION   | Orchestrator      | SUCCESS | BUY BTC/USDT          | 2025-11-03 07:02:01 | Confidence: 61%...
SIGNAL_GENERATED   | SentimentAnalyst  | INFO    | buy signal for BTC    | 2025-11-03 07:01:58 | Confidence: 80%
...
```

**Activity Sources:**
- `agent_executions` - When agents run
- `agent_signals` - When signals are generated
- `trading_decisions` - When decisions are made
- `paper_orders` - When trades execute

---

## Alert Thresholds

**Recommended Grafana Alerts** (to be configured):

### Critical Alerts (🔴)
```
1. System Status = DOWN for > 10 minutes
   → Send notification to restart orchestrator

2. Errors > 5 in last hour
   → Investigate error messages in Activity Log

3. No decisions for > 30 minutes (during trading hours)
   → Check orchestrator and agents
```

### Warning Alerts (🟡)
```
1. System Status = DEGRADED for > 30 minutes
   → Monitor closely, may need restart

2. Only 1 agent active (should be 2)
   → Check sentiment analyst (may need Reddit API key refresh)

3. Decisions/hour < 3 (during active trading)
   → May indicate low confidence scores
```

---

## Metrics Explained

### Orchestrator Age
```
Time since orchestrator last executed
- < 5 min: Healthy (orchestrator running every 60 seconds)
- 5-15 min: Degraded (may have slowed or paused)
- > 15 min: Down (orchestrator stopped)
```

### Agents Active
```
Number of unique agents generating signals in last hour
- 2: Healthy (Technical + Sentiment both active)
- 1: Degraded (one agent not working, likely Sentiment)
- 0: Down (no agents running)
```

### Decisions Per Hour
```
Trading decisions made in last hour
- 5-10: Healthy (normal rate: ~1 per analysis cycle)
- 2-4: Degraded (low activity)
- 0: Down (not making decisions)
```

### Signals Per Hour
```
Agent signals generated in last hour
- 10-20: Healthy (both agents generating signals)
- 5-10: Degraded (reduced signal generation)
- 0-5: Down (agents not generating signals)
```

---

## Integration with Existing Dashboard

The system monitoring panels work alongside your existing trading metrics:

**Top Section:**
1. **System Health (NEW)** - 🚦 RAG Status
2. Portfolio Value
3. Total PnL
4. Win Rate
5. Open Positions

**Middle Section:**
- All existing charts and tables (unchanged)
- Portfolio trends
- Trade outcomes
- Performance metrics

**Bottom Section:**
- Recent Trades
- Recent Trading Decisions
- **System Activity Log (NEW)** - 📋 Last 15 actions

---

## Example Healthy System

```
🟢 HEALTHY
All systems operational
Orchestrator: 2.3m ago | Agents: 2 active | Decisions: 5/hr | Signals: 15/hr

Recent Activity:
11-03 14:02:01 | TRADING_DECISION  | ✅ | Orchestrator     | BUY BTC/USDT (61%)
11-03 14:01:58 | SIGNAL_GENERATED  | ℹ️ | SentimentAnalyst | buy signal (80%)
11-03 14:01:58 | SIGNAL_GENERATED  | ℹ️ | Technical        | buy signal (50%)
11-03 14:01:45 | AGENT_EXECUTION   | ✅ | SentimentAnalyst | analyst executed
11-03 14:01:44 | AGENT_EXECUTION   | ✅ | Technical        | analyst executed
11-03 14:01:30 | AGENT_EXECUTION   | ✅ | Orchestrator     | orchestrator executed
...
```

---

## Example Degraded System

```
🟡 DEGRADED
System running but degraded
Orchestrator: 12.1m ago | Agents: 1 active | Decisions: 1/hr | Signals: 3/hr

Recent Activity:
11-03 13:50:15 | TRADING_DECISION  | ⚠️ | Orchestrator     | HOLD ETH/USDT (52%)
11-03 13:50:12 | SIGNAL_GENERATED  | ℹ️ | Technical        | hold signal (50%)
11-03 13:50:01 | AGENT_EXECUTION   | ✅ | Technical        | analyst executed
11-03 13:49:58 | AGENT_EXECUTION   | ❌ | SentimentAnalyst | ERROR: API rate limit
...

Action: Check why SentimentAnalyst is failing
```

---

## Example Down System

```
🔴 DOWN
Orchestrator stopped or stalled
Orchestrator: 2235.4m ago | Agents: 0 active | Decisions: 0/hr | Signals: 0/hr

Recent Activity:
11-01 07:02:01 | TRADING_DECISION  | ℹ️ | Orchestrator     | HOLD MATIC/USDT (25%)
11-01 07:02:01 | TRADING_DECISION  | ℹ️ | Orchestrator     | HOLD AVAX/USDT (45%)
...
[All activity from 37+ hours ago]

Action: Restart orchestrator immediately!
  ./start_trading.sh
```

---

## Best Practices

### 1. Daily Monitoring
- ✅ Check RAG status every morning
- ✅ Review Activity Log for any errors
- ✅ Verify both agents are active (should see 2)

### 2. During Trading Hours
- ✅ Keep dashboard open in browser tab
- ✅ Set auto-refresh to 30 seconds
- ✅ Monitor for red error messages in Activity Log

### 3. After System Changes
- ✅ Watch Activity Log for first 5-10 minutes
- ✅ Verify GREEN status after restart
- ✅ Confirm both agents generating signals

### 4. If Errors Occur
- ❌ Don't panic - check Activity Log details first
- ✅ Read error message carefully
- ✅ Most errors auto-recover (API limits, network)
- ✅ Only restart if status goes RED

---

## Summary

**What You Get:**

1. **Real-Time System Health**
   - Instant visibility into orchestrator status
   - RAG indicators for quick assessment
   - Key metrics at a glance

2. **Complete Activity Visibility**
   - Every action logged and timestamped
   - Color-coded status indicators
   - Detailed error messages when issues occur

3. **Proactive Problem Detection**
   - Know immediately when orchestrator stops
   - See which agents are having issues
   - Identify errors before they impact trading

4. **Historical Context**
   - Last 15 actions always visible
   - Understand what led to current state
   - Troubleshoot issues effectively

**Result:**
- 📊 Better visibility into system operations
- 🔍 Faster problem diagnosis
- ⚠️ Early warning of issues
- ✅ Increased confidence in system reliability

---

*Document Version: 1.0*
*Last Updated: November 3, 2025*
*System Monitoring: ACTIVE*

# Grafana Dashboard Guide

## ✅ Grafana is Now Configured!

Your Grafana instance is fully set up with data sources and a trading dashboard.

---

## 🔐 **Access Grafana**

**URL:** http://localhost:3000

**Default Credentials:**
- **Username:** `admin`
- **Password:** `admin`

**Important:** You'll be prompted to change the password on first login. You can:
- Set a new secure password, OR
- Click "Skip" to keep using admin/admin (not recommended for production)

---

## 📊 **What's Already Configured**

### **Data Sources (Auto-configured)**

1. **TimescaleDB** (Default)
   - Type: PostgreSQL
   - Connected to your trading database
   - All your trading data, signals, decisions

2. **Prometheus**
   - Type: Prometheus
   - Metrics collection
   - Agent performance metrics

To view data sources: **Configuration** (⚙️) → **Data Sources**

### **Dashboard Available**

**"Autonomous Trading System - Overview"**

This dashboard shows:

1. **Summary Stats (Top Row)**
   - Decisions made in last 24h
   - Agent success rate
   - Price candles collected
   - Signals generated

2. **Recent Trading Decisions Table**
   - Latest 20 decisions
   - Symbol, decision type, confidence
   - Reasoning summary

3. **Price Charts**
   - BTC/USDT hourly prices
   - ETH/USDT hourly prices (scaled x30 to fit)

4. **Decision Distribution (Pie Chart)**
   - BUY vs SELL vs HOLD breakdown

5. **Signal Distribution (Pie Chart)**
   - Types of signals generated

6. **Agent Performance Table**
   - Each agent's execution count
   - Success rate
   - Average execution time

**Dashboard Location:**
- Home → Dashboards → Trading System folder → "Autonomous Trading System - Overview"

---

## 🚀 **How to Access Your Dashboard**

### Step 1: Open Grafana

Open your browser and go to: **http://localhost:3000**

### Step 2: Login

- Username: `admin`
- Password: `admin`

(Change password if prompted, or skip)

### Step 3: View Dashboard

1. Click **"Dashboards"** in the left sidebar (four squares icon)
2. Click on **"Trading System"** folder
3. Click **"Autonomous Trading System - Overview"**

You should now see your live trading data!

---

## 📈 **Understanding Your Dashboard**

### **Metrics Refreshed Every 30 Seconds**

The dashboard automatically refreshes every 30 seconds to show latest data.

### **Time Range Selector**

Top right corner - default shows **Last 24 hours**. You can change to:
- Last 6 hours
- Last 7 days
- Custom range

### **Panels You'll See**

#### **1. Decisions (24h)**
Shows total number of trading decisions made in last 24 hours.
- Expected: 48 per day (if running every 30 min) × 5 pairs = 240 decisions/day

#### **2. Agent Success Rate**
Percentage of successful agent executions.
- Target: 100% (green)
- Warning if below 90% (yellow)
- Alert if below 80% (red)

#### **3. Candles Collected**
Number of price candles stored in last 24 hours.
- Expected: ~7,200 per day (48 runs × 5 pairs × 6 timeframes × 5 new candles)

#### **4. Signals Generated**
Number of trading signals from technical analysis.
- Expected: 240 per day (48 runs × 5 pairs)

#### **5. Recent Trading Decisions**
Table showing latest decisions with:
- **Timestamp**: When decision was made
- **Symbol**: Which crypto pair
- **Decision**: BUY / SELL / HOLD
- **Confidence**: 0.0 to 1.0 (70%+ triggers BUY/SELL)
- **Reasoning**: Why the decision was made

#### **6. Price Charts**
Live price charts for BTC and ETH.
- Hover over chart to see exact prices
- Zoom by dragging
- Pan by holding shift and dragging

#### **7. Decision Distribution**
Pie chart showing breakdown of decisions.
- Mostly HOLD is normal (conservative system)
- BUY signals when confidence > 70%
- SELL signals when confidence > 70%

#### **8. Signal Distribution**
Breakdown of technical signals.
- Shows sentiment from technical analysis
- buy/sell/hold distribution

#### **9. Agent Performance**
Table of all agents showing:
- **Executions**: How many times they ran
- **Success Rate**: Should be 1.0 (100%)
- **Avg Duration**: How long they take to execute

---

## 🎨 **Customizing Your Dashboard**

### **Add New Panels**

1. Click **"Add panel"** (top right)
2. Select **"Add a new panel"**
3. Choose data source: **TimescaleDB**
4. Write SQL query
5. Configure visualization
6. Click **"Apply"**

### **Example Queries You Can Add**

#### **Latest BTC Price**
```sql
SELECT close as "BTC Price"
FROM price_data
WHERE symbol = 'BTC/USDT'
  AND timeframe = '1h'
ORDER BY time DESC
LIMIT 1
```

#### **RSI Indicator**
```sql
SELECT
  time,
  rsi_14 as "RSI"
FROM technical_indicators
WHERE symbol = 'BTC/USDT'
  AND timeframe = '1h'
  AND $__timeFilter(time)
ORDER BY time
```

#### **Agent Execution History**
```sql
SELECT
  start_time as time,
  agent_name,
  duration_seconds
FROM agent_executions
WHERE $__timeFilter(start_time)
ORDER BY start_time
```

### **Edit Existing Panels**

1. Hover over any panel
2. Click the **three dots** (⋮) in top right
3. Select **"Edit"**
4. Modify query or visualization
5. Click **"Apply"**

---

## 🔔 **Setting Up Alerts (Optional)**

You can configure alerts to notify you when:
- Agent success rate drops below 80%
- No data collected in last hour
- Trading decision confidence exceeds threshold

### **To Add an Alert**

1. Edit a panel
2. Go to **"Alert"** tab
3. Click **"Create alert rule from this panel"**
4. Configure conditions
5. Set notification channel (email, Slack, etc.)

---

## 📊 **Creating More Dashboards**

### **Dashboard Ideas**

1. **Technical Indicators Dashboard**
   - RSI, MACD, EMAs for all pairs
   - Indicator correlation heatmap
   - Signal strength over time

2. **Performance Tracking**
   - Predicted vs Actual ROI (when live trading)
   - Win rate by pair
   - Best performing strategies

3. **System Health Dashboard**
   - Docker container status
   - Database query performance
   - Agent execution times
   - Error rates

4. **Alert Dashboard**
   - Recent errors
   - Data freshness issues
   - System warnings

### **To Create New Dashboard**

1. Click **+** in left sidebar
2. Select **"Dashboard"**
3. Click **"Add visualization"**
4. Choose **TimescaleDB** data source
5. Build your query
6. Save dashboard

---

## 🛠️ **Troubleshooting**

### **Can't Login**

If admin/admin doesn't work:

1. Reset Grafana data:
   ```bash
   docker compose down
   docker volume rm trading_grafana_data
   docker compose up -d
   ```
2. Wait 10 seconds
3. Try admin/admin again

### **No Data Showing**

1. **Check if data exists:**
   ```bash
   docker compose exec timescaledb psql -U trading_user -d trading_system -c "SELECT COUNT(*) FROM trading_decisions;"
   ```

2. **Check data source connection:**
   - Go to Configuration → Data Sources → TimescaleDB
   - Click "Save & Test"
   - Should show green "Database Connection OK"

3. **Check time range:**
   - Top right corner, make sure time range includes your data
   - Try "Last 7 days" or "Last 30 days"

### **Dashboard Not Appearing**

1. Restart Grafana:
   ```bash
   docker compose restart grafana
   ```

2. Wait 10 seconds and refresh browser

3. Check Dashboards → Manage → should see "Trading System" folder

### **Panels Show "No Data"**

1. Verify trading system has run:
   ```bash
   cat logs/last_cycle.json
   ```

2. Check time range matches your data

3. Verify queries in panel settings

---

## 🎯 **Quick Start Checklist**

✅ Open http://localhost:3000
✅ Login with admin/admin
✅ Navigate to Dashboards → Trading System
✅ View "Autonomous Trading System - Overview"
✅ Verify panels show data
✅ Adjust time range if needed
✅ Bookmark dashboard URL for quick access

---

## 📚 **Next Steps**

1. **Familiarize yourself** with the overview dashboard
2. **Monitor daily** as part of your 2x daily check-ins
3. **Create custom dashboards** for specific metrics you want to track
4. **Set up alerts** for critical issues (optional)
5. **Share dashboards** with team members (if needed)

---

## 🔗 **Useful Links**

**Your Grafana:** http://localhost:3000
**Grafana Documentation:** https://grafana.com/docs/
**Query Examples:** https://grafana.com/docs/grafana/latest/datasources/postgres/

---

## 💡 **Pro Tips**

1. **Pin your dashboard** - Click the star icon to add to favorites
2. **Use variables** - Create dynamic dashboards with dropdowns to select pairs
3. **Share snapshots** - Share dashboard views with others via snapshots
4. **Export/Import** - Save dashboard JSON to backup your custom dashboards
5. **Keyboard shortcuts** - Press `?` in Grafana to see all shortcuts

---

**Grafana Status:** ✅ Configured and Running
**Dashboard:** ✅ Available
**Data Sources:** ✅ Connected

**Your trading data is now visualized!** 📊🚀

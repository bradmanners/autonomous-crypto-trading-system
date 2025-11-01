# Cron Job Monitoring Guide

## ✅ Cron Job Installed!

Your autonomous trading system is now scheduled to run **every 30 minutes**.

### Schedule Details

**Cron Expression:** `*/30 * * * *`
**Meaning:** Runs at minute 0 and 30 of every hour (e.g., 10:00, 10:30, 11:00, 11:30, etc.)
**Expected Executions:** 48 times per day

### Next Execution Times

The system will run at:
- :00 minutes (top of every hour)
- :30 minutes (half past every hour)

For example, if it's currently 11:15, the next runs will be at:
- 11:30
- 12:00
- 12:30
- etc.

## 📊 Monitoring Your Cron Job

### 1. Check Cron Logs

View real-time cron execution logs:

```bash
cd "/Users/bradmancini/Library/CloudStorage/OneDrive-aevance.com/03_Atvia Entities/03_Atmospherique Pty Ltd/App Development/01_Terminal_Dev_Auto_Trader"
tail -f logs/cron.log
```

This will show you the output from each automated run.

### 2. View Last Cycle Results

After each run, check the results:

```bash
cat logs/last_cycle.json | python -m json.tool
```

Look for:
- `"success": true`
- `"candles_collected"` count
- `"pairs_analyzed"` count
- `"trading_decisions"` array

### 3. Check Trading System Logs

View detailed system logs:

```bash
tail -f logs/trading_system.log
```

### 4. Verify Cron is Running

Check your crontab:

```bash
crontab -l
```

You should see:
```
# Autonomous Crypto Trading System - Run every 30 minutes
*/30 * * * * cd "/Users/bradmancini/Library/CloudStorage/OneDrive-aevance.com/03_Atvia Entities/03_Atmospherique Pty Ltd/App Development/01_Terminal_Dev_Auto_Trader" && ...
```

### 5. Database Activity

Check that new data is being collected:

```bash
docker compose exec timescaledb psql -U trading_user -d trading_system -c "SELECT COUNT(*), MAX(time) as latest FROM price_data;"
```

The count should increase by ~150-300 candles every 30 minutes (5 pairs × 6 timeframes × ~5-10 new candles).

## 🔍 Troubleshooting

### Cron Not Running?

On macOS, you may need to give Terminal "Full Disk Access":

1. Open **System Preferences** → **Security & Privacy** → **Privacy**
2. Select **Full Disk Access**
3. Click the lock to make changes
4. Add **Terminal** to the list
5. Restart Terminal

### Check macOS Cron Service

```bash
# Check if cron is loaded (may require password)
sudo launchctl list | grep cron

# If not running, enable it:
sudo launchctl load -w /System/Library/LaunchDaemons/com.vix.cron.plist
```

### Manual Test

Run the script manually to ensure it works:

```bash
cd "/Users/bradmancini/Library/CloudStorage/OneDrive-aevance.com/03_Atvia Entities/03_Atmospherique Pty Ltd/App Development/01_Terminal_Dev_Auto_Trader"
venv/bin/python scripts/run_trading_cycle.py
```

If this works, the cron job will work too.

### Check Cron Logs for Errors

If cron.log is empty after expected run times:

```bash
# Check system log for cron activity (macOS)
log show --predicate 'process == "cron"' --last 1h --info
```

## 📈 Expected Behavior

### Every 30 Minutes

The system will automatically:

1. **Collect Price Data** (~12 seconds)
   - Fetch latest candles from Binance
   - Store in TimescaleDB
   - Update cache

2. **Run Technical Analysis** (~0.1 seconds per pair)
   - Calculate 10+ indicators
   - Generate signals with confidence scores
   - Store in database

3. **Make Trading Decisions** (~1 second)
   - Aggregate all signals
   - Evaluate against thresholds (70%+ for BUY/SELL)
   - Log decisions to database

4. **Health Check** (~0.5 seconds)
   - Verify data freshness
   - Check agent execution success rates
   - Identify any issues

**Total Cycle Time:** ~15-20 seconds

### What Gets Logged

Each run creates:
- Entry in `logs/cron.log` (stdout/stderr)
- Entry in `logs/trading_system.log` (structured logging)
- Updated `logs/last_cycle.json` (summary)
- Database records in:
  - `agent_executions`
  - `price_data`
  - `technical_indicators`
  - `agent_signals`
  - `trading_decisions`

## 🎯 Daily Monitoring Checklist

### Morning Check-in (5 minutes)

```bash
# 1. Check last cycle was successful
cat logs/last_cycle.json | python -m json.tool | grep success

# 2. View today's trading decisions
docker compose exec timescaledb psql -U trading_user -d trading_system -c "
SELECT symbol, decision, confidence, timestamp
FROM trading_decisions
WHERE timestamp >= CURRENT_DATE
ORDER BY timestamp DESC;"

# 3. Check agent health
docker compose exec timescaledb psql -U trading_user -d trading_system -c "
SELECT agent_name, COUNT(*) as runs,
       ROUND(AVG(CASE WHEN success THEN 1.0 ELSE 0.0 END), 2) as success_rate
FROM agent_executions
WHERE start_time >= CURRENT_DATE
GROUP BY agent_name;"
```

### Evening Check-in (5 minutes)

```bash
# 1. Check how many cycles ran today
grep "CYCLE SUMMARY" logs/cron.log | wc -l

# 2. View any errors
tail -20 logs/errors.log

# 3. Check data growth
docker compose exec timescaledb psql -U trading_user -d trading_system -c "
SELECT
    'price_data' as table_name, COUNT(*) as records
FROM price_data
UNION ALL
SELECT 'agent_signals', COUNT(*)
FROM agent_signals
UNION ALL
SELECT 'trading_decisions', COUNT(*)
FROM trading_decisions;"
```

## ⏸️ Pausing/Stopping the Cron Job

### Temporary Pause

Comment out the cron job:

```bash
crontab -e
# Add # at the beginning of the line to comment it out
# */30 * * * * cd "/Users/..." && ...
```

Save and exit.

### Permanent Removal

```bash
crontab -r
```

This removes all your cron jobs. Use with caution!

### View Without Editing

```bash
crontab -l
```

## 📊 Performance Expectations

### After 24 Hours (48 executions)

- **Price Data**: +7,200 candles (48 cycles × 150 candles)
- **Signals**: +240 signals (48 cycles × 5 pairs)
- **Decisions**: +240 decisions (48 cycles × 5 pairs)
- **Disk Usage**: ~100 MB additional

### After 1 Week (336 executions)

- **Price Data**: ~50,000 candles
- **Signals**: ~1,680 signals
- **Decisions**: ~1,680 decisions
- **Disk Usage**: ~500 MB total

### After 2 Weeks (Paper Trading Period)

- **Price Data**: ~100,000 candles
- **Signals**: ~3,360 signals
- **Decisions**: ~3,360 decisions
- **You'll have**: Enough data to evaluate system performance

## 🚨 Alert Conditions

Watch for these issues in logs:

1. **Consecutive Failures** - More than 3 failed cycles in a row
2. **No Data Collection** - `candles_collected: 0` multiple times
3. **Database Errors** - Connection failures
4. **Docker Down** - Services not running

If you see any of these, run:

```bash
docker compose ps  # Check services
docker compose restart  # Restart if needed
```

## 💡 Tips

1. **Check logs once in the morning, once in the evening** (as you planned)
2. **Don't worry about HOLD decisions** - Market is often neutral
3. **Watch for BUY/SELL signals** - They'll only trigger at 70%+ confidence
4. **First week is validation** - You're building confidence in the system
5. **Keep Docker Desktop running** - Required for the system to work

## 🎉 Success Indicators

After 24 hours, you should see:

✅ 48 successful cycles
✅ ~7,200 new price candles
✅ 240+ signals generated
✅ 240+ decisions logged
✅ 0% error rate
✅ All Docker services healthy

If you see this, the system is working perfectly!

---

**Cron Job Status:** ✅ ACTIVE
**Frequency:** Every 30 minutes
**Next Steps:** Monitor for 24-48 hours, then relax!

Your autonomous trading system is now live! 🚀

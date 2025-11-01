# Automated Scheduling Guide

This guide explains how to set up automated execution of the trading system.

## Quick Start

The trading system can run autonomously on a schedule using cron (macOS/Linux) or Task Scheduler (Windows).

## Option 1: Cron (macOS/Linux) - RECOMMENDED

### Hourly Execution

Run the trading cycle every hour at minute 0:

```bash
crontab -e
```

Add this line:

```cron
0 * * * * cd /Users/bradmancini/Library/CloudStorage/OneDrive-aevance.com/03_Atvia\ Entities/03_Atmospherique\ Pty\ Ltd/App\ Development/01_Terminal_Dev_Auto_Trader && /Users/bradmancini/Library/CloudStorage/OneDrive-aevance.com/03_Atvia\ Entities/03_Atmospherique\ Pty\ Ltd/App\ Development/01_Terminal_Dev_Auto_Trader/venv/bin/python scripts/run_trading_cycle.py >> logs/cron.log 2>&1
```

### Every 4 Hours

More conservative approach (6 times per day):

```cron
0 */4 * * * cd /Users/bradmancini/Library/CloudStorage/OneDrive-aevance.com/03_Atvia\ Entities/03_Atmospherique\ Pty\ Ltd/App\ Development/01_Terminal_Dev_Auto_Trader && /Users/bradmancini/Library/CloudStorage/OneDrive-aevance.com/03_Atvia\ Entities/03_Atmospherique\ Pty\ Ltd/App\ Development/01_Terminal_Dev_Auto_Trader/venv/bin/python scripts/run_trading_cycle.py >> logs/cron.log 2>&1
```

### Daily at Specific Time

Run once per day at 9:00 AM:

```cron
0 9 * * * cd /Users/bradmancini/Library/CloudStorage/OneDrive-aevance.com/03_Atvia\ Entities/03_Atmospherique\ Pty\ Ltd/App\ Development/01_Terminal_Dev_Auto_Trader && /Users/bradmancini/Library/CloudStorage/OneDrive-aevance.com/03_Atvia\ Entities/03_Atmospherique\ Pty\ Ltd/App\ Development/01_Terminal_Dev_Auto_Trader/venv/bin/python scripts/run_trading_cycle.py >> logs/cron.log 2>&1
```

## Option 2: Manual Execution

You can run the trading cycle manually anytime:

```bash
cd "/Users/bradmancini/Library/CloudStorage/OneDrive-aevance.com/03_Atvia Entities/03_Atmospherique Pty Ltd/App Development/01_Terminal_Dev_Auto_Trader"
venv/bin/python scripts/run_trading_cycle.py
```

## Option 3: System Service (Advanced)

For production deployment, create a systemd service (Linux) or launchd plist (macOS).

### macOS launchd Example

Create file: `~/Library/LaunchAgents/com.atmospherique.trading.plist`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.atmospherique.trading</string>

    <key>ProgramArguments</key>
    <array>
        <string>/Users/bradmancini/Library/CloudStorage/OneDrive-aevance.com/03_Atvia Entities/03_Atmospherique Pty Ltd/App Development/01_Terminal_Dev_Auto_Trader/venv/bin/python</string>
        <string>/Users/bradmancini/Library/CloudStorage/OneDrive-aevance.com/03_Atvia Entities/03_Atmospherique Pty Ltd/App Development/01_Terminal_Dev_Auto_Trader/scripts/run_trading_cycle.py</string>
    </array>

    <key>WorkingDirectory</key>
    <string>/Users/bradmancini/Library/CloudStorage/OneDrive-aevance.com/03_Atvia Entities/03_Atmospherique Pty Ltd/App Development/01_Terminal_Dev_Auto_Trader</string>

    <key>StartInterval</key>
    <integer>3600</integer>  <!-- Run every hour -->

    <key>StandardOutPath</key>
    <string>/Users/bradmancini/Library/CloudStorage/OneDrive-aevance.com/03_Atvia Entities/03_Atmospherique Pty Ltd/App Development/01_Terminal_Dev_Auto_Trader/logs/launchd.log</string>

    <key>StandardErrorPath</key>
    <string>/Users/bradmancini/Library/CloudStorage/OneDrive-aevance.com/03_Atvia Entities/03_Atmospherique Pty Ltd/App Development/01_Terminal_Dev_Auto_Trader/logs/launchd_error.log</string>

    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
```

Load the service:

```bash
launchctl load ~/Library/LaunchAgents/com.atmospherique.trading.plist
```

Unload if needed:

```bash
launchctl unload ~/Library/LaunchAgents/com.atmospherique.trading.plist
```

## Monitoring

### View Last Cycle Results

```bash
cat logs/last_cycle.json | python -m json.tool
```

### View Logs

```bash
# All logs
tail -f logs/trading_system.log

# Errors only
tail -f logs/errors.log

# Cron logs (if using cron)
tail -f logs/cron.log
```

### Check Cron Status

```bash
# View current crontab
crontab -l

# View cron job execution logs
grep CRON /var/log/system.log  # macOS
```

## Recommended Schedule

For the initial paper trading phase:

- **Week 1-2**: Run **every 4 hours** (6x per day)
- **Week 3-4**: Run **hourly** if performance is good
- **Live Trading**: Continue hourly or increase to every 15 minutes

## Prerequisites

Before scheduling:

1. ✅ Docker Desktop is running
2. ✅ All Docker services are up (timescaledb, redis, grafana, prometheus)
3. ✅ .env file is configured with API keys
4. ✅ Manual test run successful

Verify Docker services:

```bash
docker compose ps
```

Should show all services as "Up" and healthy.

## Troubleshooting

### Cron Not Running

1. Check cron is enabled: `sudo launchctl load -w /System/Library/LaunchDaemons/com.vix.cron.plist` (macOS)
2. Check system logs: `log show --predicate 'process == "cron"' --last 1h` (macOS)
3. Verify paths in crontab are absolute
4. Ensure Python venv path is correct

### Script Errors

1. Run manually first to test
2. Check logs/errors.log
3. Verify Docker services are running
4. Check database connectivity

### Permission Issues

```bash
chmod +x scripts/run_trading_cycle.py
```

## Next Steps

1. Set up your preferred schedule (cron or launchd)
2. Monitor for 24-48 hours to ensure stability
3. Review logs and trading decisions
4. Adjust schedule frequency as needed
5. Set up monitoring alerts (Grafana dashboards)

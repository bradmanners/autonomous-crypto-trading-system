# Project Manager Agent Setup

## Overview

The Project Manager Agent is an autonomous meta-agent that:
- Monitors all project tasks and agent work
- Tracks trading system performance
- Generates comprehensive status reports every 2 hours
- Emails reports to stakeholders
- Provides architecture, security, and performance recommendations

## Features

### 1. Task Monitoring
- Tracks active tasks by status (pending, in_progress, blocked, completed)
- Monitors task progress percentages
- Reports on agent assignments and workload

### 2. Trading Performance Analysis
- Portfolio value and P&L tracking
- Position monitoring
- Trade statistics (24-hour rolling)
- Win rate and profitability metrics

### 3. Agent Performance Tracking
- Individual agent performance metrics
- Sharpe ratio and win rate analysis
- Signal quality assessment
- Performance trending over 7 days

### 4. System Health Monitoring
- System metrics collection
- Performance indicators
- Error rate tracking
- Resource utilization

### 5. Recommendations Engine
- **Architecture**: System design and scalability suggestions
- **Security**: Security best practices and vulnerabilities
- **Performance**: Optimization opportunities
- **Trading**: Strategy and risk management improvements

## Database Schema

The Project Manager uses the following tables (created by migration 007):
- `project_tasks` - Task tracking and management
- `agent_work_log` - Agent activity logging
- `agent_performance` - Performance metrics by agent
- `project_reports` - Generated reports storage
- `improvement_suggestions` - AI-generated recommendations
- `system_metrics` - System health metrics
- `email_config` - Email configuration

## Email Configuration

To enable email reports, update the `email_config` table in the database:

```sql
-- Update SMTP configuration
UPDATE email_config SET config_value = 'smtp.gmail.com' WHERE config_key = 'smtp_server';
UPDATE email_config SET config_value = '587' WHERE config_key = 'smtp_port';
UPDATE email_config SET config_value = 'your-email@gmail.com' WHERE config_key = 'smtp_user';

-- Add SMTP password (IMPORTANT: Store securely in production)
INSERT INTO email_config (config_key, config_value, is_encrypted)
VALUES ('smtp_password', 'your-app-password', true)
ON CONFLICT (config_key) DO UPDATE SET config_value = 'your-app-password';

-- Update recipient email
UPDATE email_config SET config_value = 'brad@skylie.com' WHERE config_key = 'recipient_email';

-- Update report frequency (in hours)
UPDATE email_config SET config_value = '2' WHERE config_key = 'report_frequency_hours';
```

### Gmail App Password Setup

If using Gmail:
1. Go to Google Account settings → Security
2. Enable 2-Factor Authentication
3. Generate an "App Password" for "Mail"
4. Use the generated 16-character password in `smtp_password`

## Running the Project Manager

### Option 1: Manual Execution
```bash
cd /path/to/project
PYTHONPATH=. venv/bin/python agents/meta/project_manager.py
```

### Option 2: Automated 2-Hour Schedule
```bash
./start_project_manager.sh
```

This will run the agent continuously, generating reports every 2 hours.

### Option 3: Background Process
```bash
nohup ./start_project_manager.sh > /dev/null 2>&1 &
```

## Report Structure

Each report includes:

### 1. Summary Section
- Portfolio value and P&L
- Open positions count
- Active tasks count
- Active agents count

### 2. Trading Performance
```json
{
  "portfolio": {
    "cash_balance": 10000.00,
    "total_value": 12500.00,
    "total_pnl": 2500.00,
    "unrealized_pnl": 150.00
  },
  "positions": [...],
  "trades": {
    "total_trades_24h": 15,
    "filled_trades_24h": 14
  }
}
```

### 3. Agent Performance
```json
{
  "summary": {
    "TechnicalAnalyst": {
      "avg_sharpe": 1.2,
      "avg_win_rate": 0.65,
      "total_signals": 150
    }
  }
}
```

### 4. Recommendations
```json
{
  "architecture": [
    "Consider implementing automated backtesting..."
  ],
  "security": [
    "Ensure API keys are rotated regularly..."
  ],
  "performance": [...],
  "trading": [...]
}
```

## Report Storage

Reports are saved to:
1. Database table: `project_reports`
2. Email: Sent to configured recipient
3. Logs: `logs/project_manager.log`

## Querying Reports

```sql
-- Get latest report
SELECT * FROM project_reports
ORDER BY generated_at DESC
LIMIT 1;

-- Get all reports from last 24 hours
SELECT
    report_type,
    generated_at,
    summary,
    recommendations
FROM project_reports
WHERE generated_at >= NOW() - INTERVAL '24 hours'
ORDER BY generated_at DESC;

-- Get report data as JSON
SELECT report_data
FROM project_reports
WHERE id = 1;
```

## Monitoring

View logs in real-time:
```bash
tail -f logs/project_manager.log
```

Check agent status:
```python
from agents.meta.project_manager import ProjectManagerAgent
agent = ProjectManagerAgent()
status = agent.get_status()
print(status)
```

## Troubleshooting

### Email Not Sending
1. Check SMTP configuration in `email_config` table
2. Verify Gmail App Password is correct
3. Check firewall allows port 587
4. Review logs for authentication errors

### Missing Data in Reports
1. Ensure all migrations have been applied
2. Verify paper trading engine is running
3. Check that agents are generating signals
4. Confirm database tables exist

### Performance Issues
1. Check database connection pooling
2. Review report frequency (consider increasing interval)
3. Monitor system resources
4. Check log file size

## Next Steps

1. **Configure Email**: Set up SMTP credentials
2. **Start Agent**: Run `./start_project_manager.sh`
3. **Monitor Reports**: Check email every 2 hours
4. **Review Recommendations**: Act on high-priority suggestions
5. **Expand Agents**: Add Performance Analyzer and Weight Optimizer agents

## Integration with Other Agents

The Project Manager coordinates with:
- **Performance Analyzer**: Tracks agent effectiveness
- **Weight Optimizer**: Adjusts agent weights based on performance
- **Implementation Agent**: Executes improvement tasks
- **Testing Agent**: Validates changes

These agents will be created next to build a fully autonomous self-improving system.

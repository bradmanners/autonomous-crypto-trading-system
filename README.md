# Autonomous Crypto Trading System

A state-of-the-art autonomous trading system powered by AI agents, machine learning, and multi-source data analysis.

## 🎯 Overview

This system uses a multi-agent architecture to analyze cryptocurrency markets, make trading decisions, and continuously improve performance. It combines:

- **Multiple specialized AI agents** for data collection, analysis, and decision-making
- **Machine learning models** (XGBoost ensemble initially, deep learning planned)
- **Real-time sentiment analysis** from Twitter, Reddit, and news sources
- **On-chain data analysis** for crypto-specific insights
- **Macro and geopolitical event tracking** including US political impacts
- **Continuous improvement agent** that proposes daily optimizations
- **Professional risk management** with Kelly Criterion position sizing
- **Comprehensive monitoring** via Grafana dashboards
- **Predicted vs Actual ROI tracking** as key performance indicator

## 📋 Features

### Current (Phase 1-2)
- ✅ Hourly data collection from multiple sources
- ✅ Technical analysis with 15+ indicators
- ✅ XGBoost ensemble for predictions
- ✅ Multi-source sentiment analysis
- ✅ Risk management system
- ✅ Paper trading mode
- ✅ TimescaleDB for time-series data
- ✅ Prometheus + Grafana monitoring

### Planned (Phase 3-6)
- 🔄 Deep learning models (LSTM, Transformers, RL)
- 🔄 Multi-asset expansion (stocks, forex, commodities)
- 🔄 Advanced derivatives strategies
- 🔄 High-frequency capabilities

## 🏗️ Architecture

```
┌─────────────────────────────────────┐
│     ORCHESTRATOR AGENT (Claude)     │
│  - Aggregates all signals           │
│  - Makes final BUY/SELL/HOLD        │
│  - Manages risk and portfolio       │
└───────────┬─────────────────────────┘
            │
    ┌───────┼───────┐
    │       │       │
    ▼       ▼       ▼
┌──────┐ ┌──────┐ ┌──────┐
│ Data │ │ ML   │ │ Exec │
│ Team │ │ Team │ │ Team │
└──────┘ └──────┘ └──────┘

┌────────────────────────────────┐
│  CONTINUOUS IMPROVEMENT AGENT  │
│  - Monitors performance        │
│  - Generates daily proposals   │
│  - Backtests improvements      │
└────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- 8GB RAM minimum
- API Keys (see Configuration section)

### Installation

1. **Clone and setup:**
```bash
cd /path/to/01_Terminal_Dev_Auto_Trader

# Copy environment template
cp .env.template .env

# Edit .env with your API keys
nano .env
```

2. **Start infrastructure:**
```bash
# Start databases and monitoring
docker-compose up -d timescaledb redis grafana prometheus

# Wait for services to be healthy
docker-compose ps
```

3. **Install Python dependencies:**
```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

4. **Initialize database:**
```bash
# Database will be initialized automatically via docker-compose
# Check logs: docker-compose logs timescaledb
```

5. **Run the system (paper trading):**
```bash
# Ensure TRADING_MODE=paper in .env
python -m agents.orchestrator.main
```

## ⚙️ Configuration

### Required API Keys

Update `.env` with the following:

#### Essential (Required for basic operation):
```bash
# Binance (for price data and trading)
BINANCE_API_KEY=your_key
BINANCE_API_SECRET=your_secret
BINANCE_TESTNET=true  # Set to false for live trading

# Claude AI (for agent orchestration)
ANTHROPIC_API_KEY=your_anthropic_key
```

#### Recommended (for full functionality):
```bash
# Twitter (sentiment analysis)
TWITTER_BEARER_TOKEN=your_bearer_token

# Reddit (sentiment analysis)
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_secret

# CryptoPanic (news aggregation)
CRYPTOPANIC_API_KEY=your_key

# Email (notifications)
SENDGRID_API_KEY=your_key  # Or use SMTP settings
NOTIFICATION_EMAIL=your_email@domain.com
```

#### Optional (advanced features):
```bash
# Glassnode (on-chain data)
GLASSNODE_API_KEY=your_key

# CoinGecko (additional price data)
COINGECKO_API_KEY=your_key

# NewsAPI (additional news)
NEWS_API_KEY=your_key
```

### Trading Parameters

Key settings in `.env`:

```bash
TRADING_MODE=paper  # paper or live
INITIAL_CAPITAL=1000.00
MAX_POSITIONS=3
RISK_PER_TRADE=0.02  # 2% per trade
MAX_PORTFOLIO_HEAT=0.06  # 6% total risk
DAILY_LOSS_LIMIT=0.05  # 5% daily loss limit

# Assets to trade
CRYPTO_PAIRS=BTC/USDT,ETH/USDT,SOL/USDT,AVAX/USDT,MATIC/USDT
```

## 📊 Monitoring

### Grafana Dashboards

Access Grafana at: `http://localhost:3000`

Default credentials:
- Username: `admin`
- Password: Check `GRAFANA_ADMIN_PASSWORD` in .env

**Pre-configured dashboards:**
1. **Trading Performance** - P&L, win rate, Sharpe ratio
2. **Portfolio Overview** - Positions, risk metrics, capital allocation
3. **Agent Performance** - Signal accuracy, contribution to P&L
4. **Predicted vs Actual ROI** - Key KPI for model calibration
5. **System Health** - API errors, latency, uptime

### Prometheus Metrics

Access raw metrics at: `http://localhost:9090`

Key metrics tracked:
- `trading_pnl_total` - Total profit/loss
- `trading_positions_open` - Number of open positions
- `trading_win_rate` - Percentage of winning trades
- `agent_signal_accuracy` - Per-agent prediction accuracy
- `model_prediction_error` - MAE/RMSE for predictions
- `api_request_latency` - API response times

## 📧 Notifications

### Daily Email Summary

Automatically sent at 8:00 AM (your timezone) with:
- Yesterday's performance summary
- Open positions and their status
- Recent trades
- Agent insights and recommendations
- Continuous improvement proposals

### Alert Emails

Sent immediately for:
- Large drawdowns (>10%)
- System errors
- API failures
- Unusual market opportunities

## 🧪 Testing Strategy

### Before Live Trading:

1. **Paper Trade (2 weeks minimum)**
```bash
# Set in .env
TRADING_MODE=paper
BINANCE_TESTNET=true

# Run system
python -m agents.orchestrator.main
```

2. **Monitor Key Metrics**
   - Sharpe Ratio > 1.5
   - Max Drawdown < 15%
   - Win Rate > 50%
   - Predicted vs Actual ROI error < 2%

3. **Backtest**
```bash
# Run comprehensive backtest
python -m scripts.run_backtest --start 2023-01-01 --end 2024-12-31
```

4. **Review Continuous Improvement Proposals**
   - Check daily proposals
   - Implement improvements
   - Re-test

5. **Small Capital Start**
   - Deploy $500 first (50% of capital)
   - Monitor for 1 week
   - Scale gradually

## 🔒 Risk Management

### Built-in Safeguards

- **Position Sizing**: Kelly Criterion with 0.25 fractional
- **Stop Losses**: 2x ATR (Average True Range)
- **Maximum Risk**: 2% per trade, 6% portfolio total
- **Daily Loss Limit**: Trading paused if 5% daily loss
- **Drawdown Protection**: Position sizes reduced at 15% drawdown
- **Emergency Stop**: All trading halted at 25% drawdown

### Circuit Breakers

The system will automatically:
1. **Reduce position sizes** if approaching risk limits
2. **Pause trading** if daily loss limit hit
3. **Alert you** for any unusual activity
4. **Log all decisions** for review

## 📁 Project Structure

```
01_Terminal_Dev_Auto_Trader/
├── agents/                      # AI Agents
│   ├── orchestrator/           # Main decision-making agent
│   ├── data_collectors/        # Price, sentiment, macro data
│   ├── analysts/               # Technical, ML, regime detection
│   ├── execution/              # Risk management, order execution
│   └── improvement/            # Continuous improvement agent
├── models/                      # ML Models
│   ├── sentiment/              # Sentiment analysis models
│   ├── price_prediction/       # Price prediction models
│   └── rl_agent/               # Reinforcement learning (future)
├── data/                        # Data storage
│   ├── raw/                    # Raw collected data
│   ├── processed/              # Processed data
│   └── features/               # Engineered features
├── config/                      # Configuration
│   └── config.py               # Main config file
├── infrastructure/              # Infrastructure configs
│   ├── docker/                 # Docker configs
│   ├── airflow/                # Workflow orchestration
│   └── monitoring/             # Grafana, Prometheus, Loki
├── utils/                       # Utilities
│   ├── database.py             # Database helpers
│   └── logging_config.py       # Logging setup
├── tests/                       # Unit & integration tests
├── scripts/                     # Utility scripts
├── backtests/                   # Backtest results
├── logs/                        # Application logs
├── docs/                        # Documentation
│   ├── project_roadmap.md      # Development roadmap
│   └── future_assets_expansion.md  # Future asset classes
├── docker-compose.yml           # Infrastructure definition
├── Dockerfile                   # Application container
├── requirements.txt             # Python dependencies
├── .env.template                # Environment template
└── README.md                    # This file
```

## 🛠️ Development

### Running Tests

```bash
# All tests
pytest

# Specific test file
pytest tests/test_agents.py

# With coverage
pytest --cov=agents --cov-report=html
```

### Code Quality

```bash
# Format code
black .

# Lint
ruff check .

# Type checking
mypy agents/
```

### Adding a New Agent

1. Create agent file in appropriate directory
2. Inherit from `BaseAgent` class
3. Implement `analyze()` and `generate_signal()` methods
4. Register in orchestrator
5. Add tests

Example:
```python
# agents/analysts/custom_agent.py
from agents.base import BaseAgent

class CustomAnalyst(BaseAgent):
    def __init__(self):
        super().__init__("CustomAnalyst")

    async def analyze(self, symbol: str) -> Dict:
        # Your analysis logic
        return {...}

    def generate_signal(self, analysis: Dict) -> Signal:
        # Generate trading signal
        return Signal(...)
```

## 📈 Performance Tracking

### Key Metrics

**Trading Performance:**
- **Sharpe Ratio**: Risk-adjusted returns (target: >1.5)
- **Max Drawdown**: Largest peak-to-trough decline (target: <15%)
- **Win Rate**: Percentage of profitable trades (target: >50%)
- **Profit Factor**: Gross profit / gross loss (target: >1.5)
- **Expectancy**: Average win * win rate - average loss * loss rate

**Model Performance:**
- **Predicted vs Actual ROI**: MAE (target: <2%)
- **Directional Accuracy**: Correct direction predictions (target: >60%)
- **Calibration**: Brier score for probabilities (target: <0.2)
- **Agent Accuracy**: Per-agent signal quality

### Continuous Improvement

The system's **Continuous Improvement Agent** runs daily to:

1. **Analyze** last 7 days of performance
2. **Identify** bottlenecks and opportunities
3. **Generate** 2-3 improvement hypotheses
4. **Backtest** proposals on historical data
5. **Submit** top proposal for your review

**Review Process:**
- Check email for daily proposal
- Review backtest results
- Approve, reject, or request modifications
- System implements approved changes

## 🚨 Troubleshooting

### Common Issues

**Database Connection Errors:**
```bash
# Check if TimescaleDB is running
docker-compose ps timescaledb

# View logs
docker-compose logs timescaledb

# Restart
docker-compose restart timescaledb
```

**API Rate Limits:**
- Binance: 1200 requests/minute (we stay well below)
- Twitter: Check your tier limits
- Reddit: 60 requests/minute

**Memory Issues:**
- Increase Docker memory allocation (8GB recommended)
- Reduce `DATA_RETENTION_DAYS` in .env
- Clear old data: `python scripts/cleanup_old_data.py`

**Model Training Fails:**
- Check if sufficient historical data exists
- Verify `MODEL_LOOKBACK_DAYS` in .env
- Review logs in `logs/errors.log`

### Getting Help

1. Check logs: `tail -f logs/trading_system.log`
2. Review error log: `tail -f logs/errors.log`
3. Check Grafana system health dashboard
4. Review audit log in database: `SELECT * FROM audit_log ORDER BY time DESC LIMIT 50;`

## 📚 Additional Documentation

- [Project Roadmap](docs/project_roadmap.md) - Development phases and timeline
- [Future Assets Expansion](docs/future_assets_expansion.md) - Planned asset classes
- [Database Schema](infrastructure/docker/init-db.sql) - Complete database structure

## ⚠️ Disclaimer

**This system is for educational and research purposes. Cryptocurrency trading carries significant risk.**

- Start with paper trading
- Never invest more than you can afford to lose
- Past performance does not guarantee future results
- The system can lose money
- You are responsible for your trading decisions
- Comply with all applicable laws and regulations

## 📄 License

Proprietary - All Rights Reserved

## 🤝 Contributing

This is a private project. For questions or suggestions, contact the project owner.

---

**Last Updated:** 2025-11-01
**Version:** 1.0.0 (Phase 1 - Foundation)
**Status:** In Development

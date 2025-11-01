# Quick Start Guide

Get your autonomous trading system running in 15 minutes.

## Prerequisites Checklist

- [ ] Docker Desktop installed and running
- [ ] Python 3.11+ installed
- [ ] 8GB+ RAM available
- [ ] Binance account created (testnet for practice)
- [ ] Anthropic API key (for Claude)

## Step 1: Get API Keys (10 min)

### Essential Keys

**1. Binance API** (Required - Free)
1. Go to https://testnet.binance.vision/ (for practice)
2. Click "Generate HMAC_SHA256 Key"
3. Save the API Key and Secret Key

For live trading (later):
1. Go to https://www.binance.com/
2. Account → API Management
3. Create new API key
4. Enable "Enable Spot & Margin Trading"
5. Save key and secret

**2. Anthropic API** (Required - Paid)
1. Go to https://console.anthropic.com/
2. Account Settings → API Keys
3. Create new key
4. Copy the key (starts with `sk-ant-`)

### Recommended Keys (for full features)

**3. Twitter API** (Optional - Free tier available)
1. Go to https://developer.twitter.com/
2. Sign up for developer account
3. Create new app
4. Generate Bearer Token
5. Save the token

**4. Reddit API** (Optional - Free)
1. Go to https://www.reddit.com/prefs/apps
2. Create new app (select "script")
3. Copy client ID and secret

**5. CryptoPanic** (Optional - Free tier available)
1. Go to https://cryptopanic.com/developers/api/
2. Sign up and get free API key

## Step 2: Configure Environment (3 min)

1. **Navigate to project:**
```bash
cd "/Users/bradmancini/Library/CloudStorage/OneDrive-aevance.com/03_Atvia Entities/03_Atmospherique Pty Ltd/App Development/01_Terminal_Dev_Auto_Trader"
```

2. **Copy environment template:**
```bash
cp .env.template .env
```

3. **Edit .env file:**
```bash
nano .env  # or use your favorite editor
```

4. **Update these essential values:**
```bash
# Binance
BINANCE_API_KEY=your_testnet_key_here
BINANCE_API_SECRET=your_testnet_secret_here
BINANCE_TESTNET=true

# Claude
ANTHROPIC_API_KEY=sk-ant-your_key_here

# Email (for notifications)
NOTIFICATION_EMAIL=your_email@gmail.com

# Optional: Add Twitter, Reddit, CryptoPanic keys if you have them
```

5. **Save and exit** (Ctrl+X, then Y, then Enter in nano)

## Step 3: Start Infrastructure (2 min)

```bash
# Start databases and monitoring
docker-compose up -d

# Wait 30 seconds for services to start, then check status
docker-compose ps

# You should see all services "Up" and "healthy"
```

**Expected output:**
```
NAME                    STATUS
trading_timescaledb     Up (healthy)
trading_redis           Up (healthy)
trading_grafana         Up
trading_prometheus      Up
trading_loki            Up
```

**If services aren't healthy:**
```bash
# Check logs
docker-compose logs timescaledb
docker-compose logs redis

# Restart if needed
docker-compose restart
```

## Step 4: Install Python Dependencies (3 min)

```bash
# Create virtual environment (recommended)
python3 -m venv venv

# Activate it
source venv/bin/activate  # Mac/Linux
# or on Windows:
# venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# This may take 2-3 minutes
```

**Note:** If TA-Lib installation fails:
- **Mac:** `brew install ta-lib` then `pip install TA-Lib`
- **Ubuntu:** `sudo apt-get install ta-lib` then `pip install TA-Lib`
- **Windows:** Download from https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib

## Step 5: Verify Setup

```bash
# Check database connection
docker-compose exec timescaledb psql -U trading_user -d trading_system -c "SELECT COUNT(*) FROM portfolio_state;"

# Should show: count = 1 (initial portfolio state)

# Check Python can import modules
python -c "from config.config import config; print(f'Config loaded: {config.trading_mode}')"

# Should show: Config loaded: paper
```

## Step 6: Run Paper Trading Test (Quick Test)

Create a simple test script to verify everything works:

```bash
# Create test script
cat > test_system.py << 'EOF'
from utils.logging_config import setup_logging
from utils.database import db
from config.config import config
import logging

logger = logging.getLogger(__name__)

def test_system():
    logger.info("Testing trading system setup...")

    # Test config
    logger.info(f"Trading mode: {config.trading_mode}")
    logger.info(f"Trading pairs: {config.trading_pairs}")

    # Test database
    portfolio = db.get_portfolio_state()
    logger.info(f"Portfolio state: {portfolio}")

    # Test Redis
    from utils.database import redis_client
    redis_client.set("test_key", "test_value", expiry=60)
    value = redis_client.get("test_key")
    logger.info(f"Redis test: {value}")

    logger.info("✅ System test passed!")

if __name__ == "__main__":
    test_system()
EOF

# Run test
python test_system.py
```

**Expected output:**
```
✅ System test passed!
```

## Step 7: Access Monitoring Dashboards

**Grafana:**
1. Open browser: http://localhost:3000
2. Login: `admin` / `admin` (or your password from .env)
3. Dashboards will be available once the system starts collecting data

**Prometheus (metrics):**
- http://localhost:9090

**Database (optional):**
```bash
# Connect to database
docker-compose exec timescaledb psql -U trading_user -d trading_system

# Run queries
SELECT * FROM portfolio_state ORDER BY time DESC LIMIT 1;

# Exit with \q
```

## Next Steps

### Option A: Run Full System (Recommended for first time)

**Coming in next phase** - We'll build the main orchestrator and agents in the next iteration.

For now, the infrastructure is ready and you can:
1. Explore the database schema
2. Test API connections
3. Review the project structure

### Option B: Start Building Agents

If you're ready to start implementing:

```bash
# We'll create the agents in the next phase, including:
# 1. Price data collector
# 2. Sentiment analyzer
# 3. Technical analysis agent
# 4. ML prediction agent
# 5. Orchestrator
```

## Troubleshooting

### Docker services won't start

```bash
# Stop all
docker-compose down

# Remove volumes (⚠️ deletes data)
docker-compose down -v

# Start fresh
docker-compose up -d
```

### Permission errors on Mac

```bash
# If you get permission errors with OneDrive paths
cd ~
mkdir -p temp-trading-system
# Copy project there and try again
```

### Python dependency installation fails

```bash
# Update pip and setuptools
pip install --upgrade pip setuptools wheel

# Install problematic packages individually
pip install TA-Lib  # If this fails, see Step 4 note

# Try again
pip install -r requirements.txt
```

### Can't connect to database

```bash
# Check if PostgreSQL port is already in use
lsof -i :5432

# If another service is using it, either:
# 1. Stop that service, or
# 2. Change POSTGRES_PORT in docker-compose.yml and .env
```

## Verify Everything is Working

Run this checklist:

- [ ] Docker containers all running (`docker-compose ps`)
- [ ] Python dependencies installed (`pip list | grep pandas`)
- [ ] Config loads without errors
- [ ] Database accessible
- [ ] Redis accessible
- [ ] Grafana loads in browser
- [ ] Test script passes

If all checked, you're ready to proceed! 🎉

## What We Built

**Infrastructure:**
- ✅ TimescaleDB (time-series optimized PostgreSQL)
- ✅ Redis (caching and pub/sub)
- ✅ Grafana (dashboards)
- ✅ Prometheus (metrics)
- ✅ Loki (log aggregation)

**Database Schema:**
- ✅ 15+ tables for prices, sentiment, trades, predictions, etc.
- ✅ Optimized for time-series queries
- ✅ Views for common queries
- ✅ Functions for calculations (Sharpe ratio, etc.)

**Configuration:**
- ✅ Environment-based configuration
- ✅ All parameters in one place
- ✅ Easy to modify for different strategies

**Project Structure:**
- ✅ Organized directory structure
- ✅ Separate concerns (agents, models, utils)
- ✅ Ready for scaling

## Next Phase: Building the Agents

We'll implement:
1. Data collection agents (price, sentiment, news)
2. Technical analysis agent
3. ML prediction agent (XGBoost)
4. Orchestrator (decision maker)
5. Risk management system
6. Order execution
7. Continuous improvement agent

**Estimated time:** 2-3 days of development

---

**Questions or Issues?**

Check:
1. Logs: `tail -f logs/trading_system.log`
2. Docker logs: `docker-compose logs -f`
3. README.md for detailed documentation
4. docs/project_roadmap.md for development plan

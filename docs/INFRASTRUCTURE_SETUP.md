# Infrastructure Setup Guide

Complete step-by-step guide to set up and test the trading system infrastructure.

## Prerequisites

Before you start, ensure you have:

- [ ] Docker Desktop installed and running
- [ ] Python 3.11+ installed (`python3 --version`)
- [ ] At least 8GB free RAM
- [ ] 10GB free disk space
- [ ] Internet connection (for downloading images and packages)

## Step 1: Get API Keys (15-20 minutes)

### 1.1 Binance Testnet (Required)

**For practice trading:**

1. Go to https://testnet.binance.vision/
2. Click "Generate HMAC_SHA256 Key"
3. Save both:
   - API Key
   - Secret Key

**Note:** Testnet gives you fake USDT to practice with!

**For live trading (later):**
1. Create account at https://www.binance.com/
2. Complete KYC verification
3. Enable 2FA
4. Go to Account → API Management
5. Create API key with "Enable Spot & Margin Trading"
6. Whitelist your IP address

### 1.2 Anthropic API (Required)

1. Go to https://console.anthropic.com/
2. Sign up or log in
3. Go to Account Settings → API Keys
4. Click "Create Key"
5. Copy the key (starts with `sk-ant-`)
6. **Important:** This is paid - set up billing

**Pricing:** ~$3 per million input tokens for Haiku, ~$15 for Sonnet
**Estimated monthly cost:** $20-50 depending on usage

### 1.3 Twitter API (Optional but Recommended)

1. Go to https://developer.twitter.com/
2. Sign up for developer account
3. Create new app
4. Navigate to Keys and Tokens
5. Generate Bearer Token
6. Save the Bearer Token

**Note:** Free tier has rate limits (500k tweets/month)

### 1.4 Reddit API (Optional but Recommended)

1. Go to https://www.reddit.com/prefs/apps
2. Scroll down and click "create another app"
3. Fill in details:
   - Name: "Trading Bot"
   - Type: "script"
   - Redirect URI: http://localhost:8080
4. Click "create app"
5. Save:
   - Client ID (under app name)
   - Secret

**Note:** Free with rate limits (60 requests/minute)

### 1.5 CryptoPanic (Optional)

1. Go to https://cryptopanic.com/developers/api/
2. Sign up for free account
3. Get free API key
4. Save the key

### 1.6 Other APIs (Optional)

For future features:
- **Glassnode:** https://glassnode.com/ (on-chain data)
- **CoinGecko:** https://www.coingecko.com/en/api (free tier available)
- **NewsAPI:** https://newsapi.org/ (news aggregation)

## Step 2: Configure Environment (5 minutes)

1. **Navigate to project directory:**
```bash
cd "/Users/bradmancini/Library/CloudStorage/OneDrive-aevance.com/03_Atvia Entities/03_Atmospherique Pty Ltd/App Development/01_Terminal_Dev_Auto_Trader"
```

2. **Copy environment template:**
```bash
cp .env.template .env
```

3. **Edit .env file:**
```bash
# Use your preferred editor
nano .env
# or
code .env
# or
open -a TextEdit .env
```

4. **Update required values:**

```bash
# ============================================
# REQUIRED - Must set these
# ============================================

# Binance (use testnet keys for now)
BINANCE_API_KEY=your_testnet_api_key_here
BINANCE_API_SECRET=your_testnet_secret_here
BINANCE_TESTNET=true

# Anthropic (Claude AI)
ANTHROPIC_API_KEY=sk-ant-your_key_here

# Email for notifications
NOTIFICATION_EMAIL=your_email@gmail.com

# ============================================
# RECOMMENDED - Set if you have them
# ============================================

# Twitter
TWITTER_BEARER_TOKEN=your_bearer_token_here

# Reddit
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_secret

# CryptoPanic
CRYPTOPANIC_API_KEY=your_key

# ============================================
# OPTIONAL - Can set later
# ============================================

# Email provider (for daily summaries)
SENDGRID_API_KEY=your_sendgrid_key
# or use SMTP settings for Gmail

# Database passwords (change from defaults!)
POSTGRES_PASSWORD=choose_secure_password_here
REDIS_PASSWORD=choose_secure_password_here
GRAFANA_ADMIN_PASSWORD=choose_secure_password_here
```

5. **Save the file**

## Step 3: Start Docker Services (5 minutes)

1. **Ensure Docker Desktop is running:**
```bash
# Check Docker is running
docker ps

# If error, start Docker Desktop application
```

2. **Start all services:**
```bash
# From project directory
docker-compose up -d

# This will:
# - Download images (first time: ~2-3 GB, takes 5-10 min)
# - Create containers
# - Initialize database
# - Start all services
```

3. **Wait for services to be healthy:**
```bash
# Check status (wait until all show "Up" and "healthy")
docker-compose ps

# Should see:
# NAME                    STATUS
# trading_timescaledb     Up (healthy)
# trading_redis           Up (healthy)
# trading_grafana         Up
# trading_prometheus      Up
# trading_loki            Up
```

4. **If services aren't healthy after 2 minutes:**
```bash
# Check logs
docker-compose logs timescaledb
docker-compose logs redis

# Common issues:
# - Port already in use (5432, 6379, 3000, 9090)
# - Insufficient memory
# - Docker Desktop not allocated enough resources
```

5. **Verify database initialized:**
```bash
# Check database logs for success message
docker-compose logs timescaledb | grep "initialized successfully"

# You should see: "Trading system database initialized successfully!"
```

## Step 4: Install Python Dependencies (5-10 minutes)

1. **Create virtual environment:**
```bash
# Create venv
python3 -m venv venv

# Activate it
source venv/bin/activate  # Mac/Linux

# On Windows:
# venv\Scripts\activate

# Your prompt should now show (venv)
```

2. **Upgrade pip:**
```bash
pip install --upgrade pip setuptools wheel
```

3. **Install TA-Lib (if needed):**

**Mac:**
```bash
brew install ta-lib
```

**Ubuntu/Debian:**
```bash
sudo apt-get install ta-lib
```

**Windows:**
Download wheel from: https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib
```bash
pip install TA_Lib-0.4.XX-cpXX-cpXX-win_amd64.whl
```

4. **Install Python packages:**
```bash
pip install -r requirements.txt

# This will take 5-10 minutes
# You may see some warnings - these are usually OK
```

5. **Verify installation:**
```bash
# Check key packages installed
pip list | grep -E "pandas|numpy|ccxt|anthropic|sqlalchemy"

# Should see all packages with version numbers
```

## Step 5: Run Infrastructure Tests (5 minutes)

Now let's test everything is working:

```bash
# Make sure you're in the project directory and venv is activated
python scripts/test_infrastructure.py
```

**Expected Output:**

```
==================================================================
  AUTONOMOUS TRADING SYSTEM - INFRASTRUCTURE TEST SUITE
==================================================================

──────────────────────────────────────────────────────────────────
Testing Python imports...
  ✓ pandas
  ✓ numpy
  ✓ sqlalchemy
  ✓ redis
  ✓ ccxt
  ✓ anthropic
  ... (all packages)

──────────────────────────────────────────────────────────────────
Testing configuration...
  ✓ Config loaded
  - Trading mode: paper
  - Trading pairs: ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
  ...

──────────────────────────────────────────────────────────────────
Testing database connection...
  ✓ Connected to PostgreSQL: PostgreSQL 15.X ...
  ✓ TimescaleDB extension installed
  ✓ Found 17 tables
  ✓ All critical tables exist
  ✓ Portfolio initialized (1 records)

──────────────────────────────────────────────────────────────────
Testing Redis connection...
  ✓ Redis set/get working
  ✓ Redis JSON operations working

──────────────────────────────────────────────────────────────────
Testing Binance API...
  - Using Binance TESTNET
  ✓ Public API working - BTC/USDT: $XX,XXX.XX
  ✓ Authenticated API working
  - Testnet USDT balance: XXXXX

──────────────────────────────────────────────────────────────────
Testing Anthropic API...
  ✓ Anthropic API working
  - Response: OK

──────────────────────────────────────────────────────────────────
Testing monitoring endpoints...
  ✓ Grafana accessible at http://localhost:3000
  ✓ Prometheus accessible at http://localhost:9090
  ✓ Loki accessible at http://localhost:3100/ready

==================================================================
  TEST SUMMARY
==================================================================

✓ PASS   Python Imports           All required packages imported successfully
✓ PASS   Configuration            Configuration loaded successfully
✓ PASS   Database                 Database connection and schema validated
✓ PASS   Redis                    Redis connectivity validated
✓ PASS   Binance API              Binance API connectivity validated
✓ PASS   Anthropic API            Anthropic API connectivity validated
✓ PASS   Monitoring Stack         All monitoring endpoints accessible

──────────────────────────────────────────────────────────────────
Results: 7/7 tests passed
==================================================================

🎉 All tests passed! Infrastructure is ready.
```

## Step 6: Access Monitoring Dashboards

### Grafana (Dashboards)

1. **Open browser:** http://localhost:3000
2. **Login:**
   - Username: `admin`
   - Password: Check `GRAFANA_ADMIN_PASSWORD` in `.env` (default: `admin`)
3. **First time:** You'll be prompted to change password

**Note:** Dashboards will be empty until the system starts collecting data.

### Prometheus (Metrics)

1. **Open browser:** http://localhost:9090
2. **Explore metrics:**
   - Click "Graph"
   - Try query: `up` (shows all services)
   - No data yet - metrics will appear when agents start running

### Database (Optional)

```bash
# Connect to database directly
docker-compose exec timescaledb psql -U trading_user -d trading_system

# Run some queries
SELECT * FROM portfolio_state;
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';

# Exit
\q
```

## Step 7: Verify Complete Setup

Run through this checklist:

- [ ] Docker containers running (`docker-compose ps` shows all "Up")
- [ ] Python venv activated (prompt shows `(venv)`)
- [ ] All Python packages installed (`pip list | wc -l` shows 50+)
- [ ] `.env` file configured with API keys
- [ ] Infrastructure test passes (7/7)
- [ ] Grafana accessible at http://localhost:3000
- [ ] Prometheus accessible at http://localhost:9090
- [ ] Database has portfolio initialized

**If all checked:** ✅ Infrastructure setup complete!

## Troubleshooting

### Docker Issues

**"Port already in use"**
```bash
# Find what's using port 5432 (PostgreSQL)
lsof -i :5432

# Kill the process or change port in docker-compose.yml
```

**"Cannot connect to Docker daemon"**
```bash
# Start Docker Desktop
# Wait for it to fully start (whale icon in menu bar)
```

**"Service unhealthy"**
```bash
# Check specific service logs
docker-compose logs timescaledb
docker-compose logs redis

# Restart specific service
docker-compose restart timescaledb
```

**"Out of memory"**
```bash
# Docker Desktop → Settings → Resources
# Increase Memory to 8GB
# Increase CPU to 4 cores
# Click "Apply & Restart"
```

### Database Issues

**"Database does not exist"**
```bash
# Stop containers
docker-compose down

# Remove volumes (⚠️ deletes data)
docker-compose down -v

# Restart
docker-compose up -d

# Check initialization
docker-compose logs timescaledb | tail -50
```

**"Connection refused"**
```bash
# Wait 30 seconds after docker-compose up
# TimescaleDB takes time to initialize

# Check it's running
docker-compose ps timescaledb

# Check logs
docker-compose logs -f timescaledb
```

### Python Issues

**"ModuleNotFoundError"**
```bash
# Ensure venv is activated
source venv/bin/activate

# Reinstall package
pip install <package-name>

# Or reinstall all
pip install -r requirements.txt --force-reinstall
```

**"TA-Lib installation failed"**
```bash
# Mac
brew install ta-lib
pip install TA-Lib

# Ubuntu
sudo apt-get install ta-lib
pip install TA-Lib

# Windows - download wheel file
# From: https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib
pip install TA_Lib-0.4.XX-cpXX-cpXX-win_amd64.whl
```

### API Issues

**"Invalid API key"**
- Double-check you copied the full key (no spaces)
- Verify you're using testnet keys with `BINANCE_TESTNET=true`
- Regenerate key if needed

**"Rate limit exceeded"**
- Normal for free tier APIs
- System will handle this with backoff/retry
- Consider upgrading API tier if needed

**"Anthropic authentication failed"**
- Verify API key starts with `sk-ant-`
- Check billing is set up in Anthropic console
- Try regenerating the key

## Next Steps

Once infrastructure is set up and all tests pass:

1. **Review system architecture**
   - Read `README.md`
   - Review `docs/project_roadmap.md`

2. **Understand the database schema**
   - Check `infrastructure/docker/init-db.sql`
   - Explore tables in database

3. **Ready to build agents!**
   - Start with price data collector
   - Then sentiment analyzer
   - Then technical analysis agent
   - Then orchestrator

## Stopping/Starting the System

**Stop everything:**
```bash
docker-compose down
```

**Start everything:**
```bash
docker-compose up -d
```

**View logs:**
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f timescaledb
docker-compose logs -f redis
```

**Restart specific service:**
```bash
docker-compose restart timescaledb
docker-compose restart redis
```

**Remove everything (including data):**
```bash
# ⚠️ WARNING: This deletes all data!
docker-compose down -v
```

## Health Check Commands

Quick commands to verify system health:

```bash
# Docker services
docker-compose ps

# Database connection
docker-compose exec timescaledb psql -U trading_user -d trading_system -c "SELECT COUNT(*) FROM portfolio_state;"

# Redis connection
docker-compose exec redis redis-cli -a $REDIS_PASSWORD ping

# Python environment
source venv/bin/activate
python -c "from config.config import config; print('Config OK')"

# Full test
python scripts/test_infrastructure.py
```

---

**Setup Time:** ~30-45 minutes total
**Status:** Infrastructure ready for agent development
**Next:** Build data collection agents

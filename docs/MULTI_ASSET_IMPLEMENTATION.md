# Multi-Asset Trading System Implementation

## Overview

This document describes the multi-asset trading infrastructure that extends the system beyond crypto to support stocks, forex, commodities, leveraged ETFs, and meme stocks.

**Status:** Foundation Complete - Ready for Phase 1 Activation
**Created:** 2025-11-01
**Last Updated:** 2025-11-01

---

## What Has Been Built

### 1. Asset Configuration System (`config/assets_config.yaml`)

A comprehensive YAML configuration file defining **22 tradable assets** across **6 asset classes**:

#### Asset Classes Configured:
- **Crypto** (Active): BTC/USDT, ETH/USDT
- **Stocks** (Phase 1): NVDA, TSLA, AMD
- **Leveraged ETFs** (Phase 2): TQQQ, SOXL, UVXY
- **Forex Majors** (Phase 3): GBP/JPY
- **Emerging Market Forex** (Phase 4): USD/TRY, USD/ZAR, USD/BRL, AUD/JPY
- **Commodities** (Phase 5): Natural Gas, Silver, Crude Oil
- **Meme/Speculative Stocks** (Phase 6): GME, AMC, OPEN, RGTI, QUBT, DNUT

#### Features Per Asset:
- Asset class classification
- Enable/disable toggle
- Volatility score (1-10)
- Leading indicators list
- Data source requirements
- Risk parameters (position sizing, stop loss, special rules)
- Exchange and trading specifications

#### Global Risk Management:
```yaml
risk_management:
  max_portfolio_heat: 0.25          # 25% total risk
  max_correlation_exposure: 0.60    # Max 60% in correlated assets
  max_single_asset_class: 0.40      # Max 40% in one class
  emergency_stop_drawdown: 0.25     # Emergency stop at 25% DD
  daily_loss_limit: 0.05            # Stop if down 5% in a day
```

---

### 2. Asset Manager Class (`utils/asset_manager.py`)

A Python class that manages all asset operations:

#### Key Features:
```python
from utils.asset_manager import AssetManager

manager = AssetManager()

# Get enabled assets
enabled = manager.get_enabled_assets()  # Currently: BTC/USDT, ETH/USDT

# Get assets by class
stocks = manager.get_assets_by_class(AssetClass.STOCKS)  # NVDA, TSLA, AMD (disabled)

# Check if class is enabled
if manager.is_class_enabled(AssetClass.CRYPTO):
    print("Crypto trading active")

# Calculate position size
asset = manager.get_asset('NVDA')
position_size = manager.calculate_position_size(
    asset=asset,
    portfolio_value=10000
)

# Check phase activation requirements
metrics = {
    'crypto_profitable_days': 35,
    'sharpe_ratio_min': 1.8,
    'max_drawdown_max': 0.12,
    'win_rate_min': 0.55
}

if manager.can_enable_phase('phase_1_stocks', metrics):
    manager.enable_asset_class(AssetClass.STOCKS)
```

#### Core Methods:
- `get_asset(symbol)` - Get specific asset configuration
- `get_enabled_assets()` - List all active assets
- `get_assets_by_class(AssetClass)` - Filter by class
- `calculate_position_size()` - Risk-adjusted sizing
- `can_enable_phase()` - Check activation requirements
- `enable_asset_class()` - Activate new asset class
- `validate_portfolio_allocation()` - Enforce limits

---

### 3. Database Schema Extension (`infrastructure/docker/multi-asset-schema-extension.sql`)

Extends the existing TimescaleDB schema to support multi-asset trading:

#### New Tables Created:

**asset_registry**
- Stores all tradable assets and their configurations
- Syncs with `assets_config.yaml`
- Tracks enabled/disabled status

**asset_class_config**
- Configuration for each asset class
- Allocation limits, position sizing rules
- Phase activation tracking

**data_source_registry**
- Manages API connections
- Rate limiting tracking
- Cost monitoring

**phase_activation_log**
- Audit trail of phase activations
- Performance metrics that triggered activation
- Notes and timestamps

**asset_performance**
- Per-asset performance metrics
- Win rate, profit factor, Sharpe ratio
- Allows comparison across asset classes

**leading_indicators**
- Storage for asset-specific indicators
- Options flow, sentiment, macro data
- Time-series optimized (hypertable)

**social_sentiment**
- Reddit, Twitter, StockTwits data
- Mention counts, sentiment scores
- Critical for meme stock trading

**options_flow**
- Unusual options activity
- Sweeps, blocks, large trades
- For stocks with active options

**economic_calendar**
- Scheduled economic events
- Impact forecasts
- Volatility warnings

**asset_correlations**
- Tracks correlations between assets
- Prevents over-concentration
- Updated periodically

#### Schema Modifications:
All existing tables extended with `asset_class` column:
- `price_data` - Now supports stocks, forex, commodities
- `trading_decisions` - Tracks decision asset class
- `agent_signals` - Class-aware signals
- `predictions` - Model predictions per asset
- `trades` - Executed trades with asset class

---

## Data Sources Configured

The system is configured to integrate with 9 data source types:

### Currently Active (Crypto):
- ✅ **ccxt_binance** - Crypto price data
- ✅ **glassnode** - On-chain metrics
- ✅ **etherscan** - Ethereum data
- ✅ **coinmetrics** - Crypto analytics
- ✅ **defillama** - DeFi data

### Ready for Activation (Other Assets):
- ⏸️ **polygon_io** - Stocks & options ($250/month)
- ⏸️ **alpha_vantage** - Stocks & forex (free tier)
- ⏸️ **oanda_api** - Forex & commodities
- ⏸️ **reddit_api** - Social sentiment (free)
- ⏸️ **twitter_api** - Tweet monitoring
- ⏸️ **eia_api** - Energy data (free)
- ⏸️ **fred_api** - Economic data (free)
- ⏸️ **unusual_whales** - Options flow ($50/month)

---

## Phase Activation System

The system includes automatic phase gating based on performance:

### Phase Requirements:

**Phase 0: Crypto Only** (Current State)
- ✅ Active and running
- ✅ 2 assets enabled (BTC/USDT, ETH/USDT)

**Phase 1: Add Liquid Stocks**
Requirements to activate:
- 30+ days profitable in crypto
- Sharpe Ratio > 1.5 over 60 days
- Max Drawdown < 15%
- Win Rate > 50%

Assets to enable: NVDA, TSLA, AMD

**Phase 2: Leveraged ETFs**
Requirements:
- Phase 1 complete
- 60+ days profitable
- Sharpe Ratio > 1.8

Assets: TQQQ, SOXL, UVXY

**Phase 3-6:** See `future_assets_expansion.md`

### Checking Phase Readiness:

```python
manager = AssetManager()

# Get current performance metrics
metrics = get_current_metrics()  # From database

# Check if Phase 1 can be activated
if manager.can_enable_phase('phase_1_stocks', metrics):
    print("✅ Ready for Phase 1!")
    print("📊 Performance metrics met all requirements")
    print("🚀 Can activate NVDA, TSLA, AMD trading")

    # Activate Phase 1
    manager.enable_asset_class(AssetClass.STOCKS)
    manager.enable_asset('NVDA')
    manager.enable_asset('TSLA')
    manager.enable_asset('AMD')
else:
    print("⏳ Not ready for Phase 1 yet")
    print("📉 Continue optimizing crypto strategy")
```

---

## Asset-Specific Features

### NVDA (Nvidia)
**Leading Indicators:**
- Options flow analysis
- Semiconductor index (SOX)
- AI news sentiment
- GPU shortage/availability
- Data center buildout news

**Risk Parameters:**
- Max position: 10%
- Stop loss: 8%
- Earnings blackout: 3 days before earnings

### TSLA (Tesla)
**Leading Indicators:**
- Elon Musk tweets (monitored via Twitter API)
- Quarterly delivery numbers
- EV sales data
- FSD regulatory news

**Special Features:**
- Tweet monitor: `true`
- Monitored accounts: @elonmusk
- Max position: 8% (Musk risk)
- Stop loss: 10% (high volatility)

### GBP/JPY "The Beast"
**Characteristics:**
- 100+ pip daily moves
- Risk sentiment barometer

**Leading Indicators:**
- UK economic data
- Japan BOJ policy
- Brexit-related news
- Risk-on/risk-off sentiment

**Risk Parameters:**
- Stop loss: 50 pips
- Take profit: 100 pips
- Max position: 10%

### TQQQ (3x Leveraged NASDAQ)
**Special Risks:**
- Daily rebalancing decay
- Only hold in trending markets
- Max hold: 5 days
- Sideways market avoidance: `true`

**Risk Parameters:**
- Max position: 5% (leverage!)
- Stop loss: 5% (tight)
- Decay warning: enabled

---

## How to Use the System

### 1. View Current Configuration

```bash
cd /path/to/trading/system
PYTHONPATH=. venv/bin/python utils/asset_manager.py
```

Output:
```
=== Asset Manager Summary ===
total_assets: 22
enabled_assets: 2
enabled_classes: ['crypto']

=== Enabled Assets ===
- BTC/USDT (Bitcoin) - crypto
- ETH/USDT (Ethereum) - crypto

=== Phase 1 Stocks (Disabled) ===
✗ NVDA (Nvidia Corporation) - $132
✗ TSLA (Tesla Inc) - $400
✗ AMD (Advanced Micro Devices)
```

### 2. Apply Database Schema Extension

When ready to support multi-asset:

```bash
# Apply schema extension to database
docker exec -i timescaledb psql -U trading_user -d trading_system < infrastructure/docker/multi-asset-schema-extension.sql
```

This adds:
- asset_registry table
- asset_class_config table
- leading_indicators table
- social_sentiment table
- options_flow table
- And extends existing tables

### 3. Enable Phase 1 (When Ready)

Modify `config/assets_config.yaml`:

```yaml
asset_classes:
  stocks:
    enabled: true  # Change from false

assets:
  NVDA:
    enabled: true  # Change from false
  TSLA:
    enabled: true
  AMD:
    enabled: true
```

Or programmatically:
```python
manager = AssetManager()
manager.enable_asset_class(AssetClass.STOCKS)
manager.enable_asset('NVDA')
```

---

## Data Source Integration

### Required for Phase 1 (Stocks):

**Polygon.io Setup:**
```bash
# Add to .env
export POLYGON_API_KEY="your_key_here"
```

Cost: $250/month for real-time data

**Alpha Vantage (Free Alternative):**
```bash
export ALPHA_VANTAGE_KEY="your_key_here"
```

Free tier: 5 requests/minute (sufficient for testing)

### Sentiment Data (Meme Stocks):

**Reddit API:**
```bash
export REDDIT_CLIENT_ID="your_id"
export REDDIT_SECRET="your_secret"
```

Free, rate limited to 60 req/minute

**Twitter API (For TSLA/Musk monitoring):**
```bash
export TWITTER_BEARER_TOKEN="your_token"
```

---

## Integration with Existing Agents

The multi-asset system integrates seamlessly:

### Orchestrator Updates Needed:
```python
from utils.asset_manager import AssetManager, AssetClass

class TradingOrchestrator:
    def __init__(self):
        self.asset_manager = AssetManager()
        # ... existing code

    def run_cycle(self):
        # Get enabled assets (crypto + any activated phases)
        assets = self.asset_manager.get_enabled_assets()

        for asset in assets:
            # Asset-specific logic
            if asset.is_crypto:
                self._trade_crypto(asset)
            elif asset.asset_class == AssetClass.STOCKS:
                self._trade_stocks(asset)
            elif asset.is_forex:
                self._trade_forex(asset)

            # Apply asset-specific risk
            position_size = self.asset_manager.calculate_position_size(
                asset=asset,
                portfolio_value=self.portfolio_value
            )
```

---

## Risk Management

### Portfolio-Level Controls:
- **Max Portfolio Heat:** 25% (total risk across all positions)
- **Max Single Asset Class:** 40% (diversification requirement)
- **Max Correlation Exposure:** 60% (avoid concentrated correlation)
- **Emergency Stop:** Trading halts at 25% drawdown
- **Daily Loss Limit:** Stop if down 5% in a single day

### Asset-Level Controls:
Each asset has individual:
- Maximum position size
- Stop loss percentage
- Leverage limits (for ETFs)
- Pip-based stops (for forex)
- Special rules (earnings blackouts, tweet monitoring, etc.)

---

## Capital Requirements

| Phase | Assets | Minimum Capital | Recommended |
|-------|--------|----------------|-------------|
| Crypto Only | BTC, ETH | $1,000 | $2,500 |
| + Stocks | Add NVDA, TSLA, AMD | $3,000 | $5,000 |
| + Leveraged ETFs | Add TQQQ, SOXL | $5,000 | $10,000 |
| + Forex | Add GBP/JPY | $5,000 | $10,000 |
| + Commodities | Add Oil, NG, Silver | $10,000 | $25,000 |
| Full Suite | All 22 assets | $15,000 | $50,000 |

---

## Testing

### Unit Tests Needed:
```bash
# Test asset manager
pytest tests/test_asset_manager.py

# Test position sizing
pytest tests/test_risk_management.py

# Test phase activation logic
pytest tests/test_phase_activation.py
```

### Integration Tests:
- Multi-asset portfolio allocation
- Correlation monitoring
- Data source failover
- Phase activation flow

---

## Next Steps

### Immediate (To Complete Foundation):
1. ✅ Asset configuration system - **COMPLETE**
2. ✅ Asset Manager class - **COMPLETE**
3. ✅ Database schema extension - **COMPLETE**
4. ⏳ Data source adapters (Polygon, Alpha Vantage, etc.)
5. ⏳ Phase activation automation
6. ⏳ Multi-asset tests

### Before Phase 1 Activation:
1. Achieve 30+ profitable days in crypto
2. Sharpe Ratio > 1.5
3. Max Drawdown < 15%
4. Set up Polygon.io or Alpha Vantage API
5. Test stock data collection
6. Run Phase 1 backtest

### Phase 1 Launch Checklist:
- [ ] Performance requirements met
- [ ] Stock data API configured
- [ ] Database schema extended
- [ ] Agents updated for multi-asset
- [ ] Risk management tested
- [ ] Position sizing validated
- [ ] Grafana dashboard updated
- [ ] Monitoring alerts configured

---

## Files Created

1. **config/assets_config.yaml** - Asset configurations (22 assets)
2. **utils/asset_manager.py** - Asset management class
3. **infrastructure/docker/multi-asset-schema-extension.sql** - Database extension
4. **docs/MULTI_ASSET_IMPLEMENTATION.md** - This document

---

## Summary

### ✅ What's Ready:
- Complete asset configuration for 22 assets across 6 classes
- Asset Manager with position sizing, risk management, phase activation
- Database schema ready for multi-asset trading
- Data source registry and integration points
- Phase-based expansion framework

### ⏳ What's Needed:
- Data source adapter implementations
- Agent modifications for multi-asset
- Testing and validation
- Performance monitoring per asset class

### 🎯 When to Activate:
**Phase 1 can be activated when:**
- Crypto strategy is consistently profitable (30+ days)
- Risk management is proven (Sharpe > 1.5, DD < 15%)
- Data APIs are configured and tested
- Team is comfortable expanding beyond crypto

The foundation is complete. The system is ready to scale from 2 crypto assets to 22+ assets across 6 asset classes when performance metrics justify expansion.

**Status: Foundation Complete - Ready for Phase 1 Preparation**

---

**Last Updated:** 2025-11-01
**Next Review:** When crypto strategy hits 30-day profitability milestone

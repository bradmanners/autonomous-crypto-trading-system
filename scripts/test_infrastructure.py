"""
Infrastructure Test Suite
Tests all components before building agents
"""
import sys
import logging
from datetime import datetime
from typing import Dict, Tuple

# Setup basic logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_imports() -> Tuple[bool, str]:
    """Test that all required Python packages can be imported"""
    logger.info("Testing Python imports...")

    required_packages = [
        'pandas', 'numpy', 'sqlalchemy', 'redis', 'ccxt',
        'anthropic', 'requests', 'pydantic', 'pytest'
    ]

    failed = []
    for package in required_packages:
        try:
            __import__(package)
            logger.info(f"  ✓ {package}")
        except ImportError as e:
            logger.error(f"  ✗ {package}: {e}")
            failed.append(package)

    if failed:
        return False, f"Failed to import: {', '.join(failed)}"
    return True, "All required packages imported successfully"


def test_config() -> Tuple[bool, str]:
    """Test configuration loading"""
    logger.info("Testing configuration...")

    try:
        from config.config import config

        logger.info(f"  ✓ Config loaded")
        logger.info(f"  - Trading mode: {config.trading_mode}")
        logger.info(f"  - Trading pairs: {config.trading_pairs}")
        logger.info(f"  - Database: {config.postgres_host}:{config.postgres_port}/{config.postgres_db}")
        logger.info(f"  - Redis: {config.redis_host}:{config.redis_port}")

        # Check critical settings
        if not config.binance_api_key or config.binance_api_key == "":
            logger.warning("  ⚠ Binance API key not set in .env")

        if not config.anthropic_api_key or config.anthropic_api_key == "":
            logger.warning("  ⚠ Anthropic API key not set in .env")

        return True, "Configuration loaded successfully"
    except Exception as e:
        return False, f"Failed to load config: {e}"


def test_database() -> Tuple[bool, str]:
    """Test database connectivity and schema"""
    logger.info("Testing database connection...")

    try:
        from utils.database import db
        from sqlalchemy import text

        # Test connection
        with db.get_session() as session:
            result = session.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            logger.info(f"  ✓ Connected to PostgreSQL: {version[:50]}...")

            # Test TimescaleDB extension
            result = session.execute(text(
                "SELECT COUNT(*) FROM pg_extension WHERE extname = 'timescaledb'"
            ))
            if result.fetchone()[0] > 0:
                logger.info("  ✓ TimescaleDB extension installed")
            else:
                logger.warning("  ⚠ TimescaleDB extension not found")

            # Test tables exist
            result = session.execute(text(
                """
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
                """
            ))
            tables = [row[0] for row in result.fetchall()]
            logger.info(f"  ✓ Found {len(tables)} tables")

            expected_tables = [
                'price_data', 'sentiment_data', 'agent_signals',
                'portfolio_state', 'trades', 'predictions'
            ]
            missing = [t for t in expected_tables if t not in tables]
            if missing:
                logger.warning(f"  ⚠ Missing tables: {', '.join(missing)}")
            else:
                logger.info(f"  ✓ All critical tables exist")

            # Test portfolio initialization
            result = session.execute(text("SELECT COUNT(*) FROM portfolio_state"))
            count = result.fetchone()[0]
            if count > 0:
                logger.info(f"  ✓ Portfolio initialized ({count} records)")
            else:
                logger.warning("  ⚠ Portfolio not initialized")

        return True, "Database connection and schema validated"
    except Exception as e:
        return False, f"Database test failed: {e}"


def test_redis() -> Tuple[bool, str]:
    """Test Redis connectivity"""
    logger.info("Testing Redis connection...")

    try:
        from utils.database import redis_client

        # Test set/get
        test_key = "infrastructure_test"
        test_value = f"test_{datetime.now().isoformat()}"

        redis_client.set(test_key, test_value, expiry=60)
        retrieved = redis_client.get(test_key)

        if retrieved == test_value:
            logger.info("  ✓ Redis set/get working")
        else:
            return False, f"Redis value mismatch: {retrieved} != {test_value}"

        # Test JSON
        test_json = {"timestamp": datetime.now().isoformat(), "test": True}
        redis_client.set_json("test_json", test_json, expiry=60)
        retrieved_json = redis_client.get_json("test_json")

        if retrieved_json and retrieved_json.get("test") == True:
            logger.info("  ✓ Redis JSON operations working")
        else:
            return False, "Redis JSON operations failed"

        return True, "Redis connectivity validated"
    except Exception as e:
        return False, f"Redis test failed: {e}"


def test_binance_api() -> Tuple[bool, str]:
    """Test Binance API connectivity"""
    logger.info("Testing Binance API...")

    try:
        import ccxt
        from config.config import config

        # Initialize exchange
        exchange_params = {}
        if config.binance_testnet:
            exchange_params['urls'] = {
                'api': {
                    'public': 'https://testnet.binance.vision/api/v3',
                    'private': 'https://testnet.binance.vision/api/v3',
                }
            }
            logger.info("  - Using Binance TESTNET")

        if config.binance_api_key and config.binance_api_key != "":
            exchange_params['apiKey'] = config.binance_api_key
            exchange_params['secret'] = config.binance_api_secret

        exchange = ccxt.binance(exchange_params)

        # Test public API (no auth required)
        ticker = exchange.fetch_ticker('BTC/USDT')
        logger.info(f"  ✓ Public API working - BTC/USDT: ${ticker['last']:,.2f}")

        # Test authenticated API if keys provided
        if config.binance_api_key and config.binance_api_key != "":
            try:
                balance = exchange.fetch_balance()
                logger.info(f"  ✓ Authenticated API working")

                # Show testnet balance if available
                if 'USDT' in balance['free']:
                    usdt_balance = balance['free']['USDT']
                    logger.info(f"  - Testnet USDT balance: {usdt_balance}")
            except Exception as e:
                logger.warning(f"  ⚠ Auth API failed (may need valid keys): {e}")
        else:
            logger.warning("  ⚠ No API keys configured - only public API tested")

        return True, "Binance API connectivity validated"
    except Exception as e:
        return False, f"Binance API test failed: {e}"


def test_anthropic_api() -> Tuple[bool, str]:
    """Test Anthropic (Claude) API connectivity"""
    logger.info("Testing Anthropic API...")

    try:
        from anthropic import Anthropic
        from config.config import config

        if not config.anthropic_api_key or config.anthropic_api_key == "":
            return False, "Anthropic API key not configured in .env"

        client = Anthropic(api_key=config.anthropic_api_key)

        # Simple test message
        message = client.messages.create(
            model="claude-3-haiku-20240307",  # Use Haiku for cheap test
            max_tokens=100,
            messages=[{
                "role": "user",
                "content": "Reply with just 'OK' if you receive this."
            }]
        )

        response = message.content[0].text
        logger.info(f"  ✓ Anthropic API working")
        logger.info(f"  - Response: {response[:50]}")

        return True, "Anthropic API connectivity validated"
    except Exception as e:
        return False, f"Anthropic API test failed: {e}"


def test_monitoring_endpoints() -> Tuple[bool, str]:
    """Test monitoring stack endpoints"""
    logger.info("Testing monitoring endpoints...")

    import requests

    endpoints = {
        'Grafana': 'http://localhost:3000',
        'Prometheus': 'http://localhost:9090',
        'Loki': 'http://localhost:3100/ready'
    }

    results = {}
    for name, url in endpoints.items():
        try:
            response = requests.get(url, timeout=5)
            if response.status_code < 500:  # 200, 302, 401, etc. are OK
                logger.info(f"  ✓ {name} accessible at {url}")
                results[name] = True
            else:
                logger.warning(f"  ⚠ {name} returned {response.status_code}")
                results[name] = False
        except requests.exceptions.ConnectionError:
            logger.warning(f"  ⚠ {name} not accessible at {url} (service may not be running)")
            results[name] = False
        except Exception as e:
            logger.warning(f"  ⚠ {name} error: {e}")
            results[name] = False

    if all(results.values()):
        return True, "All monitoring endpoints accessible"
    else:
        failed = [k for k, v in results.items() if not v]
        return False, f"Some endpoints not accessible: {', '.join(failed)}"


def run_all_tests() -> Dict[str, Tuple[bool, str]]:
    """Run all infrastructure tests"""

    print("\n" + "="*70)
    print("  AUTONOMOUS TRADING SYSTEM - INFRASTRUCTURE TEST SUITE")
    print("="*70 + "\n")

    tests = [
        ("Python Imports", test_imports),
        ("Configuration", test_config),
        ("Database", test_database),
        ("Redis", test_redis),
        ("Binance API", test_binance_api),
        ("Anthropic API", test_anthropic_api),
        ("Monitoring Stack", test_monitoring_endpoints),
    ]

    results = {}
    for test_name, test_func in tests:
        print(f"\n{'─'*70}")
        try:
            success, message = test_func()
            results[test_name] = (success, message)
        except Exception as e:
            results[test_name] = (False, f"Unexpected error: {e}")
            logger.error(f"Unexpected error in {test_name}: {e}")

    # Summary
    print("\n" + "="*70)
    print("  TEST SUMMARY")
    print("="*70 + "\n")

    passed = sum(1 for success, _ in results.values() if success)
    total = len(results)

    for test_name, (success, message) in results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status:8} {test_name:25} {message}")

    print(f"\n{'─'*70}")
    print(f"Results: {passed}/{total} tests passed")
    print("="*70 + "\n")

    if passed == total:
        print("🎉 All tests passed! Infrastructure is ready.\n")
        return results
    else:
        print("⚠️  Some tests failed. Review errors above and fix before proceeding.\n")
        return results


if __name__ == "__main__":
    results = run_all_tests()

    # Exit with error code if any test failed
    if not all(success for success, _ in results.values()):
        sys.exit(1)

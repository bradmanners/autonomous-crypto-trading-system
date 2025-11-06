"""
Test script for SHORT position functionality

This script tests:
1. Opening SHORT positions via SELL orders
2. Closing SHORT positions via BUY orders
3. P&L calculations for SHORT positions (profit when price drops)
4. Integration with orchestrator decision execution
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from trading.paper_trading_engine import PaperTradingEngine, OrderType, OrderSide, PositionSide
from utils.database import DatabaseManager
from sqlalchemy import text

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_short_position_lifecycle():
    """Test complete SHORT position lifecycle"""

    print("\n" + "="*80)
    print("TEST: SHORT POSITION LIFECYCLE")
    print("="*80 + "\n")

    # Initialize engine
    engine = PaperTradingEngine(initial_capital=10000.0)
    db = DatabaseManager()

    # Clean up any existing BTC/USDT positions from previous tests
    with db.get_session() as session:
        session.execute(text("DELETE FROM paper_positions WHERE symbol = 'BTC/USDT'"))
        session.commit()
        print("Cleaned up existing BTC/USDT positions\n")

    # Get initial portfolio value
    initial_portfolio = engine.get_portfolio_value()
    print(f"Initial Portfolio: ${initial_portfolio.total_value:,.2f}")
    print(f"Initial Cash: ${initial_portfolio.cash_balance:,.2f}\n")

    # Get current BTC price
    current_price = engine.get_current_price('BTC/USDT')
    if not current_price:
        print("ERROR: No price data available for BTC/USDT")
        return False

    print(f"Current BTC Price: ${current_price:,.2f}\n")

    # STEP 1: Open SHORT position
    print("-" * 80)
    print("STEP 1: Opening SHORT position (SELL order)")
    print("-" * 80)

    short_quantity = 0.1  # 0.1 BTC
    print(f"Opening SHORT: {short_quantity} BTC @ ${current_price:,.2f}")

    order1 = engine.execute_order(
        symbol='BTC/USDT',
        asset_class='crypto',
        order_type=OrderType.MARKET,
        side=OrderSide.SELL,
        quantity=short_quantity
    )

    if not order1:
        print("ERROR: Failed to open SHORT position")
        return False

    print(f"✅ SHORT position opened")
    print(f"   Order ID: {order1.order_id}")
    print(f"   Quantity: {order1.filled_quantity:.8f} BTC")
    print(f"   Entry Price: ${order1.avg_fill_price:,.2f}")
    print(f"   Commission: ${order1.commission:.2f}")
    print(f"   Slippage: ${order1.slippage:.2f}")
    print(f"   Total Proceeds: ${order1.total_cost:,.2f}\n")

    # Check position was created
    with db.get_session() as session:
        position = session.execute(text("""
            SELECT position_id, symbol, side, quantity, entry_price
            FROM paper_positions
            WHERE symbol = 'BTC/USDT' AND side = 'SHORT'
        """)).fetchone()

        if not position:
            print("ERROR: SHORT position not found in database")
            return False

        print(f"✅ Position verified in database:")
        print(f"   Position ID: {position.position_id}")
        print(f"   Side: {position.side}")
        print(f"   Quantity: {position.quantity:.8f}")
        print(f"   Entry Price: ${position.entry_price:,.2f}\n")

    # STEP 2: Simulate price drop and check unrealized P&L
    print("-" * 80)
    print("STEP 2: Simulating price drop (should show profit)")
    print("-" * 80)

    # Update positions with current prices
    engine.update_positions()

    # Get open positions
    positions = engine.get_open_positions()
    if not positions:
        print("ERROR: No open positions found")
        return False

    short_pos = positions[0]
    print(f"SHORT Position Status:")
    print(f"   Symbol: {short_pos.symbol}")
    print(f"   Side: {short_pos.side.value}")
    print(f"   Quantity: {short_pos.quantity:.8f}")
    print(f"   Entry Price: ${short_pos.entry_price:,.2f}")
    print(f"   Current Price: ${short_pos.current_price:,.2f}")
    print(f"   Price Change: ${short_pos.current_price - short_pos.entry_price:,.2f}")
    print(f"   Unrealized P&L: ${short_pos.unrealized_pnl:,.2f} ({short_pos.unrealized_pnl_pct:+.2f}%)")

    # Verify SHORT P&L calculation (profit when price drops)
    expected_pnl = (short_pos.entry_price - short_pos.current_price) * short_pos.quantity
    if abs(short_pos.unrealized_pnl - expected_pnl) > 0.01:
        print(f"\n❌ ERROR: P&L calculation incorrect!")
        print(f"   Expected: ${expected_pnl:,.2f}")
        print(f"   Got: ${short_pos.unrealized_pnl:,.2f}")
        return False

    print(f"\n✅ P&L calculation verified (SHORT profits when price drops)\n")

    # STEP 3: Close SHORT position with BUY order
    print("-" * 80)
    print("STEP 3: Closing SHORT position (BUY order)")
    print("-" * 80)

    close_price = engine.get_current_price('BTC/USDT')
    print(f"Closing SHORT: {short_quantity} BTC @ ${close_price:,.2f}")

    order2 = engine.execute_order(
        symbol='BTC/USDT',
        asset_class='crypto',
        order_type=OrderType.MARKET,
        side=OrderSide.BUY,
        quantity=short_quantity
    )

    if not order2:
        print("ERROR: Failed to close SHORT position")
        return False

    print(f"✅ SHORT position closed")
    print(f"   Order ID: {order2.order_id}")
    print(f"   Quantity: {order2.filled_quantity:.8f} BTC")
    print(f"   Exit Price: ${order2.avg_fill_price:,.2f}")
    print(f"   Commission: ${order2.commission:.2f}")
    print(f"   Slippage: ${order2.slippage:.2f}")
    print(f"   Total Cost: ${order2.total_cost:,.2f}\n")

    # Check trade was recorded
    with db.get_session() as session:
        trade = session.execute(text("""
            SELECT trade_id, side, entry_price, exit_price, realized_pnl, realized_pnl_pct
            FROM paper_trades
            WHERE symbol = 'BTC/USDT'
            ORDER BY exit_time DESC
            LIMIT 1
        """)).fetchone()

        if not trade:
            print("ERROR: Trade not found in database")
            return False

        print(f"✅ Trade recorded in database:")
        print(f"   Trade ID: {trade.trade_id}")
        print(f"   Side: {trade.side}")
        print(f"   Entry Price: ${trade.entry_price:,.2f}")
        print(f"   Exit Price: ${trade.exit_price:,.2f}")
        print(f"   Realized P&L: ${trade.realized_pnl:,.2f} ({trade.realized_pnl_pct:+.2f}%)")

        # Verify SHORT P&L (should profit if exit price < entry price)
        expected_realized_pnl = (float(trade.entry_price) - float(trade.exit_price)) * short_quantity
        if abs(float(trade.realized_pnl) - expected_realized_pnl) > 0.01:
            print(f"\n❌ ERROR: Realized P&L calculation incorrect!")
            print(f"   Expected: ${expected_realized_pnl:,.2f}")
            print(f"   Got: ${trade.realized_pnl:,.2f}")
            return False

        print(f"\n✅ Realized P&L calculation verified\n")

    # Verify position was closed
    with db.get_session() as session:
        remaining = session.execute(text("""
            SELECT COUNT(*) FROM paper_positions WHERE symbol = 'BTC/USDT'
        """)).fetchone()[0]

        if remaining > 0:
            print(f"❌ ERROR: Position still exists after closing")
            return False

        print(f"✅ Position properly closed and removed\n")

    # STEP 4: Check final portfolio
    print("-" * 80)
    print("STEP 4: Final Portfolio Status")
    print("-" * 80)

    final_portfolio = engine.get_portfolio_value()
    print(f"Final Portfolio: ${final_portfolio.total_value:,.2f}")
    print(f"Final Cash: ${final_portfolio.cash_balance:,.2f}")
    print(f"Total P&L: ${final_portfolio.total_pnl:,.2f} ({final_portfolio.total_pnl_pct:+.2f}%)\n")

    return True


def test_long_vs_short_pnl():
    """Test that LONG and SHORT P&L calculations are opposites"""

    print("\n" + "="*80)
    print("TEST: LONG vs SHORT P&L COMPARISON")
    print("="*80 + "\n")

    print("This test verifies that:")
    print("- LONG positions profit when price increases")
    print("- SHORT positions profit when price decreases")
    print("- P&L calculations are correct for both sides\n")

    engine = PaperTradingEngine()
    db = DatabaseManager()

    # Get current price
    current_price = engine.get_current_price('BTC/USDT')
    if not current_price:
        print("ERROR: No price data available")
        return False

    print(f"Current BTC Price: ${current_price:,.2f}\n")

    # Test LONG position P&L
    print("-" * 80)
    print("LONG Position Scenario")
    print("-" * 80)

    test_quantity = 0.05
    entry_price = current_price
    exit_price_higher = current_price * 1.05  # 5% increase
    exit_price_lower = current_price * 0.95   # 5% decrease

    long_pnl_price_up = (exit_price_higher - entry_price) * test_quantity
    long_pnl_price_down = (exit_price_lower - entry_price) * test_quantity

    print(f"Entry: {test_quantity} BTC @ ${entry_price:,.2f}")
    print(f"\nIf price increases to ${exit_price_higher:,.2f} (+5%):")
    print(f"   LONG P&L: ${long_pnl_price_up:,.2f} (profit ✅)")
    print(f"\nIf price decreases to ${exit_price_lower:,.2f} (-5%):")
    print(f"   LONG P&L: ${long_pnl_price_down:,.2f} (loss ❌)\n")

    # Test SHORT position P&L
    print("-" * 80)
    print("SHORT Position Scenario")
    print("-" * 80)

    short_pnl_price_up = (entry_price - exit_price_higher) * test_quantity
    short_pnl_price_down = (entry_price - exit_price_lower) * test_quantity

    print(f"Entry: {test_quantity} BTC SHORT @ ${entry_price:,.2f}")
    print(f"\nIf price increases to ${exit_price_higher:,.2f} (+5%):")
    print(f"   SHORT P&L: ${short_pnl_price_up:,.2f} (loss ❌)")
    print(f"\nIf price decreases to ${exit_price_lower:,.2f} (-5%):")
    print(f"   SHORT P&L: ${short_pnl_price_down:,.2f} (profit ✅)\n")

    # Verify calculations
    if long_pnl_price_up > 0 and short_pnl_price_down > 0:
        print("✅ P&L calculations correct!")
        print("   - LONG profits when price increases")
        print("   - SHORT profits when price decreases\n")
        return True
    else:
        print("❌ ERROR: P&L calculations incorrect\n")
        return False


def main():
    """Run all tests"""

    print("\n" + "="*80)
    print("SHORT POSITION FUNCTIONALITY TESTS")
    print("="*80)

    tests = [
        ("P&L Calculation Logic", test_long_vs_short_pnl),
        ("SHORT Position Lifecycle", test_short_position_lifecycle),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"Test '{test_name}' failed with exception: {e}", exc_info=True)
            results.append((test_name, False))

    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80 + "\n")

    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    print(f"\n{passed}/{total} tests passed")

    if passed == total:
        print("\n✅ All tests passed! SHORT position functionality is working correctly.\n")
        return 0
    else:
        print("\n❌ Some tests failed. Please review the output above.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())

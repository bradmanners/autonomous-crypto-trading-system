"""
Trading Orchestrator
Connects trading decisions to paper trading engine
Manages the trading execution loop
"""

import logging
import time
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from trading.paper_trading_engine import (
    PaperTradingEngine,
    OrderType,
    OrderSide,
    Order
)
from utils.database import DatabaseManager
from sqlalchemy import text


class TradingOrchestrator:
    """
    Orchestrates the trading system

    Features:
    - Monitors trading decisions
    - Executes trades via paper trading engine
    - Manages positions
    - Enforces risk limits
    - Logs performance
    """

    def __init__(
        self,
        paper_engine: Optional[PaperTradingEngine] = None,
        db: Optional[DatabaseManager] = None,
        execution_mode: str = 'paper',  # 'paper' or 'live'
        decision_confidence_threshold: float = 0.6,  # Only trade if confidence >= 60%
        check_interval: int = 60  # Check for new decisions every 60 seconds
    ):
        """
        Initialize Trading Orchestrator

        Args:
            paper_engine: Paper trading engine instance
            db: Database instance
            execution_mode: 'paper' or 'live'
            decision_confidence_threshold: Minimum confidence to execute
            check_interval: Seconds between decision checks
        """
        self.logger = logging.getLogger(__name__)
        self.paper_engine = paper_engine or PaperTradingEngine()
        self.db = db or DatabaseManager()

        self.execution_mode = execution_mode
        self.decision_confidence_threshold = decision_confidence_threshold
        self.check_interval = check_interval
        self.last_processed_decision_id = self._get_last_processed_decision()

        self.logger.info(
            f"Trading Orchestrator initialized in {execution_mode} mode "
            f"(confidence threshold: {decision_confidence_threshold:.0%})"
        )

    def _get_last_processed_decision(self) -> int:
        """Get the ID of the last processed trading decision"""
        with self.db.get_session() as session:
            result = session.execute(text("""
                SELECT COALESCE(MAX(decision_id), 0) as last_id
                FROM paper_orders
                WHERE decision_id IS NOT NULL
            """)).fetchone()

            return result.last_id if result else 0

    def get_pending_decisions(self, limit: int = 10) -> List[Dict]:
        """
        Get unprocessed trading decisions

        Args:
            limit: Maximum number of decisions to fetch

        Returns:
            List of decision dictionaries
        """
        with self.db.get_session() as session:
            results = session.execute(text("""
                SELECT
                    id,
                    timestamp,
                    symbol,
                    asset_class,
                    decision,
                    confidence,
                    current_price,
                    reasoning,
                    risk_score
                FROM trading_decisions
                WHERE id > :last_id
                    AND confidence >= :threshold
                    AND timestamp >= NOW() - INTERVAL '1 hour'
                ORDER BY timestamp DESC
                LIMIT :limit
            """), {
                'last_id': self.last_processed_decision_id,
                'threshold': self.decision_confidence_threshold,
                'limit': limit
            }).fetchall()

            decisions = []
            for row in results:
                decisions.append({
                    'id': row.id,
                    'timestamp': row.timestamp,
                    'symbol': row.symbol,
                    'asset_class': row.asset_class if row.asset_class else 'crypto',
                    'decision': row.decision,
                    'confidence': float(row.confidence),
                    'price': float(row.current_price) if row.current_price else None,
                    'reason': row.reasoning,
                    'risk_score': float(row.risk_score) if row.risk_score else 0.5
                })

            return decisions

    def calculate_position_size(
        self,
        symbol: str,
        decision: Dict,
        portfolio_value: float
    ) -> float:
        """
        Calculate appropriate position size for a trade

        Args:
            symbol: Trading symbol
            decision: Trading decision dict
            portfolio_value: Current portfolio value

        Returns:
            Quantity to trade
        """
        # Get asset's maximum position size (default 20% of portfolio)
        max_position_pct = 0.20

        # Adjust based on confidence
        confidence = decision['confidence']
        confidence_multiplier = min(confidence / 0.8, 1.0)  # Scale: 60% conf = 0.75x, 80%+ = 1.0x

        # Adjust based on risk score (lower risk = larger position)
        risk_score = decision.get('risk_score', 0.5)
        risk_multiplier = 1.0 - (risk_score * 0.5)  # Risk 0 = 1.0x, Risk 1 = 0.5x

        # Calculate target position value
        target_position_value = portfolio_value * max_position_pct * confidence_multiplier * risk_multiplier

        # Calculate quantity based on current price
        current_price = decision.get('price')
        if not current_price:
            current_price = self.paper_engine.get_current_price(symbol)

        if not current_price:
            self.logger.error(f"Cannot calculate position size - no price for {symbol}")
            return 0.0

        quantity = target_position_value / current_price

        self.logger.info(
            f"Position size for {symbol}: {quantity:.4f} "
            f"(conf: {confidence:.0%}, risk: {risk_score:.2f}, value: ${target_position_value:.2f})"
        )

        return quantity

    def execute_decision(self, decision: Dict) -> Optional[Order]:
        """
        Execute a trading decision

        Args:
            decision: Trading decision dictionary

        Returns:
            Executed Order or None
        """
        symbol = decision['symbol']
        asset_class = decision['asset_class']
        action = decision['decision']
        confidence = decision['confidence']

        self.logger.info(
            f"Executing {action} decision for {symbol} "
            f"(confidence: {confidence:.1%}, reason: {decision.get('reason', 'N/A')})"
        )

        # Update positions with current prices
        self.paper_engine.update_positions()

        # Get current portfolio value
        portfolio = self.paper_engine.get_portfolio_value()

        # Determine order side
        if action == 'BUY':
            side = OrderSide.BUY
            quantity = self.calculate_position_size(symbol, decision, portfolio.total_value)
        elif action == 'SELL':
            side = OrderSide.SELL
            # Get current position to determine how much to sell
            positions = self.paper_engine.get_open_positions()
            position = next((p for p in positions if p.symbol == symbol), None)

            if not position:
                self.logger.warning(f"SELL decision for {symbol} but no open position")
                return None

            quantity = position.quantity  # Sell entire position
        elif action == 'HOLD':
            self.logger.info(f"HOLD decision for {symbol} - no action taken")
            return None
        else:
            self.logger.warning(f"Unknown decision action: {action}")
            return None

        if quantity <= 0:
            self.logger.warning(f"Invalid quantity {quantity} for {symbol}")
            return None

        # Execute order
        try:
            order = self.paper_engine.execute_order(
                symbol=symbol,
                asset_class=asset_class,
                order_type=OrderType.MARKET,
                side=side,
                quantity=quantity,
                decision_id=decision['id']
            )

            if order:
                self.last_processed_decision_id = decision['id']
                self.logger.info(
                    f"✅ Executed {action}: {quantity:.4f} {symbol} @ ${order.avg_fill_price:,.2f} "
                    f"(decision_id: {decision['id']})"
                )
            else:
                self.logger.error(f"Failed to execute {action} for {symbol}")

            return order

        except Exception as e:
            self.logger.error(f"Error executing decision for {symbol}: {e}", exc_info=True)
            return None

    def run_trading_cycle(self):
        """
        Run one trading cycle:
        1. Check for new trading decisions
        2. Execute approved decisions
        3. Update positions
        4. Save portfolio snapshot
        """
        self.logger.info("Running trading cycle...")

        # Get pending decisions
        decisions = self.get_pending_decisions()

        if not decisions:
            self.logger.info("No new trading decisions to process")
            return

        self.logger.info(f"Found {len(decisions)} pending decisions")

        # Execute each decision
        executed_count = 0
        for decision in decisions:
            order = self.execute_decision(decision)
            if order:
                executed_count += 1
                time.sleep(1)  # Brief pause between orders

        # Update all positions with current prices
        self.paper_engine.update_positions()

        # Save portfolio snapshot
        self.paper_engine.save_portfolio_snapshot()

        # Get portfolio status
        portfolio = self.paper_engine.get_portfolio_value()
        positions = self.paper_engine.get_open_positions()

        self.logger.info(
            f"Trading cycle complete: {executed_count}/{len(decisions)} decisions executed, "
            f"Portfolio: ${portfolio.total_value:,.2f} ({portfolio.total_pnl_pct:+.2f}%), "
            f"Open positions: {len(positions)}"
        )

    def run_continuous(self):
        """
        Run continuous trading loop

        Checks for new decisions every check_interval seconds
        """
        self.logger.info(
            f"Starting continuous trading loop (checking every {self.check_interval}s)"
        )

        try:
            while True:
                try:
                    self.run_trading_cycle()
                except Exception as e:
                    self.logger.error(f"Error in trading cycle: {e}", exc_info=True)

                # Wait for next cycle
                time.sleep(self.check_interval)

        except KeyboardInterrupt:
            self.logger.info("Trading loop stopped by user")

    def get_performance_summary(self) -> Dict:
        """Get trading performance summary"""
        portfolio = self.paper_engine.get_portfolio_value()
        positions = self.paper_engine.get_open_positions()
        trades = self.paper_engine.get_recent_trades(limit=100)

        # Calculate win rate
        if trades:
            winning_trades = sum(1 for t in trades if t.realized_pnl > 0)
            win_rate = winning_trades / len(trades)
            avg_win = sum(t.realized_pnl for t in trades if t.realized_pnl > 0) / max(winning_trades, 1)
            avg_loss = sum(t.realized_pnl for t in trades if t.realized_pnl < 0) / max(len(trades) - winning_trades, 1)
        else:
            win_rate = 0.0
            avg_win = 0.0
            avg_loss = 0.0

        return {
            'portfolio_value': portfolio.total_value,
            'total_pnl': portfolio.total_pnl,
            'total_pnl_pct': portfolio.total_pnl_pct,
            'open_positions': len(positions),
            'total_trades': len(trades),
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': abs(avg_win / avg_loss) if avg_loss != 0 else 0,
            'positions': [
                {
                    'symbol': p.symbol,
                    'quantity': p.quantity,
                    'entry_price': p.entry_price,
                    'current_price': p.current_price,
                    'unrealized_pnl': p.unrealized_pnl,
                    'unrealized_pnl_pct': p.unrealized_pnl_pct
                }
                for p in positions
            ]
        }


if __name__ == "__main__":
    # Test the trading orchestrator
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("\n=== Trading Orchestrator Test ===\n")

    # Initialize orchestrator
    orchestrator = TradingOrchestrator(
        decision_confidence_threshold=0.5,  # Lower threshold for testing
        check_interval=10
    )

    # Get performance summary
    print("Current Performance:")
    summary = orchestrator.get_performance_summary()
    print(f"  Portfolio Value: ${summary['portfolio_value']:,.2f}")
    print(f"  Total PnL: ${summary['total_pnl']:,.2f} ({summary['total_pnl_pct']:+.2f}%)")
    print(f"  Open Positions: {summary['open_positions']}")
    print(f"  Total Trades: {summary['total_trades']}")

    if summary['total_trades'] > 0:
        print(f"  Win Rate: {summary['win_rate']:.1%}")
        print(f"  Avg Win: ${summary['avg_win']:,.2f}")
        print(f"  Avg Loss: ${summary['avg_loss']:,.2f}")
        print(f"  Profit Factor: {summary['profit_factor']:.2f}")

    # Check for pending decisions
    print("\n\nChecking for pending decisions...")
    decisions = orchestrator.get_pending_decisions()

    if decisions:
        print(f"Found {len(decisions)} pending decisions:")
        for decision in decisions:
            print(f"  - {decision['decision']} {decision['symbol']} "
                  f"(conf: {decision['confidence']:.1%}, reason: {decision.get('reason', 'N/A')})")

        # Run one trading cycle
        print("\n\nRunning trading cycle...")
        orchestrator.run_trading_cycle()

        # Show updated performance
        print("\n\nUpdated Performance:")
        summary = orchestrator.get_performance_summary()
        print(f"  Portfolio Value: ${summary['portfolio_value']:,.2f}")
        print(f"  Total PnL: ${summary['total_pnl']:,.2f} ({summary['total_pnl_pct']:+.2f}%)")
        print(f"  Open Positions: {summary['open_positions']}")

        if summary['positions']:
            print("\n  Open Positions:")
            for pos in summary['positions']:
                print(f"    {pos['symbol']}: {pos['quantity']:.4f} @ ${pos['entry_price']:,.2f} "
                      f"(PnL: ${pos['unrealized_pnl']:,.2f} / {pos['unrealized_pnl_pct']:+.2f}%)")
    else:
        print("No pending decisions to process")

    print("\n✅ Trading Orchestrator test complete!")
    print("\nTo run continuous trading loop, use:")
    print("  orchestrator.run_continuous()")

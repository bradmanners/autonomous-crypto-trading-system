"""
Paper Trading Engine
Simulates realistic order execution with slippage, fees, and position tracking
"""

import logging
import json
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import random

from utils.database import DatabaseManager
from sqlalchemy import text


class OrderType(Enum):
    """Order types"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"


class OrderSide(Enum):
    """Order sides"""
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(Enum):
    """Order status"""
    PENDING = "PENDING"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"


class PositionSide(Enum):
    """Position sides"""
    LONG = "LONG"
    SHORT = "SHORT"


@dataclass
class Order:
    """Represents a trading order"""
    symbol: str
    asset_class: str
    order_type: OrderType
    side: OrderSide
    quantity: float
    limit_price: Optional[float] = None

    # Execution details
    order_id: Optional[int] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0.0
    avg_fill_price: Optional[float] = None
    commission: float = 0.0
    slippage: float = 0.0
    total_cost: Optional[float] = None

    # Timestamps
    created_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None

    # References
    decision_id: Optional[int] = None
    metadata: Dict = None


@dataclass
class Position:
    """Represents an open trading position"""
    position_id: int
    symbol: str
    asset_class: str
    side: PositionSide
    quantity: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    position_value: float
    opened_at: datetime
    entry_order_id: int


@dataclass
class Trade:
    """Represents a closed trade"""
    trade_id: int
    symbol: str
    asset_class: str
    side: PositionSide
    quantity: float
    entry_price: float
    exit_price: float
    realized_pnl: float
    realized_pnl_pct: float
    gross_pnl: float
    net_pnl: float
    total_commission: float
    total_slippage: float
    entry_time: datetime
    exit_time: datetime
    hold_duration: timedelta
    strategy: Optional[str] = None


@dataclass
class PortfolioSnapshot:
    """Portfolio value snapshot"""
    total_value: float
    cash_balance: float
    positions_value: float
    total_pnl: float
    total_pnl_pct: float
    num_positions: int
    timestamp: datetime


class PaperTradingEngine:
    """
    Paper Trading Engine with realistic execution simulation

    Features:
    - Market and limit order execution
    - Realistic slippage based on volatility
    - Commission and fee calculations
    - Position tracking with PnL
    - Portfolio value snapshots
    - Risk management
    """

    def __init__(
        self,
        initial_capital: float = 10000.0,
        commission_pct: float = 0.001,  # 0.1%
        slippage_pct: float = 0.0005,  # 0.05%
        max_position_size: float = 0.20,  # 20% per position
        db: Optional[DatabaseManager] = None
    ):
        """
        Initialize Paper Trading Engine

        Args:
            initial_capital: Starting capital
            commission_pct: Commission percentage per trade
            slippage_pct: Base slippage percentage
            max_position_size: Maximum position size as fraction of portfolio
            db: DatabaseManager instance
        """
        self.logger = logging.getLogger(__name__)
        self.db = db or DatabaseManager()

        # Load or initialize configuration
        self.config = self._load_or_create_config(
            initial_capital=initial_capital,
            commission_pct=commission_pct,
            slippage_pct=slippage_pct,
            max_position_size=max_position_size
        )

        self.logger.info(f"Paper Trading Engine initialized with ${self.config['current_capital']:,.2f}")

    def _load_or_create_config(
        self,
        initial_capital: float,
        commission_pct: float,
        slippage_pct: float,
        max_position_size: float
    ) -> Dict:
        """Load existing config or create new one"""
        with self.db.get_session() as session:
            result = session.execute(
                text("SELECT * FROM paper_trading_config ORDER BY config_id DESC LIMIT 1")
            ).fetchone()

            if result:
                return {
                    'config_id': result.config_id,
                    'initial_capital': float(result.initial_capital),
                    'current_capital': float(result.current_capital),
                    'max_position_size': float(result.max_position_size),
                    'commission_pct': float(result.commission_pct),
                    'commission_min': float(result.commission_min),
                    'slippage_pct': float(result.slippage_pct),
                    'slippage_model': result.slippage_model
                }

            # Create new config
            session.execute(text("""
                INSERT INTO paper_trading_config (
                    initial_capital, current_capital, max_position_size,
                    commission_pct, slippage_pct
                ) VALUES (:initial, :current, :max_pos, :comm, :slip)
            """), {
                'initial': initial_capital,
                'current': initial_capital,
                'max_pos': max_position_size,
                'comm': commission_pct,
                'slip': slippage_pct
            })
            session.commit()

            return {
                'initial_capital': initial_capital,
                'current_capital': initial_capital,
                'max_position_size': max_position_size,
                'commission_pct': commission_pct,
                'commission_min': 1.0,
                'slippage_pct': slippage_pct,
                'slippage_model': 'PERCENTAGE'
            }

    def calculate_slippage(
        self,
        symbol: str,
        order_type: OrderType,
        side: OrderSide,
        quantity: float,
        current_price: float
    ) -> float:
        """
        Calculate realistic slippage for an order

        Slippage factors:
        - Order type (market = more slippage)
        - Order size (larger = more slippage)
        - Asset volatility (higher = more slippage)
        - Market conditions (simplified here)

        Args:
            symbol: Trading symbol
            order_type: MARKET or LIMIT
            side: BUY or SELL
            quantity: Order quantity
            current_price: Current market price

        Returns:
            Slippage amount in dollars
        """
        base_slippage_pct = self.config['slippage_pct']

        # Market orders have more slippage
        if order_type == OrderType.MARKET:
            slippage_multiplier = 2.0
        else:
            slippage_multiplier = 0.5  # Limit orders have less

        # Larger orders have more slippage (simplified)
        order_value = quantity * current_price
        if order_value > 10000:
            size_multiplier = 1.5
        elif order_value > 5000:
            size_multiplier = 1.2
        else:
            size_multiplier = 1.0

        # Add random variation (±50%)
        random_factor = random.uniform(0.5, 1.5)

        total_slippage_pct = base_slippage_pct * slippage_multiplier * size_multiplier * random_factor

        # Calculate slippage in dollars
        slippage_amount = order_value * total_slippage_pct

        # For buys, slippage increases cost; for sells, it decreases proceeds
        if side == OrderSide.BUY:
            return slippage_amount
        else:
            return slippage_amount

    def calculate_commission(self, order_value: float) -> float:
        """
        Calculate trading commission

        Args:
            order_value: Total order value

        Returns:
            Commission in dollars
        """
        commission = order_value * self.config['commission_pct']
        min_commission = self.config['commission_min']

        return max(commission, min_commission)

    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Get current market price for a symbol

        Args:
            symbol: Trading symbol

        Returns:
            Current price or None
        """
        with self.db.get_session() as session:
            result = session.execute(text("""
                SELECT close
                FROM price_data
                WHERE symbol = :symbol
                ORDER BY time DESC
                LIMIT 1
            """), {'symbol': symbol}).fetchone()

            if result:
                return float(result.close)

            self.logger.warning(f"No price data found for {symbol}")
            return None

    def execute_order(
        self,
        symbol: str,
        asset_class: str,
        order_type: OrderType,
        side: OrderSide,
        quantity: float,
        limit_price: Optional[float] = None,
        decision_id: Optional[int] = None
    ) -> Optional[Order]:
        """
        Execute a paper trading order

        Args:
            symbol: Trading symbol
            asset_class: Asset class (crypto, stocks, etc.)
            order_type: MARKET or LIMIT
            side: BUY or SELL
            quantity: Order quantity
            limit_price: Limit price for limit orders
            decision_id: Reference to trading decision

        Returns:
            Executed Order object or None if failed
        """
        self.logger.info(f"Executing {order_type.value} {side.value} order: {quantity} {symbol}")

        # Get current market price
        current_price = self.get_current_price(symbol)
        if not current_price:
            self.logger.error(f"Cannot execute order - no price data for {symbol}")
            return None

        # Determine execution price
        if order_type == OrderType.MARKET:
            execution_price = current_price
        else:
            # For limit orders, check if price is within limit
            if side == OrderSide.BUY and current_price <= limit_price:
                execution_price = limit_price
            elif side == OrderSide.SELL and current_price >= limit_price:
                execution_price = limit_price
            else:
                self.logger.info(f"Limit order not executable at current price")
                # Create pending order (would be filled later in real system)
                return self._create_pending_order(
                    symbol, asset_class, order_type, side, quantity, limit_price, decision_id
                )

        # Calculate costs
        order_value = quantity * execution_price
        slippage = self.calculate_slippage(symbol, order_type, side, quantity, current_price)
        commission = self.calculate_commission(order_value)

        # Calculate total cost including fees
        if side == OrderSide.BUY:
            total_cost = order_value + slippage + commission
            adjusted_price = execution_price + (slippage / quantity)
        else:
            total_cost = order_value - slippage - commission
            adjusted_price = execution_price - (slippage / quantity)

        # Check if we have enough capital
        current_capital = self._get_current_capital()

        # For both BUY and SELL orders, we need capital
        # BUY: need capital to purchase
        # SELL to open SHORT: need capital as margin/collateral (typically 100% of position value)
        # SELL to close LONG: don't need capital, selling existing position

        if side == OrderSide.BUY:
            # Check if this is closing a SHORT or opening a LONG
            existing_short = self._get_position(symbol, PositionSide.SHORT)
            if not existing_short and total_cost > current_capital:
                self.logger.error(f"Insufficient capital for BUY: need ${total_cost:.2f}, have ${current_capital:.2f}")
                return None
        else:  # SELL
            # Check if this is closing a LONG or opening a SHORT
            existing_long = self._get_position(symbol, PositionSide.LONG)
            if not existing_long:
                # Opening SHORT - need margin equal to position value
                if total_cost > current_capital:
                    self.logger.error(f"Insufficient capital for SHORT: need ${total_cost:.2f} margin, have ${current_capital:.2f}")
                    return None

        # Create order record
        with self.db.get_session() as session:
            result = session.execute(text("""
                INSERT INTO paper_orders (
                    symbol, asset_class, order_type, side, quantity, limit_price,
                    status, filled_quantity, avg_fill_price, commission, slippage,
                    total_cost, filled_at, decision_id
                ) VALUES (
                    :symbol, :asset_class, :order_type, :side, :quantity, :limit_price,
                    :status, :filled_qty, :avg_price, :commission, :slippage,
                    :total_cost, NOW(), :decision_id
                ) RETURNING order_id
            """), {
                'symbol': symbol,
                'asset_class': asset_class,
                'order_type': order_type.value,
                'side': side.value,
                'quantity': quantity,
                'limit_price': limit_price,
                'status': OrderStatus.FILLED.value,
                'filled_qty': quantity,
                'avg_price': adjusted_price,
                'commission': commission,
                'slippage': slippage,
                'total_cost': total_cost,
                'decision_id': decision_id
            })

            order_id = result.fetchone()[0]
            session.commit()

        # Update capital based on what we're doing
        # Need to check if we're opening or closing a position
        existing_short = self._get_position(symbol, PositionSide.SHORT)
        existing_long = self._get_position(symbol, PositionSide.LONG)

        if side == OrderSide.BUY:
            if existing_short:
                # Closing SHORT: release margin, pay for buyback
                # When we opened SHORT, we set aside margin
                # Now we buy back and return margin minus losses (or plus profits)
                self._update_capital(current_capital - total_cost)
            else:
                # Opening LONG: spend capital
                self._update_capital(current_capital - total_cost)
        else:  # SELL
            if existing_long:
                # Closing LONG: receive proceeds from sale
                self._update_capital(current_capital + total_cost)
            else:
                # Opening SHORT: set aside margin (lock capital)
                # The proceeds from SHORT sale are held as collateral
                self._update_capital(current_capital - order_value)

        # Update or create position
        if side == OrderSide.BUY:
            # Check if we're closing a SHORT position or opening a LONG position
            existing_short = self._get_position(symbol, PositionSide.SHORT)
            if existing_short:
                # Close SHORT position with BUY order
                self._close_or_reduce_position(
                    symbol=symbol,
                    quantity=quantity,
                    exit_price=adjusted_price,
                    exit_order_id=order_id,
                    position_side=PositionSide.SHORT
                )
            else:
                # Open LONG position
                self._open_or_add_position(
                    symbol=symbol,
                    asset_class=asset_class,
                    quantity=quantity,
                    entry_price=adjusted_price,
                    entry_order_id=order_id,
                    position_side=PositionSide.LONG
                )
        else:  # OrderSide.SELL
            # Check if we're closing a LONG position or opening a SHORT position
            existing_long = self._get_position(symbol, PositionSide.LONG)
            if existing_long:
                # Close LONG position with SELL order
                self._close_or_reduce_position(
                    symbol=symbol,
                    quantity=quantity,
                    exit_price=adjusted_price,
                    exit_order_id=order_id,
                    position_side=PositionSide.LONG
                )
            else:
                # Open SHORT position with SELL order
                self._open_or_add_position(
                    symbol=symbol,
                    asset_class=asset_class,
                    quantity=quantity,
                    entry_price=adjusted_price,
                    entry_order_id=order_id,
                    position_side=PositionSide.SHORT
                )

        self.logger.info(
            f"✅ Order filled: {quantity} {symbol} @ ${adjusted_price:.2f} "
            f"(commission: ${commission:.2f}, slippage: ${slippage:.2f})"
        )

        # Create Order object to return
        order = Order(
            symbol=symbol,
            asset_class=asset_class,
            order_type=order_type,
            side=side,
            quantity=quantity,
            limit_price=limit_price,
            order_id=order_id,
            status=OrderStatus.FILLED,
            filled_quantity=quantity,
            avg_fill_price=adjusted_price,
            commission=commission,
            slippage=slippage,
            total_cost=total_cost,
            filled_at=datetime.now(),
            decision_id=decision_id
        )

        return order

    def _create_pending_order(
        self,
        symbol: str,
        asset_class: str,
        order_type: OrderType,
        side: OrderSide,
        quantity: float,
        limit_price: float,
        decision_id: Optional[int]
    ) -> Order:
        """Create a pending limit order"""
        with self.db.get_session() as session:
            result = session.execute(text("""
                INSERT INTO paper_orders (
                    symbol, asset_class, order_type, side, quantity, limit_price,
                    status, decision_id
                ) VALUES (
                    :symbol, :asset_class, :order_type, :side, :quantity, :limit_price,
                    :status, :decision_id
                ) RETURNING order_id
            """), {
                'symbol': symbol,
                'asset_class': asset_class,
                'order_type': order_type.value,
                'side': side.value,
                'quantity': quantity,
                'limit_price': limit_price,
                'status': OrderStatus.PENDING.value,
                'decision_id': decision_id
            })

            order_id = result.fetchone()[0]
            session.commit()

        return Order(
            symbol=symbol,
            asset_class=asset_class,
            order_type=order_type,
            side=side,
            quantity=quantity,
            limit_price=limit_price,
            order_id=order_id,
            status=OrderStatus.PENDING,
            created_at=datetime.now(),
            decision_id=decision_id
        )

    def _get_position(self, symbol: str, side: PositionSide) -> Optional[Dict]:
        """
        Get existing position for a symbol and side

        Args:
            symbol: Trading symbol
            side: Position side (LONG or SHORT)

        Returns:
            Position dict or None
        """
        with self.db.get_session() as session:
            result = session.execute(text("""
                SELECT position_id, quantity, entry_price, position_value
                FROM paper_positions
                WHERE symbol = :symbol AND side = :side
            """), {'symbol': symbol, 'side': side.value}).fetchone()

            if result:
                return {
                    'position_id': result[0],
                    'quantity': float(result[1]),
                    'entry_price': float(result[2]),
                    'position_value': float(result[3])
                }
            return None

    def _get_current_capital(self) -> float:
        """Get current available capital"""
        with self.db.get_session() as session:
            result = session.execute(text("""
                SELECT current_capital
                FROM paper_trading_config
                ORDER BY config_id DESC
                LIMIT 1
            """)).fetchone()

            return float(result.current_capital) if result else 0.0

    def _update_capital(self, new_capital: float):
        """Update current capital"""
        with self.db.get_session() as session:
            session.execute(text("""
                UPDATE paper_trading_config
                SET current_capital = :capital,
                    updated_at = NOW()
                WHERE config_id = (SELECT config_id FROM paper_trading_config ORDER BY config_id DESC LIMIT 1)
            """), {'capital': new_capital})
            session.commit()

        self.config['current_capital'] = new_capital

    def _open_or_add_position(
        self,
        symbol: str,
        asset_class: str,
        quantity: float,
        entry_price: float,
        entry_order_id: int,
        position_side: PositionSide = PositionSide.LONG
    ):
        """Open a new position or add to existing one"""
        with self.db.get_session() as session:
            # Check if position exists
            existing = session.execute(text("""
                SELECT position_id, quantity, entry_price, position_value
                FROM paper_positions
                WHERE symbol = :symbol AND side = :side
            """), {'symbol': symbol, 'side': position_side.value}).fetchone()

            if existing:
                # Average up the position
                old_qty = float(existing.quantity)
                old_price = float(existing.entry_price)

                new_qty = old_qty + quantity
                new_avg_price = ((old_qty * old_price) + (quantity * entry_price)) / new_qty
                new_value = new_qty * entry_price

                session.execute(text("""
                    UPDATE paper_positions
                    SET quantity = :qty,
                        entry_price = :price,
                        position_value = :value,
                        current_price = :current,
                        last_updated = NOW()
                    WHERE position_id = :pos_id
                """), {
                    'qty': new_qty,
                    'price': new_avg_price,
                    'value': new_value,
                    'current': entry_price,
                    'pos_id': existing.position_id
                })

                self.logger.info(f"Added to existing position: {symbol} ({old_qty:.4f} -> {new_qty:.4f})")
            else:
                # Create new position
                position_value = quantity * entry_price

                session.execute(text("""
                    INSERT INTO paper_positions (
                        symbol, asset_class, side, quantity, entry_price,
                        current_price, position_value, entry_order_id
                    ) VALUES (
                        :symbol, :asset_class, :side, :qty, :entry,
                        :current, :value, :order_id
                    )
                """), {
                    'symbol': symbol,
                    'asset_class': asset_class,
                    'side': position_side.value,
                    'qty': quantity,
                    'entry': entry_price,
                    'current': entry_price,
                    'value': position_value,
                    'order_id': entry_order_id
                })

                self.logger.info(f"Opened new {position_side.value} position: {quantity:.4f} {symbol} @ ${entry_price:.2f}")

            session.commit()

    def _close_or_reduce_position(
        self,
        symbol: str,
        quantity: float,
        exit_price: float,
        exit_order_id: int,
        position_side: PositionSide = PositionSide.LONG
    ):
        """Close or reduce an existing position"""
        with self.db.get_session() as session:
            # Get existing position
            position = session.execute(text("""
                SELECT position_id, quantity, entry_price, position_value, opened_at, entry_order_id, asset_class
                FROM paper_positions
                WHERE symbol = :symbol AND side = :side
            """), {'symbol': symbol, 'side': position_side.value}).fetchone()

            if not position:
                self.logger.error(f"Cannot close position - no open {position_side.value} position for {symbol}")
                return

            pos_qty = float(position.quantity)
            entry_price = float(position.entry_price)

            if quantity >= pos_qty:
                # Close entire position
                # Calculate P&L based on position side
                if position_side == PositionSide.LONG:
                    # LONG: profit when price increases
                    realized_pnl = (exit_price - entry_price) * pos_qty
                else:  # SHORT
                    # SHORT: profit when price decreases
                    realized_pnl = (entry_price - exit_price) * pos_qty

                realized_pnl_pct = (realized_pnl / (entry_price * pos_qty)) * 100

                # Get order fees
                entry_order = session.execute(text("""
                    SELECT commission, slippage FROM paper_orders WHERE order_id = :id
                """), {'id': position.entry_order_id}).fetchone()

                exit_order = session.execute(text("""
                    SELECT commission, slippage FROM paper_orders WHERE order_id = :id
                """), {'id': exit_order_id}).fetchone()

                total_commission = float(entry_order.commission) + float(exit_order.commission)
                total_slippage = float(entry_order.slippage) + float(exit_order.slippage)

                gross_pnl = realized_pnl
                net_pnl = realized_pnl - total_commission - total_slippage

                # Create trade record
                session.execute(text("""
                    INSERT INTO paper_trades (
                        symbol, asset_class, side, quantity, entry_price, exit_price,
                        realized_pnl, realized_pnl_pct, gross_pnl, net_pnl,
                        total_commission, total_slippage, entry_time, exit_time,
                        hold_duration, entry_order_id, exit_order_id, position_id
                    ) VALUES (
                        :symbol, :asset_class, :side, :qty, :entry, :exit,
                        :pnl, :pnl_pct, :gross, :net,
                        :comm, :slip, :entry_time, NOW(),
                        NOW() - :entry_time, :entry_order, :exit_order, :pos_id
                    )
                """), {
                    'symbol': symbol,
                    'asset_class': position.asset_class if hasattr(position, 'asset_class') else 'crypto',
                    'side': position_side.value,
                    'qty': pos_qty,
                    'entry': entry_price,
                    'exit': exit_price,
                    'pnl': realized_pnl,
                    'pnl_pct': realized_pnl_pct,
                    'gross': gross_pnl,
                    'net': net_pnl,
                    'comm': total_commission,
                    'slip': total_slippage,
                    'entry_time': position.opened_at,
                    'entry_order': position.entry_order_id,
                    'exit_order': exit_order_id,
                    'pos_id': position.position_id
                })

                # Delete position
                session.execute(text("""
                    DELETE FROM paper_positions WHERE position_id = :id
                """), {'id': position.position_id})

                self.logger.info(
                    f"Closed {position_side.value} position: {pos_qty:.4f} {symbol} @ ${exit_price:.2f} "
                    f"(PnL: ${net_pnl:.2f} / {realized_pnl_pct:+.2f}%)"
                )
            else:
                # Reduce position
                new_qty = pos_qty - quantity
                new_value = new_qty * entry_price

                session.execute(text("""
                    UPDATE paper_positions
                    SET quantity = :qty,
                        position_value = :value,
                        current_price = :current,
                        last_updated = NOW()
                    WHERE position_id = :id
                """), {
                    'qty': new_qty,
                    'value': new_value,
                    'current': exit_price,
                    'id': position.position_id
                })

                self.logger.info(f"Reduced position: {symbol} ({pos_qty:.4f} -> {new_qty:.4f})")

            session.commit()

    def update_positions(self):
        """Update all open positions with current prices and PnL"""
        with self.db.get_session() as session:
            positions = session.execute(text("""
                SELECT position_id, symbol, quantity, entry_price, side
                FROM paper_positions
            """)).fetchall()

            for pos in positions:
                current_price = self.get_current_price(pos.symbol)
                if not current_price:
                    continue

                # Calculate unrealized PnL
                if pos.side == 'LONG':
                    unrealized_pnl = (current_price - float(pos.entry_price)) * float(pos.quantity)
                else:  # SHORT
                    unrealized_pnl = (float(pos.entry_price) - current_price) * float(pos.quantity)

                unrealized_pnl_pct = (unrealized_pnl / (float(pos.entry_price) * float(pos.quantity))) * 100
                position_value = float(pos.quantity) * current_price

                # Update position
                session.execute(text("""
                    UPDATE paper_positions
                    SET current_price = :price,
                        unrealized_pnl = :pnl,
                        unrealized_pnl_pct = :pnl_pct,
                        position_value = :value,
                        last_updated = NOW()
                    WHERE position_id = :id
                """), {
                    'price': current_price,
                    'pnl': unrealized_pnl,
                    'pnl_pct': unrealized_pnl_pct,
                    'value': position_value,
                    'id': pos.position_id
                })

            session.commit()

            if positions:
                self.logger.info(f"Updated {len(positions)} positions with current prices")

    def get_portfolio_value(self) -> PortfolioSnapshot:
        """Get current portfolio value and metrics"""
        with self.db.get_session() as session:
            result = session.execute(text("""
                SELECT * FROM get_portfolio_value()
            """)).fetchone()

            if not result:
                return PortfolioSnapshot(
                    total_value=self.config['initial_capital'],
                    cash_balance=self.config['initial_capital'],
                    positions_value=0.0,
                    total_pnl=0.0,
                    total_pnl_pct=0.0,
                    num_positions=0,
                    timestamp=datetime.now()
                )

            total_value = float(result.total_value)
            cash_balance = float(result.cash_balance)
            positions_value = float(result.positions_value)

            total_pnl = total_value - self.config['initial_capital']
            total_pnl_pct = (total_pnl / self.config['initial_capital']) * 100

            # Get number of positions
            num_positions = session.execute(text("""
                SELECT COUNT(*) FROM paper_positions
            """)).fetchone()[0]

            return PortfolioSnapshot(
                total_value=total_value,
                cash_balance=cash_balance,
                positions_value=positions_value,
                total_pnl=total_pnl,
                total_pnl_pct=total_pnl_pct,
                num_positions=num_positions,
                timestamp=datetime.now()
            )

    def get_open_positions(self) -> List[Position]:
        """Get all open positions"""
        with self.db.get_session() as session:
            results = session.execute(text("""
                SELECT * FROM v_paper_open_positions
            """)).fetchall()

            positions = []
            for row in results:
                positions.append(Position(
                    position_id=row.position_id,
                    symbol=row.symbol,
                    asset_class=row.asset_class,
                    side=PositionSide(row.side),
                    quantity=float(row.quantity),
                    entry_price=float(row.entry_price),
                    current_price=float(row.current_price),
                    unrealized_pnl=float(row.unrealized_pnl),
                    unrealized_pnl_pct=float(row.unrealized_pnl_pct),
                    position_value=float(row.position_value),
                    opened_at=row.opened_at,
                    entry_order_id=row.entry_order_id if hasattr(row, 'entry_order_id') else 0
                ))

            return positions

    def get_recent_trades(self, limit: int = 10) -> List[Trade]:
        """Get recent closed trades"""
        with self.db.get_session() as session:
            results = session.execute(text("""
                SELECT * FROM v_paper_recent_trades LIMIT :limit
            """), {'limit': limit}).fetchall()

            trades = []
            for row in results:
                trades.append(Trade(
                    trade_id=row.trade_id,
                    symbol=row.symbol,
                    asset_class=row.asset_class,
                    side=PositionSide(row.side),
                    quantity=float(row.quantity),
                    entry_price=float(row.entry_price),
                    exit_price=float(row.exit_price),
                    realized_pnl=float(row.realized_pnl),
                    realized_pnl_pct=float(row.realized_pnl_pct),
                    gross_pnl=float(row.gross_pnl) if hasattr(row, 'gross_pnl') else float(row.realized_pnl),
                    net_pnl=float(row.net_pnl),
                    total_commission=float(row.total_fees) if hasattr(row, 'total_fees') else 0.0,
                    total_slippage=0.0,
                    entry_time=row.entry_time,
                    exit_time=row.exit_time,
                    hold_duration=row.hold_duration,
                    strategy=row.strategy if hasattr(row, 'strategy') else None
                ))

            return trades

    def save_portfolio_snapshot(self):
        """Save current portfolio snapshot for historical tracking"""
        snapshot = self.get_portfolio_value()

        with self.db.get_session() as session:
            # Get position breakdown
            positions = session.execute(text("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN side = 'LONG' THEN 1 ELSE 0 END) as longs,
                    SUM(CASE WHEN side = 'SHORT' THEN 1 ELSE 0 END) as shorts
                FROM paper_positions
            """)).fetchone()

            # Get asset class allocation
            allocation = session.execute(text("""
                SELECT asset_class, SUM(position_value) as value
                FROM paper_positions
                GROUP BY asset_class
            """)).fetchall()

            allocation_dict = {row.asset_class: float(row.value) for row in allocation}

            # Calculate daily PnL
            yesterday_snapshot = session.execute(text("""
                SELECT total_value
                FROM paper_portfolio_snapshots
                WHERE time >= NOW() - INTERVAL '25 hours'
                ORDER BY time ASC
                LIMIT 1
            """)).fetchone()

            if yesterday_snapshot:
                daily_pnl = snapshot.total_value - float(yesterday_snapshot.total_value)
                daily_pnl_pct = (daily_pnl / float(yesterday_snapshot.total_value)) * 100
            else:
                daily_pnl = 0.0
                daily_pnl_pct = 0.0

            # Insert snapshot
            session.execute(text("""
                INSERT INTO paper_portfolio_snapshots (
                    total_value, cash_balance, positions_value,
                    total_pnl, total_pnl_pct, daily_pnl, daily_pnl_pct,
                    num_positions, long_positions, short_positions,
                    allocation
                ) VALUES (
                    :total, :cash, :positions,
                    :total_pnl, :total_pnl_pct, :daily_pnl, :daily_pnl_pct,
                    :num_pos, :longs, :shorts,
                    CAST(:allocation AS jsonb)
                )
            """), {
                'total': snapshot.total_value,
                'cash': snapshot.cash_balance,
                'positions': snapshot.positions_value,
                'total_pnl': snapshot.total_pnl,
                'total_pnl_pct': snapshot.total_pnl_pct,
                'daily_pnl': daily_pnl,
                'daily_pnl_pct': daily_pnl_pct,
                'num_pos': positions.total if positions else 0,
                'longs': positions.longs if positions else 0,
                'shorts': positions.shorts if positions else 0,
                'allocation': json.dumps(allocation_dict)
            })

            session.commit()

        self.logger.info(f"Portfolio snapshot saved: ${snapshot.total_value:,.2f}")


if __name__ == "__main__":
    # Test the paper trading engine
    logging.basicConfig(level=logging.INFO)

    print("\n=== Paper Trading Engine Test ===\n")

    # Initialize engine
    engine = PaperTradingEngine(initial_capital=10000.0)

    # Get portfolio value
    portfolio = engine.get_portfolio_value()
    print(f"Portfolio Value: ${portfolio.total_value:,.2f}")
    print(f"Cash Balance: ${portfolio.cash_balance:,.2f}")
    print(f"Positions Value: ${portfolio.positions_value:,.2f}")
    print(f"Total PnL: ${portfolio.total_pnl:,.2f} ({portfolio.total_pnl_pct:+.2f}%)")
    print(f"Open Positions: {portfolio.num_positions}")

    # Test market buy order
    print("\n\nExecuting test BUY order...")
    order = engine.execute_order(
        symbol='BTC/USDT',
        asset_class='crypto',
        order_type=OrderType.MARKET,
        side=OrderSide.BUY,
        quantity=0.01  # Small amount for testing
    )

    if order:
        print(f"✅ Order executed: {order.filled_quantity} BTC @ ${order.avg_fill_price:,.2f}")
        print(f"   Commission: ${order.commission:.2f}")
        print(f"   Slippage: ${order.slippage:.2f}")
        print(f"   Total Cost: ${order.total_cost:,.2f}")

    # Update positions
    print("\n\nUpdating positions...")
    engine.update_positions()

    # Get open positions
    positions = engine.get_open_positions()
    if positions:
        print("\nOpen Positions:")
        for pos in positions:
            print(f"  {pos.symbol}: {pos.quantity:.4f} @ ${pos.entry_price:,.2f}")
            print(f"    Current: ${pos.current_price:,.2f}")
            print(f"    Unrealized PnL: ${pos.unrealized_pnl:,.2f} ({pos.unrealized_pnl_pct:+.2f}%)")

    # Save snapshot
    print("\n\nSaving portfolio snapshot...")
    engine.save_portfolio_snapshot()

    print("\n✅ Paper Trading Engine test complete!")

"""
Price Forecaster Agent

Generates price forecasts using statistical methods (linear regression) and stores them
for visualization in Grafana dashboards.

Forecast Types:
- Base: Linear trend continuation (most likely scenario)
- Optimistic: +10% from base (bullish scenario)
- Pessimistic: -10% from base (bearish scenario)
"""

import json
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List
from sqlalchemy import text

from agents.base_agent import BaseAgent, AgentType
from config.config import config


class PriceForecasterAgent(BaseAgent):
    """
    Price forecasting agent using linear regression

    Responsibilities:
    - Fetch last 30 days of price data
    - Calculate linear trend using least squares regression
    - Generate 7-day forward forecasts (base, optimistic, pessimistic)
    - Store forecasts in database for Grafana visualization
    """

    def __init__(self):
        super().__init__(
            agent_name="PriceForecaster",
            agent_type=AgentType.ANALYST,
            version="1.0.0"
        )
        self.lookback_days = 30  # Use 30 days of historical data
        self.forecast_days = 7   # Forecast 7 days ahead
        self.model_version = "linear_v1.0"

    def run(self) -> Dict[str, Any]:
        """
        Main execution method (required by BaseAgent)
        """
        return self.execute()

    def execute(self) -> Dict[str, Any]:
        """
        Generate price forecasts for all trading pairs

        Returns:
            Dict with forecast results
        """
        results = {
            'success': True,
            'symbols_forecasted': 0,
            'total_forecasts': 0,
            'errors': []
        }

        for symbol in config.trading_pairs:
            try:
                self.logger.info(f"Generating forecasts for {symbol}...")

                # Get historical price data
                price_data = self._get_price_history(symbol, days=self.lookback_days)

                if not price_data or len(price_data) < 7:
                    self.logger.warning(f"Insufficient data for {symbol} (need 7+ days)")
                    continue

                # Generate forecasts
                forecasts = self._generate_forecasts(symbol, price_data)

                # Store forecasts in database
                self._store_forecasts(symbol, forecasts)

                results['symbols_forecasted'] += 1
                results['total_forecasts'] += len(forecasts)

                self.logger.info(
                    f"Generated {len(forecasts)} forecasts for {symbol} "
                    f"(next {self.forecast_days} days)"
                )

            except Exception as e:
                error_msg = f"Error forecasting {symbol}: {e}"
                self.logger.error(error_msg, exc_info=True)
                results['errors'].append(error_msg)
                results['success'] = False

        return results

    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze and return forecast insights

        Args:
            data: Optional parameters (symbol, days, etc.)

        Returns:
            Dict with forecast analysis
        """
        symbol = data.get('symbol', config.trading_pairs[0])

        # Get latest forecasts
        with self.db.get_session() as session:
            query = text("""
                SELECT
                    forecast_time,
                    forecast_type,
                    predicted_price,
                    confidence
                FROM price_forecasts
                WHERE symbol = :symbol
                    AND generated_at = (
                        SELECT MAX(generated_at)
                        FROM price_forecasts
                        WHERE symbol = :symbol
                    )
                ORDER BY forecast_time ASC
            """)

            results = session.execute(query, {'symbol': symbol}).fetchall()

            forecasts = [
                {
                    'time': row[0].isoformat(),
                    'type': row[1],
                    'price': float(row[2]),
                    'confidence': float(row[3])
                }
                for row in results
            ]

        return {
            'symbol': symbol,
            'forecasts': forecasts,
            'forecast_days': self.forecast_days,
            'model_version': self.model_version
        }

    def _get_price_history(self, symbol: str, days: int) -> List[Dict[str, Any]]:
        """
        Get historical price data for trend analysis

        Args:
            symbol: Trading pair symbol
            days: Number of days to look back

        Returns:
            List of price data points
        """
        with self.db.get_session() as session:
            query = text("""
                SELECT
                    time,
                    close
                FROM price_data
                WHERE symbol = :symbol
                    AND time >= NOW() - INTERVAL '1 day' * :days
                ORDER BY time ASC
            """)

            results = session.execute(query, {
                'symbol': symbol,
                'days': days
            }).fetchall()

            return [
                {
                    'time': row[0],
                    'price': float(row[1])
                }
                for row in results
            ]

    def _generate_forecasts(
        self,
        symbol: str,
        price_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate price forecasts using linear regression

        Args:
            symbol: Trading pair symbol
            price_data: Historical price data

        Returns:
            List of forecast data points
        """
        # Extract prices and create time indices
        prices = np.array([d['price'] for d in price_data])
        n = len(prices)
        x = np.arange(n)  # Time indices: 0, 1, 2, ...

        # Calculate linear regression (least squares)
        # y = mx + b
        x_mean = np.mean(x)
        y_mean = np.mean(prices)

        # Slope (m)
        numerator = np.sum((x - x_mean) * (prices - y_mean))
        denominator = np.sum((x - x_mean) ** 2)
        slope = numerator / denominator

        # Intercept (b)
        intercept = y_mean - slope * x_mean

        # Calculate R-squared for confidence
        y_pred = slope * x + intercept
        ss_res = np.sum((prices - y_pred) ** 2)
        ss_tot = np.sum((prices - y_mean) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

        # Use R-squared as confidence metric (0-1)
        confidence = max(0.0, min(1.0, r_squared))

        # Get last timestamp and price
        last_time = price_data[-1]['time']
        last_price = price_data[-1]['price']

        # Generate forecasts for next N days
        forecasts = []

        for day in range(1, self.forecast_days + 1):
            forecast_time = last_time + timedelta(days=day)

            # Base forecast: linear trend continuation
            base_price = slope * (n + day - 1) + intercept

            # Optimistic scenario: +10% from base
            optimistic_price = base_price * 1.10

            # Pessimistic scenario: -10% from base
            pessimistic_price = base_price * 0.90

            # Add all three scenarios
            for forecast_type, predicted_price in [
                ('base', base_price),
                ('optimistic', optimistic_price),
                ('pessimistic', pessimistic_price)
            ]:
                forecasts.append({
                    'forecast_time': forecast_time,
                    'forecast_type': forecast_type,
                    'predicted_price': predicted_price,
                    'confidence': confidence,
                    'model_params': {
                        'method': 'linear_regression',
                        'slope': float(slope),
                        'intercept': float(intercept),
                        'r_squared': float(r_squared),
                        'lookback_days': self.lookback_days,
                        'last_price': float(last_price)
                    }
                })

        self.logger.info(
            f"Trend: slope={slope:.2f}, R²={r_squared:.3f}, "
            f"last=${last_price:.2f}, "
            f"forecast_7d_base=${forecasts[-3]['predicted_price']:.2f}"
        )

        return forecasts

    def _store_forecasts(self, symbol: str, forecasts: List[Dict[str, Any]]):
        """
        Store forecasts in database

        Args:
            symbol: Trading pair symbol
            forecasts: List of forecast data points
        """
        with self.db.get_session() as session:
            generated_at = datetime.now(timezone.utc)

            for forecast in forecasts:
                session.execute(text("""
                    INSERT INTO price_forecasts (
                        symbol,
                        forecast_time,
                        forecast_type,
                        predicted_price,
                        confidence,
                        generated_at,
                        model_version,
                        model_params
                    ) VALUES (
                        :symbol,
                        :forecast_time,
                        :forecast_type,
                        :predicted_price,
                        :confidence,
                        :generated_at,
                        :model_version,
                        CAST(:model_params AS jsonb)
                    )
                    ON CONFLICT (symbol, forecast_time, forecast_type, generated_at)
                    DO UPDATE SET
                        predicted_price = EXCLUDED.predicted_price,
                        confidence = EXCLUDED.confidence
                """), {
                    'symbol': symbol,
                    'forecast_time': forecast['forecast_time'],
                    'forecast_type': forecast['forecast_type'],
                    'predicted_price': float(forecast['predicted_price']),  # Convert numpy to python float
                    'confidence': float(forecast['confidence']),  # Convert numpy to python float
                    'generated_at': generated_at,
                    'model_version': self.model_version,
                    'model_params': json.dumps(forecast['model_params'])  # Convert dict to JSON string
                })

            session.commit()


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)

    print("\n" + "="*80)
    print("Price Forecaster Agent - Test Run")
    print("="*80 + "\n")

    agent = PriceForecasterAgent()

    # Generate forecasts
    result = agent.execute()

    print("\nResults:")
    print(f"  Success: {result['success']}")
    print(f"  Symbols forecasted: {result['symbols_forecasted']}")
    print(f"  Total forecasts: {result['total_forecasts']}")

    if result['errors']:
        print(f"  Errors: {len(result['errors'])}")
        for error in result['errors']:
            print(f"    - {error}")

    # Show analysis for first symbol
    if result['symbols_forecasted'] > 0:
        print("\n" + "-"*80)
        analysis = agent.analyze({'symbol': config.trading_pairs[0]})
        print(f"\nForecast Analysis for {analysis['symbol']}:")
        print(f"  Model: {analysis['model_version']}")
        print(f"  Forecast period: Next {analysis['forecast_days']} days")

        if analysis['forecasts']:
            print(f"\n  Sample forecasts (first 3):")
            for fc in analysis['forecasts'][:3]:
                print(f"    {fc['time'][:10]}: ${fc['price']:,.2f} ({fc['type']})")

    print("\n✅ Test complete!\n")

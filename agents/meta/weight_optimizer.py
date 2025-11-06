"""
Weight Optimizer Agent

Dynamically adjusts agent weights based on performance to optimize
the ensemble's overall profitability and risk-adjusted returns.

Uses performance data from PerformanceAnalyzerAgent to:
- Calculate optimal agent weights
- Adapt to changing market conditions
- Reduce exposure to underperforming agents
- Maximize Sharpe ratio of the ensemble
"""
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
import json
from sqlalchemy import text
from scipy.optimize import minimize

from agents.base_agent import BaseAgent, AgentType
from config.config import config


class WeightOptimizerAgent(BaseAgent):
    """
    Weight Optimizer Agent

    Optimizes agent weights using:
    - Mean-variance optimization (Markowitz)
    - Sharpe ratio maximization
    - Risk parity approaches
    - Kelly criterion for sizing
    - Minimum performance thresholds
    """

    def __init__(self):
        super().__init__(
            agent_name="WeightOptimizer",
            agent_type=AgentType.META,
            version="1.0.0"
        )

        # Optimization parameters
        self.lookback_days = 30
        self.min_sharpe = 0.3  # Minimum Sharpe to receive weight
        self.min_signals = 10  # Minimum signals for consideration
        self.update_frequency_hours = 24  # Update weights daily
        self.max_weight = 0.4  # Maximum weight for any single agent
        self.min_weight = 0.05  # Minimum weight (if included)

        # Optimization method
        self.method = 'sharpe_ratio'  # 'sharpe_ratio', 'risk_parity', 'equal_weight'

    def run(self) -> Dict[str, Any]:
        """
        Main execution method

        Returns:
            Dict with optimization results
        """
        self.logger.info("Starting Weight Optimizer cycle")

        # Check if it's time to update weights
        if not self._should_update_weights():
            self.logger.info("Skipping weight update - too soon since last update")
            return {
                'weights_updated': False,
                'reason': 'update_frequency_not_met'
            }

        # Get agent performance data
        agent_data = self._get_agent_performance_data()

        if len(agent_data) < 2:
            self.logger.warning(f"Insufficient agents for optimization: {len(agent_data)}")
            return {
                'weights_updated': False,
                'reason': 'insufficient_agents',
                'agent_count': len(agent_data)
            }

        # Calculate optimal weights
        old_weights = self._get_current_weights()
        new_weights = self._optimize_weights(agent_data)

        # Calculate expected improvement
        improvement = self._calculate_expected_improvement(agent_data, old_weights, new_weights)

        # Save new weights
        self._save_weights(new_weights, improvement, agent_data)

        # Log work
        self._log_work('completed', f"Optimized weights for {len(new_weights)} agents", {
            'improvement': improvement,
            'method': self.method
        })

        result = {
            'weights_updated': True,
            'old_weights': old_weights,
            'new_weights': new_weights,
            'improvement': improvement,
            'agents_optimized': len(new_weights),
            'method': self.method,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

        self.logger.info(
            f"Weight optimization completed: "
            f"{len(new_weights)} agents, "
            f"expected improvement: {improvement.get('sharpe_improvement', 0):.2f}"
        )

        return result

    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze weight optimization for given data

        Args:
            data: Agent performance data

        Returns:
            Dict with analysis results
        """
        agent_data = data.get('agent_data', [])

        if not agent_data:
            agent_data = self._get_agent_performance_data()

        weights = self._optimize_weights(agent_data)

        return {
            'optimized_weights': weights,
            'method': self.method,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

    def _should_update_weights(self) -> bool:
        """Determine if it's time to update weights"""
        try:
            with self.db.get_session() as session:
                query = text("""
                    SELECT MAX(timestamp)
                    FROM weight_history
                """)

                result = session.execute(query).fetchone()

                if not result[0]:
                    return True  # No previous weights

                last_update = result[0]
                time_since = datetime.now(timezone.utc) - last_update

                return time_since.total_seconds() >= (self.update_frequency_hours * 3600)

        except Exception as e:
            self.logger.error(f"Error checking update frequency: {e}")
            return True  # Update on error

    def _get_current_weights(self) -> Dict[str, float]:
        """Get current agent weights"""
        try:
            with self.db.get_session() as session:
                query = text("""
                    SELECT agent_weights
                    FROM weight_history
                    ORDER BY timestamp DESC
                    LIMIT 1
                """)

                result = session.execute(query).fetchone()

                if result:
                    return result[0]  # JSONB field
                return {}

        except Exception as e:
            self.logger.error(f"Error getting current weights: {e}")
            return {}

    def _get_agent_performance_data(self) -> List[Dict[str, Any]]:
        """
        Get agent performance data for optimization

        Returns:
            List of agent performance dicts
        """
        try:
            with self.db.get_session() as session:
                cutoff = datetime.now(timezone.utc).date() - timedelta(days=self.lookback_days)

                query = text("""
                    SELECT
                        agent_name,
                        AVG(sharpe_ratio) as avg_sharpe,
                        AVG(win_rate) as avg_win_rate,
                        SUM(total_signals) as total_signals,
                        SUM(total_return) as total_return,
                        AVG(max_drawdown) as avg_max_drawdown,
                        STDDEV(total_return) as return_volatility,
                        AVG(profit_factor) as avg_profit_factor
                    FROM agent_performance
                    WHERE date >= :cutoff
                    GROUP BY agent_name
                    HAVING SUM(total_signals) >= :min_signals
                        AND AVG(sharpe_ratio) >= :min_sharpe
                    ORDER BY avg_sharpe DESC
                """)

                results = session.execute(query, {
                    'cutoff': cutoff,
                    'min_signals': self.min_signals,
                    'min_sharpe': self.min_sharpe
                }).fetchall()

                agents = []
                for row in results:
                    agents.append({
                        'agent_name': row[0],
                        'sharpe_ratio': float(row[1]) if row[1] else 0,
                        'win_rate': float(row[2]) if row[2] else 0,
                        'total_signals': row[3] or 0,
                        'total_return': float(row[4]) if row[4] else 0,
                        'max_drawdown': float(row[5]) if row[5] else 0,
                        'volatility': float(row[6]) if row[6] else 0.01,
                        'profit_factor': float(row[7]) if row[7] else 0
                    })

                return agents

        except Exception as e:
            self.logger.error(f"Error getting agent performance data: {e}")
            return []

    def _optimize_weights(self, agent_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Optimize agent weights based on performance

        Args:
            agent_data: List of agent performance dicts

        Returns:
            Dict of {agent_name: weight}
        """
        if self.method == 'sharpe_ratio':
            return self._optimize_sharpe_ratio(agent_data)
        elif self.method == 'risk_parity':
            return self._optimize_risk_parity(agent_data)
        elif self.method == 'equal_weight':
            return self._optimize_equal_weight(agent_data)
        else:
            self.logger.warning(f"Unknown method {self.method}, using Sharpe ratio")
            return self._optimize_sharpe_ratio(agent_data)

    def _optimize_sharpe_ratio(self, agent_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Optimize weights to maximize Sharpe ratio

        Args:
            agent_data: List of agent performance dicts

        Returns:
            Dict of {agent_name: weight}
        """
        n = len(agent_data)

        # Extract returns and volatility
        returns = np.array([a['total_return'] / max(a['total_signals'], 1) for a in agent_data])
        volatility = np.array([max(a['volatility'], 0.01) for a in agent_data])

        # Simple correlation matrix (assume 0.5 correlation for now)
        # In production, calculate actual correlation from signal outcomes
        corr = np.full((n, n), 0.5)
        np.fill_diagonal(corr, 1.0)

        # Covariance matrix
        cov_matrix = np.outer(volatility, volatility) * corr

        def negative_sharpe(weights):
            """Negative Sharpe ratio (for minimization)"""
            portfolio_return = np.dot(weights, returns)
            portfolio_vol = np.sqrt(np.dot(weights, np.dot(cov_matrix, weights)))

            if portfolio_vol == 0:
                return 0

            sharpe = portfolio_return / portfolio_vol
            return -sharpe  # Minimize negative Sharpe

        # Constraints: weights sum to 1
        constraints = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}
        ]

        # Bounds: min_weight <= w <= max_weight
        bounds = [(self.min_weight, self.max_weight) for _ in range(n)]

        # Initial guess: equal weights
        w0 = np.array([1.0 / n] * n)

        # Optimize
        result = minimize(
            negative_sharpe,
            w0,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )

        if not result.success:
            self.logger.warning(f"Optimization did not converge: {result.message}")
            # Fall back to weighted by Sharpe
            return self._weight_by_sharpe(agent_data)

        # Create weight dict
        weights = {}
        for i, agent in enumerate(agent_data):
            weights[agent['agent_name']] = float(result.x[i])

        # Normalize to ensure they sum to 1
        total = sum(weights.values())
        weights = {k: v/total for k, v in weights.items()}

        return weights

    def _optimize_risk_parity(self, agent_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Optimize weights using risk parity

        Each agent contributes equally to portfolio risk

        Args:
            agent_data: List of agent performance dicts

        Returns:
            Dict of {agent_name: weight}
        """
        # Inverse volatility weighting (simple risk parity)
        inv_vols = np.array([1.0 / max(a['volatility'], 0.01) for a in agent_data])

        # Normalize
        weights_array = inv_vols / inv_vols.sum()

        weights = {}
        for i, agent in enumerate(agent_data):
            weights[agent['agent_name']] = float(weights_array[i])

        return weights

    def _optimize_equal_weight(self, agent_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Equal weight allocation

        Args:
            agent_data: List of agent performance dicts

        Returns:
            Dict of {agent_name: weight}
        """
        n = len(agent_data)
        weight = 1.0 / n

        weights = {}
        for agent in agent_data:
            weights[agent['agent_name']] = weight

        return weights

    def _weight_by_sharpe(self, agent_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Weight proportional to Sharpe ratio (fallback method)

        Args:
            agent_data: List of agent performance dicts

        Returns:
            Dict of {agent_name: weight}
        """
        sharpe_ratios = np.array([max(a['sharpe_ratio'], 0) for a in agent_data])

        if sharpe_ratios.sum() == 0:
            return self._optimize_equal_weight(agent_data)

        weights_array = sharpe_ratios / sharpe_ratios.sum()

        weights = {}
        for i, agent in enumerate(agent_data):
            weights[agent['agent_name']] = float(weights_array[i])

        return weights

    def _calculate_expected_improvement(
        self,
        agent_data: List[Dict[str, Any]],
        old_weights: Dict[str, float],
        new_weights: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Calculate expected improvement from weight change

        Args:
            agent_data: List of agent performance dicts
            old_weights: Old weight allocation
            new_weights: New weight allocation

        Returns:
            Dict with improvement metrics
        """
        # Create performance dict for lookup
        perf = {a['agent_name']: a for a in agent_data}

        # Calculate weighted metrics
        def calc_weighted_metrics(weights):
            if not weights:
                return {'sharpe': 0, 'return': 0, 'win_rate': 0}

            weighted_sharpe = sum(
                weights.get(name, 0) * perf[name]['sharpe_ratio']
                for name in perf.keys()
                if name in weights
            )

            weighted_return = sum(
                weights.get(name, 0) * perf[name]['total_return']
                for name in perf.keys()
                if name in weights
            )

            weighted_win_rate = sum(
                weights.get(name, 0) * perf[name]['win_rate']
                for name in perf.keys()
                if name in weights
            )

            return {
                'sharpe': weighted_sharpe,
                'return': weighted_return,
                'win_rate': weighted_win_rate
            }

        old_metrics = calc_weighted_metrics(old_weights)
        new_metrics = calc_weighted_metrics(new_weights)

        return {
            'sharpe_improvement': new_metrics['sharpe'] - old_metrics['sharpe'],
            'return_improvement': new_metrics['return'] - old_metrics['return'],
            'win_rate_improvement': new_metrics['win_rate'] - old_metrics['win_rate'],
            'old_sharpe': old_metrics['sharpe'],
            'new_sharpe': new_metrics['sharpe']
        }

    def _save_weights(
        self,
        weights: Dict[str, float],
        improvement: Dict[str, Any],
        agent_data: List[Dict[str, Any]]
    ):
        """
        Save optimized weights to database

        Args:
            weights: New weight allocation
            improvement: Expected improvement metrics
            agent_data: Agent performance data used
        """
        try:
            with self.db.get_session() as session:
                # Create performance window summary
                perf_window = {
                    'lookback_days': self.lookback_days,
                    'agents_included': len(weights),
                    'min_sharpe': self.min_sharpe,
                    'avg_sharpe': np.mean([a['sharpe_ratio'] for a in agent_data]),
                    'method': self.method
                }

                query = text("""
                    INSERT INTO weight_history (
                        timestamp,
                        agent_weights,
                        reason,
                        performance_window,
                        sharpe_improvement,
                        created_by
                    ) VALUES (
                        :timestamp,
                        :weights,
                        :reason,
                        :perf_window,
                        :sharpe_improvement,
                        :created_by
                    )
                    RETURNING id
                """)

                result = session.execute(query, {
                    'timestamp': datetime.now(timezone.utc),
                    'weights': json.dumps(weights),
                    'reason': f"Automated optimization using {self.method}",
                    'perf_window': json.dumps(perf_window),
                    'sharpe_improvement': improvement.get('sharpe_improvement', 0),
                    'created_by': self.agent_name
                })

                weight_id = result.fetchone()[0]
                session.commit()

                self.logger.info(f"Saved new weights (ID: {weight_id})")

                # Also update Redis cache for fast access
                self.redis.set_json('agent_weights:current', weights, expiry=86400 * 7)

        except Exception as e:
            self.logger.error(f"Error saving weights: {e}")

    def _log_work(self, action: str, description: str, details: Optional[Dict] = None):
        """Log agent work to database"""
        try:
            with self.db.get_session() as session:
                query = text("""
                    INSERT INTO agent_work_log (
                        agent_name,
                        task_id,
                        action,
                        description,
                        details
                    ) VALUES (
                        :agent_name,
                        NULL,
                        :action,
                        :description,
                        :details
                    )
                """)

                session.execute(query, {
                    'agent_name': self.agent_name,
                    'action': action,
                    'description': description,
                    'details': json.dumps(details or {})
                })

                session.commit()

        except Exception as e:
            self.logger.warning(f"Could not log work: {e}")


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO)

    agent = WeightOptimizerAgent()
    result = agent.execute()

    print(json.dumps(result, indent=2, default=str))

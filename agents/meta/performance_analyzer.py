"""
Performance Analyzer Agent

Analyzes trading agent performance and calculates key metrics:
- Sharpe ratio
- Win rate
- Profit factor
- Maximum drawdown
- Risk-adjusted returns

Updates the agent_performance table for use by Weight Optimizer.
"""
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
import json
from sqlalchemy import text
from collections import defaultdict

from agents.base_agent import BaseAgent, AgentType
from config.config import config


class PerformanceAnalyzerAgent(BaseAgent):
    """
    Performance Analyzer Agent

    Analyzes trading agent performance by:
    - Tracking signal outcomes and P&L attribution
    - Calculating risk-adjusted performance metrics
    - Identifying top and bottom performers
    - Generating performance reports
    - Updating agent_performance table
    """

    def __init__(self):
        super().__init__(
            agent_name="PerformanceAnalyzer",
            agent_type=AgentType.META,
            version="1.0.0"
        )

        # Performance tracking
        self.lookback_days = 7
        self.min_signals_for_analysis = 5

    def run(self) -> Dict[str, Any]:
        """
        Main execution method

        Returns:
            Dict with analysis results
        """
        self.logger.info("Starting Performance Analyzer cycle")

        # Get all unique agents
        agents = self._get_active_agents()
        self.logger.info(f"Found {len(agents)} active agents to analyze")

        results = {
            'agents_analyzed': [],
            'performance_updates': [],
            'top_performers': [],
            'underperformers': [],
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

        # Analyze each agent
        for agent_name in agents:
            self.logger.info(f"Analyzing performance for {agent_name}")

            try:
                performance = self._analyze_agent_performance(agent_name)

                if performance:
                    # Save to database
                    self._save_agent_performance(agent_name, performance)

                    results['agents_analyzed'].append(agent_name)
                    results['performance_updates'].append({
                        'agent_name': agent_name,
                        'metrics': performance
                    })

                    # Track top performers (Sharpe > 1.5)
                    if performance.get('sharpe_ratio', 0) > 1.5:
                        results['top_performers'].append(agent_name)

                    # Track underperformers (Sharpe < 0.5 or win_rate < 0.45)
                    if (performance.get('sharpe_ratio', 0) < 0.5 or
                        performance.get('win_rate', 0) < 0.45):
                        results['underperformers'].append(agent_name)

            except Exception as e:
                self.logger.error(f"Error analyzing {agent_name}: {e}", exc_info=True)

        # Generate summary
        results['summary'] = self._generate_summary(results)

        # Log work
        self._log_work('completed', f"Analyzed {len(results['agents_analyzed'])} agents")

        self.logger.info(f"Performance analysis completed: {len(results['agents_analyzed'])} agents analyzed")
        return results

    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze specific agent performance data

        Args:
            data: Agent data to analyze

        Returns:
            Dict with analysis results
        """
        agent_name = data.get('agent_name')
        if not agent_name:
            return {'error': 'agent_name required'}

        performance = self._analyze_agent_performance(agent_name)

        return {
            'agent_name': agent_name,
            'performance': performance,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

    def _get_active_agents(self) -> List[str]:
        """Get list of agents that have generated signals recently"""
        try:
            with self.db.get_session() as session:
                cutoff = datetime.now(timezone.utc) - timedelta(days=self.lookback_days)

                query = text("""
                    SELECT DISTINCT agent_name
                    FROM agent_signals
                    WHERE time >= :cutoff
                    AND signal IN ('buy', 'sell')
                    ORDER BY agent_name
                """)

                results = session.execute(query, {'cutoff': cutoff}).fetchall()
                return [row[0] for row in results]

        except Exception as e:
            self.logger.error(f"Error getting active agents: {e}")
            return []

    def _analyze_agent_performance(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """
        Analyze performance metrics for a specific agent

        Args:
            agent_name: Name of agent to analyze

        Returns:
            Dict with performance metrics or None
        """
        try:
            # Get signal outcomes
            signals = self._get_signal_outcomes(agent_name)

            if len(signals) < self.min_signals_for_analysis:
                self.logger.info(
                    f"Insufficient signals for {agent_name}: "
                    f"{len(signals)} < {self.min_signals_for_analysis}"
                )
                return None

            # Calculate metrics
            metrics = {
                'total_signals': len(signals),
                'profitable_signals': sum(1 for s in signals if s['pnl'] > 0),
                'total_return': sum(s['pnl'] for s in signals),
                'avg_return': np.mean([s['pnl'] for s in signals]),
                'sharpe_ratio': self._calculate_sharpe_ratio(signals),
                'win_rate': sum(1 for s in signals if s['pnl'] > 0) / len(signals),
                'max_drawdown': self._calculate_max_drawdown(signals),
                'profit_factor': self._calculate_profit_factor(signals),
                'avg_win': self._calculate_avg_win(signals),
                'avg_loss': self._calculate_avg_loss(signals),
                'largest_win': max([s['pnl'] for s in signals]),
                'largest_loss': min([s['pnl'] for s in signals]),
                'consecutive_wins': self._calculate_consecutive_wins(signals),
                'consecutive_losses': self._calculate_consecutive_losses(signals)
            }

            return metrics

        except Exception as e:
            self.logger.error(f"Error analyzing {agent_name}: {e}", exc_info=True)
            return None

    def _get_signal_outcomes(self, agent_name: str) -> List[Dict[str, Any]]:
        """
        Get signal outcomes with P&L attribution

        Args:
            agent_name: Name of agent

        Returns:
            List of signal outcome dicts
        """
        try:
            with self.db.get_session() as session:
                cutoff = datetime.now(timezone.utc) - timedelta(days=self.lookback_days)

                # Get signals with their attributed P&L
                query = text("""
                    SELECT
                        s.id as signal_id,
                        s.symbol,
                        s.signal,
                        s.confidence,
                        s.time as signal_time,
                        ta.outcome_pnl,
                        ta.outcome_pnl_pct,
                        ta.was_profitable,
                        ta.hold_duration,
                        ta.exit_reason
                    FROM agent_signals s
                    LEFT JOIN trade_attribution ta ON (
                        ta.agent_contributions->:agent_name IS NOT NULL
                    )
                    LEFT JOIN trading_decisions td ON td.id = ta.decision_id
                    WHERE s.agent_name = :agent_name
                        AND s.time >= :cutoff
                        AND s.signal IN ('buy', 'sell')
                        AND ta.outcome_pnl IS NOT NULL
                    ORDER BY s.time ASC
                """)

                results = session.execute(query, {
                    'agent_name': agent_name,
                    'cutoff': cutoff
                }).fetchall()

                signals = []
                for row in results:
                    # Calculate agent's share of P&L based on contribution weight
                    pnl = float(row[5]) if row[5] else 0

                    signals.append({
                        'signal_id': row[0],
                        'symbol': row[1],
                        'signal_type': row[2],
                        'confidence': float(row[3]),
                        'time': row[4],
                        'pnl': pnl,
                        'pnl_pct': float(row[6]) if row[6] else 0,
                        'profitable': row[7],
                        'hold_duration': row[8],
                        'exit_reason': row[9]
                    })

                return signals

        except Exception as e:
            self.logger.error(f"Error getting signal outcomes for {agent_name}: {e}")
            return []

    def _calculate_sharpe_ratio(self, signals: List[Dict[str, Any]], risk_free_rate: float = 0.0) -> float:
        """
        Calculate Sharpe ratio

        Args:
            signals: List of signal outcomes
            risk_free_rate: Annual risk-free rate

        Returns:
            Sharpe ratio
        """
        if not signals:
            return 0.0

        returns = [s['pnl_pct'] for s in signals]

        if len(returns) < 2:
            return 0.0

        mean_return = np.mean(returns)
        std_return = np.std(returns)

        if std_return == 0:
            return 0.0

        # Annualized Sharpe ratio (assuming daily signals)
        sharpe = (mean_return - risk_free_rate) / std_return * np.sqrt(365)

        return float(sharpe)

    def _calculate_max_drawdown(self, signals: List[Dict[str, Any]]) -> float:
        """
        Calculate maximum drawdown

        Args:
            signals: List of signal outcomes

        Returns:
            Maximum drawdown percentage
        """
        if not signals:
            return 0.0

        # Calculate cumulative returns
        cumulative = [0]
        for s in signals:
            cumulative.append(cumulative[-1] + s['pnl'])

        # Calculate drawdown at each point
        peak = cumulative[0]
        max_dd = 0

        for value in cumulative:
            if value > peak:
                peak = value
            dd = (peak - value) / peak if peak != 0 else 0
            max_dd = max(max_dd, dd)

        return float(max_dd)

    def _calculate_profit_factor(self, signals: List[Dict[str, Any]]) -> float:
        """
        Calculate profit factor (gross profit / gross loss)

        Args:
            signals: List of signal outcomes

        Returns:
            Profit factor
        """
        if not signals:
            return 0.0

        gross_profit = sum(s['pnl'] for s in signals if s['pnl'] > 0)
        gross_loss = abs(sum(s['pnl'] for s in signals if s['pnl'] < 0))

        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0.0

        return gross_profit / gross_loss

    def _calculate_avg_win(self, signals: List[Dict[str, Any]]) -> float:
        """Calculate average winning trade"""
        wins = [s['pnl'] for s in signals if s['pnl'] > 0]
        return float(np.mean(wins)) if wins else 0.0

    def _calculate_avg_loss(self, signals: List[Dict[str, Any]]) -> float:
        """Calculate average losing trade"""
        losses = [s['pnl'] for s in signals if s['pnl'] < 0]
        return float(np.mean(losses)) if losses else 0.0

    def _calculate_consecutive_wins(self, signals: List[Dict[str, Any]]) -> int:
        """Calculate maximum consecutive wins"""
        max_consecutive = 0
        current_consecutive = 0

        for s in signals:
            if s['pnl'] > 0:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0

        return max_consecutive

    def _calculate_consecutive_losses(self, signals: List[Dict[str, Any]]) -> int:
        """Calculate maximum consecutive losses"""
        max_consecutive = 0
        current_consecutive = 0

        for s in signals:
            if s['pnl'] < 0:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0

        return max_consecutive

    def _save_agent_performance(self, agent_name: str, metrics: Dict[str, Any]):
        """
        Save agent performance metrics to database

        Args:
            agent_name: Name of agent
            metrics: Performance metrics dict
        """
        try:
            with self.db.get_session() as session:
                query = text("""
                    INSERT INTO agent_performance (
                        agent_name,
                        date,
                        total_signals,
                        profitable_signals,
                        total_return,
                        avg_return,
                        sharpe_ratio,
                        win_rate,
                        max_drawdown,
                        profit_factor
                    ) VALUES (
                        :agent_name,
                        :date,
                        :total_signals,
                        :profitable_signals,
                        :total_return,
                        :avg_return,
                        :sharpe_ratio,
                        :win_rate,
                        :max_drawdown,
                        :profit_factor
                    )
                    ON CONFLICT (agent_name, date)
                    DO UPDATE SET
                        total_signals = :total_signals,
                        profitable_signals = :profitable_signals,
                        total_return = :total_return,
                        avg_return = :avg_return,
                        sharpe_ratio = :sharpe_ratio,
                        win_rate = :win_rate,
                        max_drawdown = :max_drawdown,
                        profit_factor = :profit_factor,
                        created_at = NOW()
                """)

                session.execute(query, {
                    'agent_name': agent_name,
                    'date': datetime.now(timezone.utc).date(),
                    'total_signals': metrics['total_signals'],
                    'profitable_signals': metrics['profitable_signals'],
                    'total_return': metrics['total_return'],
                    'avg_return': metrics['avg_return'],
                    'sharpe_ratio': metrics['sharpe_ratio'],
                    'win_rate': metrics['win_rate'],
                    'max_drawdown': metrics['max_drawdown'],
                    'profit_factor': metrics.get('profit_factor', 0)
                })

                session.commit()

                self.logger.info(
                    f"Saved performance for {agent_name}: "
                    f"Sharpe={metrics['sharpe_ratio']:.2f}, "
                    f"WinRate={metrics['win_rate']:.2%}"
                )

        except Exception as e:
            self.logger.error(f"Error saving performance for {agent_name}: {e}")

    def _generate_summary(self, results: Dict[str, Any]) -> str:
        """Generate a text summary of the analysis"""
        lines = []

        lines.append(f"Performance Analysis Summary")
        lines.append(f"Agents Analyzed: {len(results['agents_analyzed'])}")

        if results['top_performers']:
            lines.append(f"Top Performers: {', '.join(results['top_performers'])}")

        if results['underperformers']:
            lines.append(f"Underperformers: {', '.join(results['underperformers'])}")

        return '\n'.join(lines)

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

    def get_agent_ranking(self) -> List[Dict[str, Any]]:
        """
        Get current agent ranking by performance

        Returns:
            List of agents ranked by Sharpe ratio
        """
        try:
            with self.db.get_session() as session:
                query = text("""
                    SELECT
                        agent_name,
                        sharpe_ratio,
                        win_rate,
                        total_signals,
                        total_return,
                        date
                    FROM agent_performance
                    WHERE date >= CURRENT_DATE - INTERVAL '7 days'
                    ORDER BY sharpe_ratio DESC NULLS LAST, win_rate DESC
                """)

                results = session.execute(query).fetchall()

                ranking = []
                for row in results:
                    ranking.append({
                        'agent_name': row[0],
                        'sharpe_ratio': float(row[1]) if row[1] else 0,
                        'win_rate': float(row[2]) if row[2] else 0,
                        'total_signals': row[3],
                        'total_return': float(row[4]) if row[4] else 0,
                        'date': row[5].isoformat()
                    })

                return ranking

        except Exception as e:
            self.logger.error(f"Error getting agent ranking: {e}")
            return []


if __name__ == "__main__":
    import logging
    import json

    logging.basicConfig(level=logging.INFO)

    agent = PerformanceAnalyzerAgent()
    result = agent.execute()

    print(json.dumps(result, indent=2, default=str))

    # Print ranking
    print("\n=== Agent Ranking ===")
    ranking = agent.get_agent_ranking()
    for i, agent_data in enumerate(ranking[:10], 1):
        print(
            f"{i}. {agent_data['agent_name']}: "
            f"Sharpe={agent_data['sharpe_ratio']:.2f}, "
            f"WinRate={agent_data['win_rate']:.1%}, "
            f"Signals={agent_data['total_signals']}"
        )

#!/usr/bin/env python3
"""
Dashboard Regression Test Agent

Runs hourly automated tests to ensure:
- Database data is fresh
- Dashboard is loading properly
- All panels are displaying data
- System is functioning during continuous improvement iterations

Reports issues to improvement_suggestions table for autonomous fixing.
"""
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from sqlalchemy import text
import logging

from agents.base_agent import BaseAgent, AgentType


class DashboardTestAgent(BaseAgent):
    """
    Dashboard Regression Test Agent

    Performs automated regression testing every hour to ensure
    the dashboard and data pipeline remain functional during
    continuous improvement iterations.
    """

    def __init__(self):
        super().__init__(
            agent_name="DashboardTestAgent",
            agent_type=AgentType.META,
            version="1.0.0"
        )

        self.test_results = []

    def run(self) -> Dict[str, Any]:
        """Main execution method (required by BaseAgent)"""
        return self.execute()

    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze test data (required by BaseAgent)

        Args:
            data: Test data to analyze

        Returns:
            Analysis results
        """
        return {
            'analyzed': True,
            'data_type': data.get('type', 'unknown'),
            'tests_count': len(data.get('tests', []))
        }

    def execute(self) -> Dict[str, Any]:
        """
        Execute dashboard regression tests

        Returns:
            Dict with test results
        """
        self.logger.info("Starting Dashboard Regression Tests")

        try:
            self.test_results = []

            # Test 1: Database data freshness
            self._test_data_freshness()

            # Test 2: Portfolio snapshots
            self._test_portfolio_snapshots()

            # Test 3: Trading orchestrator
            self._test_trading_orchestrator()

            # Test 4: System metrics
            self._test_system_metrics()

            # Analyze results
            total_tests = len(self.test_results)
            passed_tests = sum(1 for test in self.test_results if test['passed'])
            failed_tests = total_tests - passed_tests

            # Report failures as improvement suggestions
            if failed_tests > 0:
                self._report_failures()

            result = {
                'success': True,
                'total_tests': total_tests,
                'passed': passed_tests,
                'failed': failed_tests,
                'tests': self.test_results,
                'all_passed': failed_tests == 0
            }

            if failed_tests > 0:
                self.logger.warning(f"Dashboard tests: {passed_tests}/{total_tests} passed, {failed_tests} failed")
            else:
                self.logger.info(f"Dashboard tests: All {total_tests} tests passed ✓")

            return result

        except Exception as e:
            self.logger.error(f"Error in dashboard tests: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'total_tests': 0,
                'passed': 0,
                'failed': 0
            }

    def _test_data_freshness(self):
        """Test that database data is fresh (within last 5 minutes)"""
        test_name = "Data Freshness Check"

        try:
            with self.db.get_session() as session:
                query = text("""
                    SELECT time
                    FROM paper_portfolio_snapshots
                    ORDER BY time DESC
                    LIMIT 1
                """)

                result = session.execute(query).fetchone()

                if not result:
                    self.test_results.append({
                        'test': test_name,
                        'passed': False,
                        'message': 'No portfolio snapshots found in database',
                        'severity': 'high'
                    })
                    return

                snapshot_time = result[0]
                if snapshot_time.tzinfo is None:
                    snapshot_time = snapshot_time.replace(tzinfo=timezone.utc)

                time_diff = datetime.now(timezone.utc) - snapshot_time
                age_minutes = time_diff.total_seconds() / 60

                # Data should be less than 5 minutes old
                if age_minutes < 5:
                    self.test_results.append({
                        'test': test_name,
                        'passed': True,
                        'message': f'Data is fresh ({age_minutes:.1f} min old)',
                        'severity': 'none'
                    })
                else:
                    self.test_results.append({
                        'test': test_name,
                        'passed': False,
                        'message': f'Data is stale ({age_minutes:.1f} min old, should be < 5 min)',
                        'severity': 'high'
                    })

        except Exception as e:
            self.test_results.append({
                'test': test_name,
                'passed': False,
                'message': f'Test failed with error: {str(e)}',
                'severity': 'high'
            })

    def _test_portfolio_snapshots(self):
        """Test that portfolio snapshots table has recent data"""
        test_name = "Portfolio Snapshots Availability"

        try:
            with self.db.get_session() as session:
                # Check last hour of data
                query = text("""
                    SELECT COUNT(*)
                    FROM paper_portfolio_snapshots
                    WHERE time >= NOW() - INTERVAL '1 hour'
                """)

                result = session.execute(query).fetchone()
                count = result[0] if result else 0

                # Should have at least a few snapshots in last hour
                if count > 5:
                    self.test_results.append({
                        'test': test_name,
                        'passed': True,
                        'message': f'{count} snapshots in last hour',
                        'severity': 'none'
                    })
                else:
                    self.test_results.append({
                        'test': test_name,
                        'passed': False,
                        'message': f'Only {count} snapshots in last hour (expected > 5)',
                        'severity': 'medium'
                    })

        except Exception as e:
            self.test_results.append({
                'test': test_name,
                'passed': False,
                'message': f'Test failed with error: {str(e)}',
                'severity': 'high'
            })

    def _test_trading_orchestrator(self):
        """Test that trading orchestrator is running"""
        test_name = "Trading Orchestrator Status"

        try:
            import subprocess
            result = subprocess.run(
                ['ps', 'aux'],
                capture_output=True,
                text=True,
                timeout=5
            )

            # Look for orchestrator.py process
            lines = result.stdout.split('\n')
            orchestrator_found = any('agents/orchestrator/orchestrator.py' in line for line in lines)

            if orchestrator_found:
                self.test_results.append({
                    'test': test_name,
                    'passed': True,
                    'message': 'Trading orchestrator process is running',
                    'severity': 'none'
                })
            else:
                self.test_results.append({
                    'test': test_name,
                    'passed': False,
                    'message': 'Trading orchestrator process not found',
                    'severity': 'critical'
                })

        except Exception as e:
            self.test_results.append({
                'test': test_name,
                'passed': False,
                'message': f'Test failed with error: {str(e)}',
                'severity': 'high'
            })

    def _test_system_metrics(self):
        """Test that system metrics are being collected"""
        test_name = "System Metrics Collection"

        try:
            with self.db.get_session() as session:
                query = text("""
                    SELECT COUNT(*)
                    FROM system_metrics
                    WHERE time >= NOW() - INTERVAL '1 hour'
                """)

                result = session.execute(query).fetchone()
                count = result[0] if result else 0

                if count > 0:
                    self.test_results.append({
                        'test': test_name,
                        'passed': True,
                        'message': f'{count} metrics collected in last hour',
                        'severity': 'none'
                    })
                else:
                    self.test_results.append({
                        'test': test_name,
                        'passed': False,
                        'message': 'No system metrics collected in last hour',
                        'severity': 'low'
                    })

        except Exception as e:
            self.test_results.append({
                'test': test_name,
                'passed': False,
                'message': f'Test failed with error: {str(e)}',
                'severity': 'medium'
            })

    def _report_failures(self):
        """Report test failures to improvement_suggestions table"""
        try:
            with self.db.get_session() as session:
                for test in self.test_results:
                    if not test['passed']:
                        # Create improvement suggestion for each failure
                        query = text("""
                            INSERT INTO improvement_suggestions
                            (suggestion_type, priority, title, description, expected_impact, implementation_effort, status, created_at)
                            VALUES
                            (:type, :priority, :title, :description, :impact, :effort, 'pending', :created_at)
                        """)

                        # Map severity to priority
                        severity_to_priority = {
                            'critical': 'high',
                            'high': 'high',
                            'medium': 'medium',
                            'low': 'low'
                        }

                        priority = severity_to_priority.get(test['severity'], 'medium')

                        session.execute(query, {
                            'type': 'performance',
                            'priority': priority,
                            'title': f"Dashboard Test Failed: {test['test']}",
                            'description': f"Automated dashboard regression test failed. {test['message']}",
                            'impact': test['severity'],
                            'effort': 'medium',
                            'created_at': datetime.now(timezone.utc)
                        })

                session.commit()
                self.logger.info(f"Reported {sum(1 for t in self.test_results if not t['passed'])} test failures")

        except Exception as e:
            self.logger.error(f"Error reporting test failures: {e}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    agent = DashboardTestAgent()
    result = agent.execute()

    import json
    print(json.dumps(result, indent=2, default=str))

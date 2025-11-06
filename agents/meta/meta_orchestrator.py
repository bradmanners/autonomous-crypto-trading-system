#!/usr/bin/env python3
"""
Meta Agent Orchestrator

Coordinates the three meta agents:
1. Performance Analyzer - Analyzes agent performance
2. Weight Optimizer - Optimizes agent weights
3. Project Manager - Generates reports and monitors system

This orchestrator runs them in the correct sequence and frequency.
"""
import time
import logging
from datetime import datetime, timezone
from typing import Dict, Any

from agents.meta.performance_analyzer import PerformanceAnalyzerAgent
from agents.meta.weight_optimizer import WeightOptimizerAgent
from agents.meta.project_manager import ProjectManagerAgent
from agents.meta.implementation_agent import ImplementationAgent
from agents.meta.dashboard_test_agent import DashboardTestAgent


class MetaOrchestrator:
    """
    Orchestrates meta agents for autonomous system management

    Schedule:
    - Performance Analyzer: Every 6 hours
    - Weight Optimizer: Every 24 hours (after analyzer)
    - Implementation Agent: Every 15 minutes (auto-implements recommendations)
    - Project Manager: Every 15 minutes (autonomous improvement tracking)
    - Dashboard Test Agent: Every 1 hour (regression testing)
    """

    def __init__(self):
        self.logger = logging.getLogger("MetaOrchestrator")

        # Initialize agents
        self.performance_analyzer = PerformanceAnalyzerAgent()
        self.weight_optimizer = WeightOptimizerAgent()
        self.implementation_agent = ImplementationAgent()
        self.project_manager = ProjectManagerAgent()
        self.dashboard_test = DashboardTestAgent()

        # Tracking
        self.cycle_count = 0

    def run_cycle(self) -> Dict[str, Any]:
        """
        Run one complete cycle of all meta agents

        Returns:
            Dict with results from all agents
        """
        self.cycle_count += 1
        self.logger.info(f"Starting meta orchestrator cycle #{self.cycle_count}")

        results = {
            'cycle': self.cycle_count,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'performance_analysis': None,
            'weight_optimization': None,
            'implementation': None,
            'project_report': None,
            'dashboard_test': None
        }

        try:
            # Step 1: Analyze agent performance
            self.logger.info("Running Performance Analyzer...")
            perf_result = self.performance_analyzer.execute()
            results['performance_analysis'] = perf_result

            if perf_result.get('success'):
                agents_analyzed = len(perf_result.get('agents_analyzed', []))
                self.logger.info(f"✓ Performance analysis complete: {agents_analyzed} agents")

            # Step 2: Optimize weights (uses performance data)
            self.logger.info("Running Weight Optimizer...")
            weight_result = self.weight_optimizer.execute()
            results['weight_optimization'] = weight_result

            if weight_result.get('success') and weight_result.get('weights_updated'):
                improvement = weight_result.get('improvement', {})
                sharpe_imp = improvement.get('sharpe_improvement', 0)
                self.logger.info(f"✓ Weights optimized: Sharpe improvement = {sharpe_imp:.3f}")

            # Step 3: Auto-implement recommendations
            self.logger.info("Running Implementation Agent...")
            impl_result = self.implementation_agent.execute()
            results['implementation'] = impl_result

            if impl_result.get('success'):
                impl_count = impl_result.get('recommendations_implemented', 0)
                self.logger.info(f"✓ Implementation agent complete: {impl_count} recommendations implemented")

            # Step 4: Generate project report
            self.logger.info("Running Project Manager...")
            report_result = self.project_manager.execute()
            results['project_report'] = report_result

            if report_result.get('success'):
                report_gen = report_result.get('report_generated', False)
                self.logger.info(f"✓ Project management complete (report={report_gen})")

            # Step 5: Dashboard regression tests (every hour = every 4 cycles)
            if self.cycle_count % 4 == 0:
                self.logger.info("Running Dashboard Test Agent...")
                dashboard_result = self.dashboard_test.execute()
                results['dashboard_test'] = dashboard_result

                if dashboard_result.get('success'):
                    total = dashboard_result.get('total_tests', 0)
                    passed = dashboard_result.get('passed', 0)
                    failed = dashboard_result.get('failed', 0)
                    self.logger.info(f"✓ Dashboard tests complete: {passed}/{total} passed, {failed} failed")
            else:
                results['dashboard_test'] = {'skipped': True, 'reason': 'Not hourly cycle'}

            results['success'] = True
            self.logger.info(f"Meta orchestrator cycle #{self.cycle_count} completed successfully")

        except Exception as e:
            self.logger.error(f"Error in meta orchestrator cycle: {e}", exc_info=True)
            results['success'] = False
            results['error'] = str(e)

        return results

    def run_continuous(self, interval_hours: float = 2.0):
        """
        Run continuously with specified interval

        Args:
            interval_hours: Hours between cycles
        """
        self.logger.info(f"Starting continuous meta orchestrator (interval={interval_hours}h)")

        while True:
            try:
                result = self.run_cycle()

                if result.get('success'):
                    self.logger.info(f"Cycle complete. Sleeping for {interval_hours} hours...")
                else:
                    self.logger.warning(f"Cycle had errors. Sleeping for {interval_hours} hours...")

                time.sleep(interval_hours * 3600)

            except KeyboardInterrupt:
                self.logger.info("Shutdown requested. Exiting...")
                break
            except Exception as e:
                self.logger.error(f"Unexpected error: {e}", exc_info=True)
                self.logger.info("Sleeping before retry...")
                time.sleep(300)  # 5 minutes before retry


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    orchestrator = MetaOrchestrator()

    # Run once for testing
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--once':
        result = orchestrator.run_cycle()
        import json
        print(json.dumps(result, indent=2, default=str))
    else:
        # Run continuously every 15 minutes
        orchestrator.run_continuous(interval_hours=0.25)

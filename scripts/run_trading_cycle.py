#!/usr/bin/env python3
"""
Trading Cycle Runner

Executes one complete trading cycle:
1. Collect price data
2. Run technical analysis
3. Make trading decisions
4. Log results

This script is designed to be run on a schedule (e.g., hourly via cron)
"""
import sys
import os
from pathlib import Path
from datetime import datetime
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agents.orchestrator import run_orchestrator
import logging

# Get logger (logging is already configured by imports)
logger = logging.getLogger(__name__)


def main():
    """Run a single trading cycle"""
    logger.info("=" * 60)
    logger.info(f"Starting trading cycle at {datetime.now().isoformat()}")
    logger.info("=" * 60)

    try:
        # Run the orchestrator
        result = run_orchestrator()

        # Log summary
        logger.info("-" * 60)
        logger.info("CYCLE SUMMARY:")
        logger.info(f"  Success: {result.get('success', False)}")
        logger.info(f"  Duration: {result.get('duration_seconds', 0):.2f}s")

        if 'price_collection' in result:
            logger.info(f"  Price data: {result['price_collection'].get('candles_collected', 0)} candles collected")

        if 'technical_analysis' in result:
            ta = result['technical_analysis']
            logger.info(f"  Analysis: {ta.get('pairs_analyzed', 0)} pairs analyzed")
            logger.info(f"  Signals: {ta.get('buy_signals', 0)} BUY, {ta.get('sell_signals', 0)} SELL, {ta.get('hold_signals', 0)} HOLD")

        if 'trading_decisions' in result:
            decisions = result['trading_decisions']
            logger.info(f"  Decisions: {len(decisions)} made")

            for decision in decisions:
                logger.info(
                    f"    {decision['symbol']}: {decision['decision']} "
                    f"(confidence: {decision['confidence']:.0%})"
                )

        if 'system_health' in result:
            health = result['system_health']
            logger.info(f"  System health: {health.get('status', 'unknown')}")

            if health.get('issues'):
                logger.warning(f"  Issues detected: {len(health['issues'])}")
                for issue in health['issues']:
                    logger.warning(f"    - {issue}")

        if result.get('errors'):
            logger.error(f"  Errors: {len(result['errors'])}")
            for error in result['errors']:
                logger.error(f"    - {error}")

        logger.info("-" * 60)

        # Write summary to file for monitoring
        summary_file = project_root / 'logs' / 'last_cycle.json'
        summary_file.parent.mkdir(parents=True, exist_ok=True)

        with open(summary_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)

        logger.info(f"Cycle complete. Summary written to {summary_file}")

        # Exit with appropriate status code
        if result.get('success'):
            sys.exit(0)
        else:
            sys.exit(1)

    except Exception as e:
        logger.error(f"Fatal error during trading cycle: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

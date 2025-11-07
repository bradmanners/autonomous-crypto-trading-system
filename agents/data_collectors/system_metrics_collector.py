"""
System Metrics Collector Agent

Collects system performance metrics (CPU, memory, disk) and stores them
for monitoring in Grafana dashboards.

Metrics collected every minute:
- CPU usage (%)
- Memory usage (%)
- Disk usage (%)
- Process count
- Database connections
"""

import psutil
import logging
from datetime import datetime, timezone
from typing import Dict, Any
from sqlalchemy import text

from agents.base_agent import BaseAgent, AgentType
from utils.database import DatabaseManager


class SystemMetricsCollector(BaseAgent):
    """
    System metrics collector agent

    Responsibilities:
    - Collect CPU, memory, and disk metrics
    - Track process count and database connections
    - Store metrics in database for Grafana visualization
    - Run every minute via orchestrator
    """

    def __init__(self):
        super().__init__(
            agent_name="SystemMetricsCollector",
            agent_type=AgentType.DATA_COLLECTOR,
            version="1.0.0"
        )

    def run(self) -> Dict[str, Any]:
        """
        Main execution method (required by BaseAgent)
        """
        return self.execute()

    def execute(self) -> Dict[str, Any]:
        """
        Collect and store system metrics

        Returns:
            Dict with execution results
        """
        try:
            # Collect metrics
            metrics = self._collect_metrics()

            # Store in database
            self._store_metrics(metrics)

            self.logger.info(
                f"System metrics collected: "
                f"CPU={metrics['cpu_percent']:.1f}%, "
                f"Memory={metrics['memory_percent']:.1f}%, "
                f"Disk={metrics['disk_percent']:.1f}%"
            )

            return {
                'success': True,
                'metrics': metrics,
                'timestamp': metrics['timestamp']
            }

        except Exception as e:
            self.logger.error(f"Error collecting system metrics: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze recent system metrics

        Args:
            data: Optional parameters (e.g., hours to look back)

        Returns:
            Dict with metric analysis
        """
        hours = data.get('hours', 24)

        with self.db.get_session() as session:
            query = text("""
                SELECT
                    AVG(cpu_percent) as avg_cpu,
                    MAX(cpu_percent) as max_cpu,
                    AVG(memory_percent) as avg_memory,
                    MAX(memory_percent) as max_memory,
                    AVG(disk_percent) as avg_disk,
                    COUNT(*) as sample_count
                FROM system_metrics
                WHERE time >= NOW() - INTERVAL '1 hour' * :hours
            """)

            result = session.execute(query, {'hours': hours}).fetchone()

            if result and result[5] > 0:
                return {
                    'period_hours': hours,
                    'avg_cpu_percent': float(result[0]) if result[0] else 0,
                    'max_cpu_percent': float(result[1]) if result[1] else 0,
                    'avg_memory_percent': float(result[2]) if result[2] else 0,
                    'max_memory_percent': float(result[3]) if result[3] else 0,
                    'avg_disk_percent': float(result[4]) if result[4] else 0,
                    'sample_count': result[5]
                }
            else:
                return {
                    'period_hours': hours,
                    'sample_count': 0,
                    'message': 'No metrics found for this period'
                }

    def _collect_metrics(self) -> Dict[str, Any]:
        """
        Collect current system metrics

        Returns:
            Dict with all metrics
        """
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()

        # Memory metrics
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_used_mb = memory.used / (1024 * 1024)
        memory_total_mb = memory.total / (1024 * 1024)

        # Disk metrics
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        disk_used_gb = disk.used / (1024 * 1024 * 1024)
        disk_total_gb = disk.total / (1024 * 1024 * 1024)

        # Process count
        process_count = len(psutil.pids())

        # Database connections (approximate)
        try:
            with self.db.get_session() as session:
                result = session.execute(text("""
                    SELECT COUNT(*) FROM pg_stat_activity
                    WHERE datname = current_database()
                """)).fetchone()
                db_connections = result[0] if result else 0
        except:
            db_connections = 0

        return {
            'timestamp': datetime.now(timezone.utc),
            'cpu_percent': cpu_percent,
            'cpu_count': cpu_count,
            'memory_percent': memory_percent,
            'memory_used_mb': memory_used_mb,
            'memory_total_mb': memory_total_mb,
            'disk_percent': disk_percent,
            'disk_used_gb': disk_used_gb,
            'disk_total_gb': disk_total_gb,
            'process_count': process_count,
            'db_connections': db_connections
        }

    def _store_metrics(self, metrics: Dict[str, Any]):
        """
        Store metrics in database

        Args:
            metrics: Dict with all metrics
        """
        with self.db.get_session() as session:
            session.execute(text("""
                INSERT INTO system_metrics (
                    time, cpu_percent, cpu_count,
                    memory_percent, memory_used_mb, memory_total_mb,
                    disk_percent, disk_used_gb, disk_total_gb,
                    process_count, db_connections
                ) VALUES (
                    :time, :cpu_percent, :cpu_count,
                    :memory_percent, :memory_used_mb, :memory_total_mb,
                    :disk_percent, :disk_used_gb, :disk_total_gb,
                    :process_count, :db_connections
                )
            """), {
                'time': metrics['timestamp'],
                'cpu_percent': metrics['cpu_percent'],
                'cpu_count': metrics['cpu_count'],
                'memory_percent': metrics['memory_percent'],
                'memory_used_mb': metrics['memory_used_mb'],
                'memory_total_mb': metrics['memory_total_mb'],
                'disk_percent': metrics['disk_percent'],
                'disk_used_gb': metrics['disk_used_gb'],
                'disk_total_gb': metrics['disk_total_gb'],
                'process_count': metrics['process_count'],
                'db_connections': metrics['db_connections']
            })

            session.commit()


if __name__ == "__main__":
    # Test the system metrics collector
    logging.basicConfig(level=logging.INFO)

    print("\n" + "="*80)
    print("System Metrics Collector - Test Run")
    print("="*80 + "\n")

    collector = SystemMetricsCollector()

    # Collect metrics
    result = collector.execute()

    print("Results:")
    if result['success']:
        print(f"  ✅ Success")
        print(f"  Timestamp: {result['timestamp']}")
        print(f"  CPU: {result['metrics']['cpu_percent']:.1f}% ({result['metrics']['cpu_count']} cores)")
        print(f"  Memory: {result['metrics']['memory_percent']:.1f}% ({result['metrics']['memory_used_mb']:.0f}/{result['metrics']['memory_total_mb']:.0f} MB)")
        print(f"  Disk: {result['metrics']['disk_percent']:.1f}% ({result['metrics']['disk_used_gb']:.1f}/{result['metrics']['disk_total_gb']:.1f} GB)")
        print(f"  Processes: {result['metrics']['process_count']}")
        print(f"  DB Connections: {result['metrics']['db_connections']}")
    else:
        print(f"  ❌ Failed: {result.get('error')}")

    # Analyze recent metrics
    print("\n" + "-"*80)
    analysis = collector.analyze({'hours': 24})
    print("\n24-Hour Analysis:")
    if analysis.get('sample_count', 0) > 0:
        print(f"  Samples: {analysis['sample_count']}")
        print(f"  CPU: avg={analysis['avg_cpu_percent']:.1f}%, max={analysis['max_cpu_percent']:.1f}%")
        print(f"  Memory: avg={analysis['avg_memory_percent']:.1f}%, max={analysis['max_memory_percent']:.1f}%")
        print(f"  Disk: avg={analysis['avg_disk_percent']:.1f}%")
    else:
        print(f"  {analysis.get('message', 'No data')}")

    print("\n✅ Test complete!\n")

"""
Project Manager Agent

Autonomous agent that:
- Monitors project tasks and agent work
- Generates comprehensive status reports every 2 hours
- Tracks trading performance and agent effectiveness
- Produces architecture, security, and improvement recommendations
- Emails reports to stakeholders
"""
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy import text

from agents.base_agent import BaseAgent, AgentType
from config.config import config


class ProjectManagerAgent(BaseAgent):
    """
    Project Manager Agent

    Orchestrates autonomous project management by:
    - Tracking all active tasks and agent work
    - Analyzing trading system performance
    - Generating comprehensive reports
    - Emailing status updates
    - Creating improvement recommendations
    """

    def __init__(self):
        super().__init__(
            agent_name="ProjectManager",
            agent_type=AgentType.META,
            version="1.0.0"
        )

        # Load email configuration
        self._load_email_config()

        # Report tracking
        self.last_report_time = None
        self.report_interval_hours = 2

    def _load_email_config(self):
        """Load email configuration from database"""
        try:
            with self.db.get_session() as session:
                query = text("""
                    SELECT config_key, config_value
                    FROM email_config
                """)

                results = session.execute(query).fetchall()

                self.email_config = {row[0]: row[1] for row in results}

                # Set report frequency
                if 'report_frequency_hours' in self.email_config:
                    self.report_interval_hours = int(self.email_config['report_frequency_hours'])

                self.logger.info(f"Loaded email config: {len(self.email_config)} settings")

        except Exception as e:
            self.logger.warning(f"Could not load email config: {e}")
            self.email_config = {}

    def run(self) -> Dict[str, Any]:
        """
        Main execution method

        Returns:
            Dict with execution results
        """
        self.logger.info("Starting Project Manager cycle")

        # Check if it's time to generate a report
        should_report = self._should_generate_report()

        # Gather all data
        tasks_data = self._get_tasks_summary()
        agent_work = self._get_agent_work_summary()
        trading_performance = self._get_trading_performance()
        agent_performance = self._get_agent_performance()
        system_metrics = self._get_system_metrics()
        completed_improvements = self._get_completed_improvements()

        # Generate recommendations
        recommendations = self._generate_recommendations(
            tasks_data,
            agent_work,
            trading_performance,
            agent_performance,
            system_metrics
        )

        result = {
            'tasks_summary': tasks_data,
            'agent_work_summary': agent_work,
            'trading_performance': trading_performance,
            'agent_performance': agent_performance,
            'system_metrics': system_metrics,
            'completed_improvements': completed_improvements,
            'recommendations': recommendations,
            'report_generated': False
        }

        # Generate and send report if needed
        if should_report:
            report = self._generate_report(result)
            self._save_report(report)

            # Send email
            if self.email_config.get('recipient_email'):
                email_sent = self._send_email_report(report)
                result['report_generated'] = True
                result['email_sent'] = email_sent

            self.last_report_time = datetime.now(timezone.utc)

        self.logger.info("Project Manager cycle completed")
        return result

    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze project data and generate insights

        Args:
            data: Project data to analyze

        Returns:
            Dict with analysis results
        """
        # This is used for ad-hoc analysis requests
        return {
            'analysis_type': 'project_status',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'insights': self._generate_recommendations(
                data.get('tasks', {}),
                data.get('agent_work', {}),
                data.get('trading_performance', {}),
                data.get('agent_performance', {}),
                data.get('system_metrics', {})
            )
        }

    def _should_generate_report(self) -> bool:
        """Determine if it's time to generate a report"""
        if self.last_report_time is None:
            return True

        time_since_last = datetime.now(timezone.utc) - self.last_report_time
        return time_since_last.total_seconds() >= (self.report_interval_hours * 3600)

    def _get_tasks_summary(self) -> Dict[str, Any]:
        """Get summary of all project tasks"""
        try:
            with self.db.get_session() as session:
                # Get task counts by status
                query = text("""
                    SELECT
                        status,
                        priority,
                        COUNT(*) as count,
                        AVG(progress_percentage) as avg_progress
                    FROM project_tasks
                    WHERE status IN ('pending', 'in_progress', 'blocked')
                    GROUP BY status, priority
                    ORDER BY
                        CASE priority
                            WHEN 'critical' THEN 1
                            WHEN 'high' THEN 2
                            WHEN 'medium' THEN 3
                            WHEN 'low' THEN 4
                        END,
                        status
                """)

                results = session.execute(query).fetchall()

                tasks_by_status = {}
                for row in results:
                    status, priority, count, avg_progress = row
                    if status not in tasks_by_status:
                        tasks_by_status[status] = []
                    tasks_by_status[status].append({
                        'priority': priority,
                        'count': count,
                        'avg_progress': float(avg_progress) if avg_progress else 0
                    })

                # Get recent task activity
                recent_query = text("""
                    SELECT
                        id, task_name, status, priority, progress_percentage,
                        started_at, completed_at, assigned_agent
                    FROM project_tasks
                    ORDER BY
                        CASE
                            WHEN completed_at IS NOT NULL THEN completed_at
                            WHEN started_at IS NOT NULL THEN started_at
                            ELSE created_at
                        END DESC
                    LIMIT 10
                """)

                recent_tasks = []
                for row in session.execute(recent_query).fetchall():
                    recent_tasks.append({
                        'id': row[0],
                        'name': row[1],
                        'status': row[2],
                        'priority': row[3],
                        'progress': row[4],
                        'started_at': row[5].isoformat() if row[5] else None,
                        'completed_at': row[6].isoformat() if row[6] else None,
                        'assigned_agent': row[7]
                    })

                return {
                    'by_status': tasks_by_status,
                    'recent_tasks': recent_tasks,
                    'total_active': sum(len(tasks) for tasks in tasks_by_status.values())
                }

        except Exception as e:
            self.logger.error(f"Error getting tasks summary: {e}")
            return {'error': str(e)}

    def _get_agent_work_summary(self) -> Dict[str, Any]:
        """Get summary of agent work in the last 2 hours"""
        try:
            with self.db.get_session() as session:
                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=self.report_interval_hours)

                query = text("""
                    SELECT
                        agent_name,
                        action,
                        COUNT(*) as action_count,
                        MAX(timestamp) as last_activity
                    FROM agent_work_log
                    WHERE timestamp >= :cutoff
                    GROUP BY agent_name, action
                    ORDER BY agent_name, action_count DESC
                """)

                results = session.execute(query, {'cutoff': cutoff_time}).fetchall()

                work_by_agent = {}
                for row in results:
                    agent_name, action, count, last_activity = row
                    if agent_name not in work_by_agent:
                        work_by_agent[agent_name] = {
                            'actions': [],
                            'last_activity': last_activity.isoformat()
                        }
                    work_by_agent[agent_name]['actions'].append({
                        'action': action,
                        'count': count
                    })

                return {
                    'by_agent': work_by_agent,
                    'total_agents_active': len(work_by_agent),
                    'period_hours': self.report_interval_hours
                }

        except Exception as e:
            self.logger.error(f"Error getting agent work summary: {e}")
            return {'error': str(e)}

    def _get_trading_performance(self) -> Dict[str, Any]:
        """Get trading system performance metrics"""
        try:
            with self.db.get_session() as session:
                # Get portfolio summary
                portfolio_query = text("""
                    SELECT
                        cash_balance,
                        total_value,
                        total_pnl,
                        total_pnl_pct,
                        daily_pnl,
                        daily_pnl_pct,
                        num_positions,
                        max_drawdown,
                        time
                    FROM paper_portfolio_snapshots
                    ORDER BY time DESC
                    LIMIT 1
                """)

                portfolio = session.execute(portfolio_query).fetchone()

                portfolio_data = {}
                if portfolio:
                    portfolio_data = {
                        'cash_balance': float(portfolio[0]),
                        'total_value': float(portfolio[1]),
                        'total_pnl': float(portfolio[2]),
                        'total_pnl_pct': float(portfolio[3]),
                        'daily_pnl': float(portfolio[4]),
                        'daily_pnl_pct': float(portfolio[5]),
                        'num_positions': portfolio[6],
                        'max_drawdown': float(portfolio[7]),
                        'snapshot_time': portfolio[8].isoformat()
                    }

                # Get trade statistics
                trades_query = text("""
                    SELECT
                        COUNT(*) as total_trades,
                        COUNT(CASE WHEN status = 'filled' THEN 1 END) as filled_trades,
                        SUM(CASE WHEN side = 'buy' THEN 1 ELSE 0 END) as buy_trades,
                        SUM(CASE WHEN side = 'sell' THEN 1 ELSE 0 END) as sell_trades
                    FROM paper_orders
                    WHERE created_at >= NOW() - INTERVAL '24 hours'
                """)

                trades = session.execute(trades_query).fetchone()

                trades_data = {}
                if trades:
                    trades_data = {
                        'total_trades_24h': trades[0],
                        'filled_trades_24h': trades[1],
                        'buy_trades_24h': trades[2],
                        'sell_trades_24h': trades[3]
                    }

                # Get current positions
                positions_query = text("""
                    SELECT
                        symbol,
                        quantity,
                        entry_price,
                        current_price,
                        unrealized_pnl,
                        unrealized_pnl_pct
                    FROM paper_positions
                    ORDER BY opened_at DESC
                """)

                positions = []
                for row in session.execute(positions_query).fetchall():
                    positions.append({
                        'symbol': row[0],
                        'quantity': float(row[1]),
                        'entry_price': float(row[2]),
                        'current_price': float(row[3]) if row[3] else None,
                        'unrealized_pnl': float(row[4]) if row[4] else None,
                        'unrealized_pnl_pct': float(row[5]) if row[5] else None
                    })

                return {
                    'portfolio': portfolio_data,
                    'trades': trades_data,
                    'positions': positions,
                    'position_count': len(positions)
                }

        except Exception as e:
            self.logger.error(f"Error getting trading performance: {e}")
            return {'error': str(e)}

    def _get_agent_performance(self) -> Dict[str, Any]:
        """Get agent performance metrics"""
        try:
            with self.db.get_session() as session:
                # Get recent agent performance
                query = text("""
                    SELECT
                        agent_name,
                        total_signals,
                        profitable_signals,
                        avg_return,
                        sharpe_ratio,
                        win_rate,
                        date
                    FROM agent_performance
                    WHERE date >= CURRENT_DATE - INTERVAL '7 days'
                    ORDER BY date DESC, sharpe_ratio DESC NULLS LAST
                """)

                results = session.execute(query).fetchall()

                by_agent = {}
                for row in results:
                    agent_name = row[0]
                    if agent_name not in by_agent:
                        by_agent[agent_name] = []

                    by_agent[agent_name].append({
                        'total_signals': row[1],
                        'profitable_signals': row[2],
                        'avg_return': float(row[3]) if row[3] else 0,
                        'sharpe_ratio': float(row[4]) if row[4] else 0,
                        'win_rate': float(row[5]) if row[5] else 0,
                        'date': row[6].isoformat()
                    })

                # Calculate summary stats
                summary = {}
                for agent_name, performance in by_agent.items():
                    if performance:
                        summary[agent_name] = {
                            'avg_sharpe': sum(p['sharpe_ratio'] for p in performance) / len(performance),
                            'avg_win_rate': sum(p['win_rate'] for p in performance) / len(performance),
                            'total_signals': sum(p['total_signals'] for p in performance),
                            'days_tracked': len(performance)
                        }

                return {
                    'by_agent': by_agent,
                    'summary': summary
                }

        except Exception as e:
            self.logger.error(f"Error getting agent performance: {e}")
            return {'error': str(e)}

    def _get_system_metrics(self) -> Dict[str, Any]:
        """Get system health and performance metrics"""
        try:
            with self.db.get_session() as session:
                # Get recent system metrics
                query = text("""
                    SELECT
                        metric_name,
                        value,
                        unit,
                        time
                    FROM system_metrics
                    WHERE time >= NOW() - INTERVAL '2 hours'
                    ORDER BY time DESC
                """)

                results = session.execute(query).fetchall()

                metrics = {}
                for row in results:
                    metric_name = row[0]
                    if metric_name not in metrics:
                        metrics[metric_name] = []

                    metrics[metric_name].append({
                        'value': float(row[1]),
                        'type': row[2],
                        'timestamp': row[3].isoformat()
                    })

                # Calculate averages
                averages = {}
                for metric_name, values in metrics.items():
                    averages[metric_name] = {
                        'avg': sum(v['value'] for v in values) / len(values),
                        'min': min(v['value'] for v in values),
                        'max': max(v['value'] for v in values),
                        'count': len(values)
                    }

                return {
                    'metrics': metrics,
                    'averages': averages
                }

        except Exception as e:
            self.logger.error(f"Error getting system metrics: {e}")
            return {'error': str(e)}

    def _get_completed_improvements(self) -> Dict[str, Any]:
        """Get recently completed improvements"""
        try:
            with self.db.get_session() as session:
                # Get improvements completed in last 24 hours
                query = text("""
                    SELECT
                        title,
                        description,
                        expected_impact,
                        suggestion_type,
                        implemented_at
                    FROM improvement_suggestions
                    WHERE status = 'implemented'
                    AND implemented_at >= NOW() - INTERVAL '24 hours'
                    ORDER BY implemented_at DESC
                    LIMIT 10
                """)

                results = session.execute(query).fetchall()

                improvements = []
                for row in results:
                    improvements.append({
                        'title': row[0],
                        'description': row[1],
                        'impact': row[2],
                        'type': row[3],
                        'completed_at': row[4].isoformat() if row[4] else None
                    })

                return {
                    'recent_improvements': improvements,
                    'total_count': len(improvements)
                }

        except Exception as e:
            self.logger.error(f"Error getting completed improvements: {e}")
            return {'recent_improvements': [], 'total_count': 0}

    def _generate_recommendations(
        self,
        tasks: Dict[str, Any],
        agent_work: Dict[str, Any],
        trading_performance: Dict[str, Any],
        agent_performance: Dict[str, Any],
        system_metrics: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """Generate improvement recommendations from database (pending suggestions)"""
        recommendations = {
            'architecture': [],
            'security': [],
            'performance': [],
            'trading': []
        }

        try:
            # Query pending recommendations from database
            with self.db.get_session() as session:
                query = text("""
                    SELECT
                        suggestion_type,
                        title,
                        description,
                        priority
                    FROM improvement_suggestions
                    WHERE status = 'pending'
                    ORDER BY
                        CASE priority
                            WHEN 'high' THEN 1
                            WHEN 'medium' THEN 2
                            WHEN 'low' THEN 3
                            ELSE 4
                        END,
                        created_at DESC
                    LIMIT 20
                """)

                results = session.execute(query).fetchall()

                # Group recommendations by type
                for row in results:
                    suggestion_type = row[0]
                    title = row[1]
                    description = row[2]
                    priority = row[3]

                    # Create recommendation text
                    rec_text = f"[{priority.upper()}] {title}"
                    if description:
                        rec_text += f" - {description}"

                    # Add to appropriate category
                    if suggestion_type in recommendations:
                        recommendations[suggestion_type].append(rec_text)
                    else:
                        # Default to architecture if type not recognized
                        recommendations['architecture'].append(rec_text)

                self.logger.info(f"Loaded {len(results)} pending recommendations from database")

        except Exception as e:
            self.logger.error(f"Error loading recommendations from database: {e}")
            # Fallback: Add system-generated recommendations based on current state
            self._add_dynamic_recommendations(
                recommendations,
                trading_performance,
                agent_performance,
                system_metrics
            )

        # If no database recommendations, generate dynamic ones
        if sum(len(v) for v in recommendations.values()) == 0:
            self._add_dynamic_recommendations(
                recommendations,
                trading_performance,
                agent_performance,
                system_metrics
            )

        return recommendations

    def _add_dynamic_recommendations(
        self,
        recommendations: Dict[str, List[str]],
        trading_performance: Dict[str, Any],
        agent_performance: Dict[str, Any],
        system_metrics: Dict[str, Any]
    ):
        """Add dynamic recommendations based on current system state"""

        # Trading recommendations based on current performance
        portfolio = trading_performance.get('portfolio', {})
        if portfolio.get('total_pnl', 0) < -100:  # More than $100 loss
            recommendations['trading'].append(
                f"[HIGH] Portfolio showing significant negative P&L (${portfolio.get('total_pnl', 0):.2f}). "
                "Review agent weights and consider reducing position sizes."
            )

        positions = trading_performance.get('positions', [])
        if len(positions) == 0 and portfolio.get('cash_balance', 0) > 9000:
            recommendations['trading'].append(
                "[MEDIUM] No open positions despite available capital. "
                "Review signal generation thresholds."
            )

        # Agent performance recommendations
        agent_summary = agent_performance.get('summary', {})
        if agent_summary:
            low_performers = [
                name for name, stats in agent_summary.items()
                if stats.get('avg_sharpe', 0) < 0.3
            ]
            if low_performers:
                recommendations['performance'].append(
                    f"[HIGH] Low-performing agents detected: {', '.join(low_performers)}. "
                    "Consider adjusting weights or implementing new strategies."
                )

        # System monitoring
        if not system_metrics.get('metrics'):
            recommendations['performance'].append(
                "[MEDIUM] System metrics collection appears limited. "
                "Consider enhancing monitoring coverage."
            )

        self.logger.info("Generated dynamic recommendations based on current system state")

    def _generate_report(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive project report"""
        report_time = datetime.now(timezone.utc)

        report = {
            'report_type': 'status',
            'report_period': f'{self.report_interval_hours}h',
            'generated_at': report_time.isoformat(),
            'summary': self._format_summary(data),
            'trading_performance': data['trading_performance'],
            'agent_performance': data['agent_performance'],
            'tasks': data['tasks_summary'],
            'agent_work': data['agent_work_summary'],
            'system_metrics': data['system_metrics'],
            'recommendations': data['recommendations']
        }

        return report

    def _format_summary(self, data: Dict[str, Any]) -> str:
        """Format a text summary for the report"""
        lines = []
        lines.append("=== PROJECT STATUS REPORT ===\n")

        # Trading Performance
        portfolio = data['trading_performance'].get('portfolio', {})
        if portfolio:
            lines.append(f"Portfolio Value: ${portfolio.get('total_value', 0):,.2f}")
            lines.append(f"Total P&L: ${portfolio.get('total_pnl', 0):,.2f}")
            lines.append(f"Unrealized P&L: ${portfolio.get('unrealized_pnl', 0):,.2f}")

        positions = data['trading_performance'].get('positions', [])
        lines.append(f"Open Positions: {len(positions)}\n")

        # Tasks
        tasks = data['tasks_summary']
        lines.append(f"Active Tasks: {tasks.get('total_active', 0)}")

        # Agent Activity
        agent_work = data['agent_work_summary']
        lines.append(f"Active Agents: {agent_work.get('total_agents_active', 0)}\n")

        # Top Recommendations
        recs = data['recommendations']
        if any(recs.values()):
            lines.append("Top Recommendations:")
            for category, items in recs.items():
                if items:
                    lines.append(f"  [{category.upper()}] {items[0]}")

        return '\n'.join(lines)

    def _save_report(self, report: Dict[str, Any]):
        """Save report to database"""
        try:
            with self.db.get_session() as session:
                query = text("""
                    INSERT INTO project_reports (
                        report_type,
                        report_period,
                        generated_at,
                        report_data,
                        summary,
                        recommendations
                    ) VALUES (
                        :report_type,
                        :report_period,
                        :generated_at,
                        :report_data,
                        :summary,
                        :recommendations
                    )
                    RETURNING id
                """)

                result = session.execute(query, {
                    'report_type': report['report_type'],
                    'report_period': report['report_period'],
                    'generated_at': report['generated_at'],
                    'report_data': json.dumps(report),
                    'summary': report.get('summary', ''),
                    'recommendations': json.dumps(report['recommendations'])
                })

                report_id = result.fetchone()[0]
                session.commit()

                self.logger.info(f"Report saved: {report_id}")

        except Exception as e:
            self.logger.error(f"Error saving report: {e}")

    def _send_email_report(self, report: Dict[str, Any]) -> bool:
        """Send report via email"""
        try:
            recipient = self.email_config.get('recipient_email')
            if not recipient:
                self.logger.warning("No recipient email configured")
                return False

            # Create email
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"Trading System Report - {report['generated_at'][:16]}"
            msg['From'] = self.email_config.get('smtp_user', 'trading.system@example.com')
            msg['To'] = recipient

            # Create text and HTML versions
            text_body = self._format_email_text(report)
            html_body = self._format_email_html(report)

            msg.attach(MIMEText(text_body, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))

            # Send email
            smtp_server = self.email_config.get('smtp_server', 'smtp.gmail.com')
            smtp_port = int(self.email_config.get('smtp_port', 587))
            smtp_user = self.email_config.get('smtp_user')
            smtp_password = self.email_config.get('smtp_password', '')

            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                if smtp_password:
                    server.login(smtp_user, smtp_password)
                server.send_message(msg)

            self.logger.info(f"Email report sent to {recipient}")

            # Update database
            self._mark_report_sent(report)

            return True

        except Exception as e:
            self.logger.error(f"Error sending email: {e}")
            return False

    def _format_email_text(self, report: Dict[str, Any]) -> str:
        """Format plain text email body"""
        text = f"Trading System Status Report\n"
        text += f"Generated: {report['generated_at']}\n\n"

        # Trading Performance
        text += "=" * 60 + "\n"
        text += "TRADING PERFORMANCE\n"
        text += "=" * 60 + "\n"
        portfolio = report['trading_performance'].get('portfolio', {})
        if portfolio:
            text += f"Portfolio Value: ${portfolio.get('total_value', 0):,.2f}\n"
            text += f"Total P&L: ${portfolio.get('total_pnl', 0):,.2f} ({portfolio.get('total_pnl_pct', 0):.2f}%)\n"
            text += f"Open Positions: {len(report['trading_performance'].get('positions', []))}\n"

        # Add positions detail
        positions = report['trading_performance'].get('positions', [])
        if positions:
            text += "\nCurrent Positions:\n"
            for pos in positions:
                text += f"  • {pos.get('symbol')}: {pos.get('quantity', 0):.2f} @ ${pos.get('entry_price', 0):.2f}\n"
        text += "\n"

        # Agent Activity
        text += "=" * 60 + "\n"
        text += "AGENT ACTIVITY (Last 15 minutes)\n"
        text += "=" * 60 + "\n"
        agent_work = report.get('agent_work', {})
        agents_active = agent_work.get('total_agents_active', 0)
        text += f"Active Agents: {agents_active}\n\n"

        by_agent = agent_work.get('by_agent', {})
        if by_agent:
            for agent_name, agent_data in by_agent.items():
                text += f"► {agent_name}\n"
                last_activity = agent_data.get('last_activity', 'N/A')
                if last_activity != 'N/A':
                    text += f"  Last Active: {last_activity[:16]}\n"

                actions = agent_data.get('actions', [])
                if actions:
                    for action in actions:
                        action_type = action.get('action', 'unknown')
                        count = action.get('count', 0)
                        text += f"  - {action_type}: {count} times\n"
                text += "\n"
        else:
            text += "No agent activity in the last 15 minutes.\n\n"

        # Agent Performance
        agent_perf = report.get('agent_performance', {})
        if agent_perf.get('by_agent'):
            text += "Recent Agent Performance:\n"
            for agent_name, perf in agent_perf['by_agent'].items():
                text += f"  • {agent_name}: Sharpe {perf.get('sharpe_ratio', 0):.2f}, "
                text += f"Win Rate {perf.get('win_rate', 0):.1f}%, "
                text += f"Signals {perf.get('total_signals', 0)}\n"
            text += "\n"

        # Completed Improvements (PROMINENT)
        improvements = report.get('completed_improvements', {})
        recent = improvements.get('recent_improvements', [])

        if recent:
            text += "=" * 60 + "\n"
            text += "✓ RECENTLY COMPLETED IMPROVEMENTS (Last 24h)\n"
            text += "=" * 60 + "\n"
            for imp in recent:
                text += f"\n[{imp['type'].upper()}] {imp['title']}\n"
                text += f"  Description: {imp['description']}\n"
                text += f"  Impact: {imp['impact']}\n"
                text += f"  Completed: {imp['completed_at'][:16]}\n"
            text += f"\n>> Total Improvements Delivered: {improvements['total_count']} <<\n\n"

        # Next Recommendations
        text += "=" * 60 + "\n"
        text += "NEXT RECOMMENDATIONS\n"
        text += "=" * 60 + "\n"
        for category, items in report['recommendations'].items():
            if items:
                text += f"\n{category.upper()}:\n"
                for item in items:
                    text += f"  • {item}\n"

        return text

    def _format_email_html(self, report: Dict[str, Any]) -> str:
        """Format HTML email body"""
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .section {{ margin: 20px 0; }}
                .metric {{ margin: 10px 0; }}
                .positive {{ color: green; }}
                .negative {{ color: red; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #4CAF50; color: white; }}
            </style>
        </head>
        <body>
            <h1>Trading System Status Report</h1>
            <p><strong>Generated:</strong> {report['generated_at']}</p>

            <div class="section">
                <h2>Trading Performance</h2>
        """

        portfolio = report['trading_performance'].get('portfolio', {})
        if portfolio:
            pnl_class = 'positive' if portfolio.get('total_pnl', 0) >= 0 else 'negative'
            html += f"""
                <div class="metric">Portfolio Value: <strong>${portfolio.get('total_value', 0):,.2f}</strong></div>
                <div class="metric">Total P&L: <strong class="{pnl_class}">${portfolio.get('total_pnl', 0):,.2f}</strong></div>
                <div class="metric">Open Positions: <strong>{len(report['trading_performance'].get('positions', []))}</strong></div>
            """

            # Add positions detail
            positions = report['trading_performance'].get('positions', [])
            if positions:
                html += """
                <h3>Current Positions:</h3>
                <table>
                    <tr><th>Symbol</th><th>Quantity</th><th>Entry Price</th><th>Current Price</th></tr>
                """
                for pos in positions:
                    html += f"""
                    <tr>
                        <td>{pos.get('symbol', 'N/A')}</td>
                        <td>{pos.get('quantity', 0):.2f}</td>
                        <td>${pos.get('entry_price', 0):.2f}</td>
                        <td>${pos.get('current_price', 0):.2f}</td>
                    </tr>
                    """
                html += """
                </table>
                """

        html += """
            </div>
        """

        # Agent Activity Section
        html += """
            <div class="section" style="background-color: #e3f2fd; padding: 15px; border-left: 4px solid #2196F3;">
                <h2 style="color: #1565c0;">🤖 Agent Activity (Last 15 minutes)</h2>
        """

        agent_work = report.get('agent_work', {})
        agents_active = agent_work.get('total_agents_active', 0)
        html += f"<p><strong>Active Agents: {agents_active}</strong></p>"

        by_agent = agent_work.get('by_agent', {})
        if by_agent:
            for agent_name, agent_data in by_agent.items():
                html += f"""
                <div style="margin: 10px 0; padding: 10px; background-color: white; border-radius: 4px;">
                    <strong style="color: #1565c0;">► {agent_name}</strong><br/>
                """

                last_activity = agent_data.get('last_activity', 'N/A')
                if last_activity != 'N/A':
                    html += f"<em>Last Active:</em> {last_activity[:16]}<br/>"

                actions = agent_data.get('actions', [])
                if actions:
                    html += "<em>Actions:</em><ul style='margin: 5px 0;'>"
                    for action in actions:
                        action_type = action.get('action', 'unknown')
                        count = action.get('count', 0)
                        html += f"<li>{action_type}: {count} times</li>"
                    html += "</ul>"

                html += "</div>"
        else:
            html += "<p>No agent activity in the last 15 minutes.</p>"

        # Agent Performance
        agent_perf = report.get('agent_performance', {})
        if agent_perf.get('by_agent'):
            html += """
                <h3>Recent Agent Performance:</h3>
                <table>
                    <tr><th>Agent</th><th>Sharpe Ratio</th><th>Win Rate</th><th>Total Signals</th></tr>
            """
            for agent_name, perf in agent_perf['by_agent'].items():
                html += f"""
                <tr>
                    <td>{agent_name}</td>
                    <td>{perf.get('sharpe_ratio', 0):.2f}</td>
                    <td>{perf.get('win_rate', 0):.1f}%</td>
                    <td>{perf.get('total_signals', 0)}</td>
                </tr>
                """
            html += "</table>"

        html += """
            </div>
        """

        # Add Completed Improvements section (FIRST and PROMINENT)
        improvements = report.get('completed_improvements', {})
        recent = improvements.get('recent_improvements', [])

        if recent:
            html += """
            <div class="section" style="background-color: #e8f5e9; padding: 15px; border-left: 4px solid #4CAF50;">
                <h2 style="color: #2e7d32;">✓ Recently Completed Improvements (Last 24h)</h2>
            """
            for imp in recent:
                html += f"""
                <div style="margin: 10px 0; padding: 10px; background-color: white; border-radius: 4px;">
                    <strong style="color: #2e7d32;">[{imp['type'].upper()}] {imp['title']}</strong><br/>
                    <em>Description:</em> {imp['description']}<br/>
                    <em style="color: #1976d2;">Impact:</em> {imp['impact']}<br/>
                    <small>Completed: {imp['completed_at'][:16]}</small>
                </div>
                """
            html += f"""
                <p><strong>Total Improvements Delivered: {improvements['total_count']}</strong></p>
            </div>
            """

        html += """
            <div class="section">
                <h2>Next Recommendations</h2>
        """

        for category, items in report['recommendations'].items():
            if items:
                html += f"<h3>{category.title()}</h3><ul>"
                for item in items:
                    html += f"<li>{item}</li>"
                html += "</ul>"

        html += """
            </div>
        </body>
        </html>
        """

        return html

    def _mark_report_sent(self, report: Dict[str, Any]):
        """Mark report as sent in database"""
        try:
            with self.db.get_session() as session:
                query = text("""
                    UPDATE project_reports
                    SET sent_to_email = true,
                        email_sent_at = :sent_at
                    WHERE generated_at = :generated_at
                """)

                session.execute(query, {
                    'sent_at': datetime.now(timezone.utc),
                    'generated_at': report['generated_at']
                })
                session.commit()

        except Exception as e:
            self.logger.warning(f"Could not mark report as sent: {e}")


if __name__ == "__main__":
    # Test the agent
    import logging
    logging.basicConfig(level=logging.INFO)

    agent = ProjectManagerAgent()
    result = agent.execute()

    print(json.dumps(result, indent=2, default=str))

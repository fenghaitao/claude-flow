"""
Performance Dashboards and Alerting for Claude-Flow.

Provides dashboard generation, alerting rules, and notification
systems for comprehensive monitoring and operations.
"""

import asyncio
import json
import time
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart

from ..core.interfaces import BaseComponent


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertState(Enum):
    """Alert states."""
    ACTIVE = "active"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


@dataclass
class Alert:
    """Alert definition and state."""
    name: str
    description: str
    severity: AlertSeverity
    condition: str
    value: float
    threshold: float
    state: AlertState = AlertState.ACTIVE
    timestamp: float = field(default_factory=time.time)
    resolved_timestamp: Optional[float] = None
    suppressed_until: Optional[float] = None
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "severity": self.severity.value,
            "condition": self.condition,
            "value": self.value,
            "threshold": self.threshold,
            "state": self.state.value,
            "timestamp": self.timestamp,
            "resolved_timestamp": self.resolved_timestamp,
            "suppressed_until": self.suppressed_until,
            "labels": self.labels,
            "annotations": self.annotations
        }


@dataclass
class AlertRule:
    """Alert rule configuration."""
    name: str
    description: str
    condition: str  # PromQL-like expression
    threshold: float
    severity: AlertSeverity
    duration: float = 60.0  # seconds
    evaluation_interval: float = 15.0  # seconds
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True


@dataclass
class Dashboard:
    """Dashboard configuration."""
    name: str
    title: str
    description: str
    panels: List[Dict[str, Any]] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    refresh_interval: str = "30s"
    time_range: str = "1h"
    
    def add_panel(self, panel_config: Dict[str, Any]) -> None:
        """Add panel to dashboard."""
        self.panels.append(panel_config)
    
    def to_grafana_json(self) -> Dict[str, Any]:
        """Convert to Grafana dashboard JSON."""
        return {
            "dashboard": {
                "title": self.title,
                "description": self.description,
                "panels": self.panels,
                "templating": {
                    "list": list(self.variables.values())
                },
                "refresh": self.refresh_interval,
                "time": {
                    "from": f"now-{self.time_range}",
                    "to": "now"
                },
                "editable": True,
                "hideControls": False,
                "timezone": "browser"
            },
            "overwrite": True
        }


class AlertManager(BaseComponent):
    """Alert management and notification system."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__()
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Alert rules and state
        self.alert_rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        
        # Notification configuration
        self.notification_config = config.get("notifications", {})
        self.email_config = self.notification_config.get("email", {})
        self.webhook_config = self.notification_config.get("webhook", {})
        
        # Component references
        self.metrics = None
        self.health_monitor = None
        
        # Background tasks
        self._evaluation_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def initialize(self) -> None:
        """Initialize alert manager."""
        await super().initialize()
        
        # Register default alert rules
        self._register_default_alert_rules()
        
        # Start alert evaluation
        self._evaluation_task = asyncio.create_task(self._evaluate_alerts())
        
        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_alerts())
        
        self.logger.info("Alert manager initialized")
    
    async def shutdown(self) -> None:
        """Shutdown alert manager."""
        if self._evaluation_task:
            self._evaluation_task.cancel()
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
        
        try:
            if self._evaluation_task:
                await self._evaluation_task
            if self._cleanup_task:
                await self._cleanup_task
        except asyncio.CancelledError:
            pass
        
        await super().shutdown()
        self.logger.info("Alert manager shutdown")
    
    def register_component(self, name: str, component: Any) -> None:
        """Register system component for monitoring."""
        setattr(self, name, component)
    
    def add_alert_rule(self, rule: AlertRule) -> None:
        """Add alert rule."""
        self.alert_rules[rule.name] = rule
        self.logger.debug(f"Added alert rule: {rule.name}")
    
    def remove_alert_rule(self, rule_name: str) -> None:
        """Remove alert rule."""
        if rule_name in self.alert_rules:
            del self.alert_rules[rule_name]
            self.logger.debug(f"Removed alert rule: {rule_name}")
    
    def _register_default_alert_rules(self) -> None:
        """Register default alert rules."""
        default_rules = [
            AlertRule(
                name="high_memory_usage",
                description="High memory usage detected",
                condition="memory_usage_percent > threshold",
                threshold=85.0,
                severity=AlertSeverity.WARNING,
                duration=300.0,  # 5 minutes
                labels={"component": "system"},
                annotations={"summary": "Memory usage is above 85%"}
            ),
            AlertRule(
                name="high_cpu_usage",
                description="High CPU usage detected",
                condition="cpu_usage_percent > threshold",
                threshold=80.0,
                severity=AlertSeverity.WARNING,
                duration=300.0,
                labels={"component": "system"},
                annotations={"summary": "CPU usage is above 80%"}
            ),
            AlertRule(
                name="claude_api_errors",
                description="High Claude API error rate",
                condition="claude_error_rate > threshold",
                threshold=0.1,  # 10%
                severity=AlertSeverity.CRITICAL,
                duration=120.0,
                labels={"component": "claude"},
                annotations={"summary": "Claude API error rate above 10%"}
            ),
            AlertRule(
                name="agent_failures",
                description="High agent task failure rate",
                condition="agent_failure_rate > threshold",
                threshold=0.2,  # 20%
                severity=AlertSeverity.WARNING,
                duration=180.0,
                labels={"component": "agents"},
                annotations={"summary": "Agent task failure rate above 20%"}
            ),
            AlertRule(
                name="event_queue_backlog",
                description="Large event queue backlog",
                condition="event_queue_size > threshold",
                threshold=1000,
                severity=AlertSeverity.WARNING,
                duration=60.0,
                labels={"component": "events"},
                annotations={"summary": "Event queue has over 1000 pending events"}
            ),
            AlertRule(
                name="memory_storage_full",
                description="Memory storage approaching capacity",
                condition="memory_usage_ratio > threshold",
                threshold=0.9,  # 90%
                severity=AlertSeverity.CRITICAL,
                duration=60.0,
                labels={"component": "memory"},
                annotations={"summary": "Memory storage is over 90% full"}
            )
        ]
        
        for rule in default_rules:
            self.add_alert_rule(rule)
    
    async def _evaluate_alerts(self) -> None:
        """Continuously evaluate alert rules."""
        while True:
            try:
                for rule_name, rule in self.alert_rules.items():
                    if rule.enabled:
                        await self._evaluate_rule(rule)
                
                await asyncio.sleep(min(rule.evaluation_interval for rule in self.alert_rules.values()) or 15.0)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error evaluating alerts: {e}")
                await asyncio.sleep(15.0)
    
    async def _evaluate_rule(self, rule: AlertRule) -> None:
        """Evaluate a single alert rule."""
        try:
            # Get current metric value
            value = await self._get_metric_value(rule.condition)
            
            if value is None:
                return
            
            # Check if threshold is exceeded
            threshold_exceeded = self._check_threshold(rule.condition, value, rule.threshold)
            
            existing_alert = self.active_alerts.get(rule.name)
            
            if threshold_exceeded:
                if existing_alert:
                    # Update existing alert
                    existing_alert.value = value
                    existing_alert.timestamp = time.time()
                else:
                    # Create new alert
                    alert = Alert(
                        name=rule.name,
                        description=rule.description,
                        severity=rule.severity,
                        condition=rule.condition,
                        value=value,
                        threshold=rule.threshold,
                        labels=rule.labels.copy(),
                        annotations=rule.annotations.copy()
                    )
                    
                    self.active_alerts[rule.name] = alert
                    self.alert_history.append(alert)
                    
                    # Send notification
                    await self._send_alert_notification(alert)
                    
                    self.logger.warning(f"Alert fired: {rule.name} (value: {value}, threshold: {rule.threshold})")
            
            elif existing_alert and existing_alert.state == AlertState.ACTIVE:
                # Resolve alert
                existing_alert.state = AlertState.RESOLVED
                existing_alert.resolved_timestamp = time.time()
                
                # Send resolution notification
                await self._send_alert_notification(existing_alert, resolved=True)
                
                # Remove from active alerts
                del self.active_alerts[rule.name]
                
                self.logger.info(f"Alert resolved: {rule.name}")
        
        except Exception as e:
            self.logger.error(f"Error evaluating rule {rule.name}: {e}")
    
    async def _get_metric_value(self, condition: str) -> Optional[float]:
        """Get current metric value for condition."""
        # Simplified metric extraction - in production would parse PromQL
        if not self.metrics:
            return None
        
        try:
            if "memory_usage_percent" in condition:
                import psutil
                return psutil.virtual_memory().percent
            elif "cpu_usage_percent" in condition:
                import psutil
                return psutil.cpu_percent(interval=0.1)
            elif "claude_error_rate" in condition:
                stats = self.metrics.get_metrics_summary()
                # Calculate error rate from Claude metrics
                return 0.05  # Placeholder
            elif "agent_failure_rate" in condition:
                # Get agent failure rate
                return 0.15  # Placeholder
            elif "event_queue_size" in condition:
                # Get event queue size
                return 500  # Placeholder
            elif "memory_usage_ratio" in condition:
                # Get memory storage usage ratio
                return 0.75  # Placeholder
            
        except Exception as e:
            self.logger.error(f"Error getting metric value for {condition}: {e}")
        
        return None
    
    def _check_threshold(self, condition: str, value: float, threshold: float) -> bool:
        """Check if value exceeds threshold based on condition."""
        if ">" in condition:
            return value > threshold
        elif "<" in condition:
            return value < threshold
        elif ">=" in condition:
            return value >= threshold
        elif "<=" in condition:
            return value <= threshold
        elif "==" in condition:
            return abs(value - threshold) < 0.001
        else:
            # Default to greater than
            return value > threshold
    
    async def _send_alert_notification(self, alert: Alert, resolved: bool = False) -> None:
        """Send alert notification."""
        try:
            # Email notification
            if self.email_config.get("enabled", False):
                await self._send_email_notification(alert, resolved)
            
            # Webhook notification
            if self.webhook_config.get("enabled", False):
                await self._send_webhook_notification(alert, resolved)
            
        except Exception as e:
            self.logger.error(f"Error sending alert notification: {e}")
    
    async def _send_email_notification(self, alert: Alert, resolved: bool = False) -> None:
        """Send email alert notification."""
        try:
            smtp_server = self.email_config.get("smtp_server")
            smtp_port = self.email_config.get("smtp_port", 587)
            username = self.email_config.get("username")
            password = self.email_config.get("password")
            from_email = self.email_config.get("from_email")
            to_emails = self.email_config.get("to_emails", [])
            
            if not all([smtp_server, username, password, from_email, to_emails]):
                self.logger.warning("Email configuration incomplete, skipping email notification")
                return
            
            # Create email
            subject = f"[{'RESOLVED' if resolved else alert.severity.value.upper()}] {alert.name}"
            
            body = f"""
Alert: {alert.name}
Status: {'RESOLVED' if resolved else 'ACTIVE'}
Severity: {alert.severity.value.upper()}
Description: {alert.description}

Condition: {alert.condition}
Current Value: {alert.value}
Threshold: {alert.threshold}

Timestamp: {datetime.fromtimestamp(alert.timestamp).isoformat()}
{f"Resolved: {datetime.fromtimestamp(alert.resolved_timestamp).isoformat()}" if resolved else ""}

Labels: {json.dumps(alert.labels, indent=2)}
Annotations: {json.dumps(alert.annotations, indent=2)}
"""
            
            # Send email
            msg = MimeMultipart()
            msg['From'] = from_email
            msg['Subject'] = subject
            msg.attach(MimeText(body, 'plain'))
            
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(username, password)
            
            for to_email in to_emails:
                msg['To'] = to_email
                server.send_message(msg)
                del msg['To']
            
            server.quit()
            
            self.logger.debug(f"Email notification sent for alert: {alert.name}")
            
        except Exception as e:
            self.logger.error(f"Error sending email notification: {e}")
    
    async def _send_webhook_notification(self, alert: Alert, resolved: bool = False) -> None:
        """Send webhook alert notification."""
        try:
            import httpx
            
            webhook_url = self.webhook_config.get("url")
            if not webhook_url:
                return
            
            payload = {
                "alert": alert.to_dict(),
                "resolved": resolved,
                "timestamp": time.time()
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=10.0
                )
                response.raise_for_status()
            
            self.logger.debug(f"Webhook notification sent for alert: {alert.name}")
            
        except Exception as e:
            self.logger.error(f"Error sending webhook notification: {e}")
    
    async def _cleanup_alerts(self) -> None:
        """Clean up old resolved alerts."""
        while True:
            try:
                # Clean up old alerts (keep last 1000)
                if len(self.alert_history) > 1000:
                    self.alert_history = self.alert_history[-1000:]
                
                # Remove suppressed alerts that have expired
                current_time = time.time()
                for alert_name, alert in list(self.active_alerts.items()):
                    if (alert.state == AlertState.SUPPRESSED and 
                        alert.suppressed_until and 
                        current_time > alert.suppressed_until):
                        alert.state = AlertState.ACTIVE
                
                await asyncio.sleep(3600)  # Run every hour
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in alert cleanup: {e}")
                await asyncio.sleep(3600)
    
    def suppress_alert(self, alert_name: str, duration_seconds: float) -> bool:
        """Suppress an alert for a specified duration."""
        alert = self.active_alerts.get(alert_name)
        if alert:
            alert.state = AlertState.SUPPRESSED
            alert.suppressed_until = time.time() + duration_seconds
            self.logger.info(f"Alert suppressed: {alert_name} for {duration_seconds} seconds")
            return True
        return False
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all active alerts."""
        return [alert.to_dict() for alert in self.active_alerts.values()]
    
    def get_alert_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get alert history."""
        return [alert.to_dict() for alert in self.alert_history[-limit:]]


class DashboardManager:
    """Dashboard management and generation."""
    
    def __init__(self):
        self.dashboards: Dict[str, Dashboard] = {}
        self.logger = logging.getLogger(__name__)
    
    def create_claude_flow_dashboard(self) -> Dashboard:
        """Create main Claude-Flow dashboard."""
        dashboard = Dashboard(
            name="claude-flow-overview",
            title="Claude-Flow System Overview",
            description="Comprehensive system monitoring dashboard"
        )
        
        # System metrics panel
        dashboard.add_panel({
            "title": "System Resources",
            "type": "graph",
            "targets": [
                {"expr": "claude_flow_cpu_usage_percent", "legendFormat": "CPU Usage %"},
                {"expr": "claude_flow_memory_usage_bytes{type='rss'}", "legendFormat": "Memory Usage"},
                {"expr": "claude_flow_uptime_seconds", "legendFormat": "Uptime"}
            ],
            "yAxes": [{"unit": "percent"}, {"unit": "bytes"}],
            "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0}
        })
        
        # Agent metrics panel
        dashboard.add_panel({
            "title": "Agent Activity",
            "type": "graph",
            "targets": [
                {"expr": "claude_flow_agents_total", "legendFormat": "Total Agents"},
                {"expr": "claude_flow_tasks_total", "legendFormat": "Tasks Processed"},
                {"expr": "claude_flow_agent_utilization_ratio", "legendFormat": "Agent Utilization"}
            ],
            "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0}
        })
        
        # Claude API metrics panel
        dashboard.add_panel({
            "title": "Claude API Performance",
            "type": "graph",
            "targets": [
                {"expr": "rate(claude_flow_claude_requests_total[5m])", "legendFormat": "Request Rate"},
                {"expr": "claude_flow_claude_request_duration_seconds", "legendFormat": "Response Time"},
                {"expr": "claude_flow_claude_tokens_total", "legendFormat": "Token Usage"}
            ],
            "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8}
        })
        
        # Event system panel
        dashboard.add_panel({
            "title": "Event System",
            "type": "graph",
            "targets": [
                {"expr": "claude_flow_event_queue_size", "legendFormat": "Queue Size"},
                {"expr": "rate(claude_flow_events_total[5m])", "legendFormat": "Event Rate"},
                {"expr": "claude_flow_event_processing_duration_seconds", "legendFormat": "Processing Time"}
            ],
            "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8}
        })
        
        # Memory system panel
        dashboard.add_panel({
            "title": "Memory System",
            "type": "graph",
            "targets": [
                {"expr": "claude_flow_memory_entries_total", "legendFormat": "Total Entries"},
                {"expr": "claude_flow_memory_size_bytes", "legendFormat": "Storage Size"},
                {"expr": "claude_flow_memory_search_duration_seconds", "legendFormat": "Search Time"}
            ],
            "gridPos": {"h": 8, "w": 24, "x": 0, "y": 16}
        })
        
        return dashboard
    
    def create_alerts_dashboard(self) -> Dashboard:
        """Create alerts dashboard."""
        dashboard = Dashboard(
            name="claude-flow-alerts",
            title="Claude-Flow Alerts",
            description="Alert monitoring and management"
        )
        
        # Active alerts panel
        dashboard.add_panel({
            "title": "Active Alerts",
            "type": "table",
            "targets": [
                {"expr": "ALERTS{alertstate='firing'}", "format": "table"}
            ],
            "gridPos": {"h": 8, "w": 24, "x": 0, "y": 0}
        })
        
        # Alert history panel
        dashboard.add_panel({
            "title": "Alert Frequency",
            "type": "graph",
            "targets": [
                {"expr": "increase(alertmanager_alerts_total[1h])", "legendFormat": "Alerts per Hour"}
            ],
            "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8}
        })
        
        return dashboard
    
    def export_dashboard_json(self, dashboard_name: str) -> Optional[str]:
        """Export dashboard as Grafana JSON."""
        dashboard = self.dashboards.get(dashboard_name)
        if dashboard:
            return json.dumps(dashboard.to_grafana_json(), indent=2)
        return None
    
    def register_dashboard(self, dashboard: Dashboard) -> None:
        """Register a dashboard."""
        self.dashboards[dashboard.name] = dashboard
        self.logger.debug(f"Registered dashboard: {dashboard.name}")
    
    def get_all_dashboards(self) -> Dict[str, Dashboard]:
        """Get all registered dashboards."""
        return self.dashboards.copy()
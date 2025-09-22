"""
Health Check and Monitoring Endpoints for Claude-Flow.

Provides comprehensive health monitoring, status reporting,
and diagnostic endpoints for system observability.
"""

import asyncio
import time
import json
import traceback
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging
from fastapi import FastAPI, Response, HTTPException, Depends
from fastapi.responses import JSONResponse, PlainTextResponse
import uvicorn

from ..core.interfaces import BaseComponent


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Individual health check result."""
    name: str
    status: HealthStatus
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp
        }


@dataclass
class SystemStatus:
    """Overall system status."""
    status: HealthStatus
    uptime_seconds: float
    version: str
    environment: str
    checks: List[HealthCheck] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status": self.status.value,
            "uptime_seconds": self.uptime_seconds,
            "version": self.version,
            "environment": self.environment,
            "checks": [check.to_dict() for check in self.checks],
            "metrics": self.metrics,
            "timestamp": self.timestamp
        }


class HealthMonitor(BaseComponent):
    """Health monitoring and endpoint management."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__()
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.host = config.get("host", "0.0.0.0")
        self.port = config.get("port", 8080)
        self.check_interval = config.get("check_interval", 30.0)  # seconds
        
        # System info
        self.start_time = time.time()
        self.version = config.get("version", "1.0.0")
        self.environment = config.get("environment", "development")
        
        # Health checks registry
        self.health_checks: Dict[str, Callable] = {}
        self.last_check_results: Dict[str, HealthCheck] = {}
        
        # Component references (set by system)
        self.claude_client = None
        self.event_bus = None
        self.memory_manager = None
        self.agent_orchestrator = None
        self.metrics = None
        
        # FastAPI app
        self.app = FastAPI(
            title="Claude-Flow Health Monitor",
            description="Health monitoring and status endpoints",
            version=self.version
        )
        self._setup_routes()
        
        # Background tasks
        self._health_check_task: Optional[asyncio.Task] = None
        self._server_task: Optional[asyncio.Task] = None
    
    async def initialize(self) -> None:
        """Initialize health monitoring."""
        await super().initialize()
        
        # Register default health checks
        self._register_default_checks()
        
        # Start background health checking
        self._health_check_task = asyncio.create_task(self._periodic_health_check())
        
        # Start HTTP server
        self._server_task = asyncio.create_task(self._run_server())
        
        self.logger.info(f"Health monitor started on {self.host}:{self.port}")
    
    async def shutdown(self) -> None:
        """Shutdown health monitoring."""
        if self._health_check_task:
            self._health_check_task.cancel()
        
        if self._server_task:
            self._server_task.cancel()
        
        try:
            if self._health_check_task:
                await self._health_check_task
            if self._server_task:
                await self._server_task
        except asyncio.CancelledError:
            pass
        
        await super().shutdown()
        self.logger.info("Health monitor shutdown")
    
    def register_component(self, name: str, component: Any) -> None:
        """Register a system component for monitoring."""
        setattr(self, name, component)
        self.logger.debug(f"Registered component: {name}")
    
    def register_health_check(self, name: str, check_func: Callable) -> None:
        """Register a custom health check."""
        self.health_checks[name] = check_func
        self.logger.debug(f"Registered health check: {name}")
    
    def _register_default_checks(self) -> None:
        """Register default system health checks."""
        self.register_health_check("system", self._check_system_health)
        self.register_health_check("claude_client", self._check_claude_client)
        self.register_health_check("event_bus", self._check_event_bus)
        self.register_health_check("memory_manager", self._check_memory_manager)
        self.register_health_check("agent_orchestrator", self._check_agent_orchestrator)
    
    async def _periodic_health_check(self) -> None:
        """Periodically run health checks."""
        while True:
            try:
                await self.run_health_checks()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in periodic health check: {e}")
                await asyncio.sleep(self.check_interval)
    
    async def run_health_checks(self) -> SystemStatus:
        """Run all registered health checks."""
        checks = []
        overall_status = HealthStatus.HEALTHY
        
        for name, check_func in self.health_checks.items():
            try:
                start_time = time.time()
                
                if asyncio.iscoroutinefunction(check_func):
                    result = await check_func()
                else:
                    result = check_func()
                
                duration_ms = (time.time() - start_time) * 1000
                
                # Ensure result is a HealthCheck object
                if not isinstance(result, HealthCheck):
                    result = HealthCheck(
                        name=name,
                        status=HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY,
                        message=str(result) if result else "Check failed",
                        duration_ms=duration_ms
                    )
                else:
                    result.duration_ms = duration_ms
                
                checks.append(result)
                self.last_check_results[name] = result
                
                # Update overall status
                if result.status == HealthStatus.UNHEALTHY:
                    overall_status = HealthStatus.UNHEALTHY
                elif result.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                    overall_status = HealthStatus.DEGRADED
                
            except Exception as e:
                error_check = HealthCheck(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Health check failed: {str(e)}",
                    details={"error": str(e), "traceback": traceback.format_exc()}
                )
                checks.append(error_check)
                self.last_check_results[name] = error_check
                overall_status = HealthStatus.UNHEALTHY
                
                self.logger.error(f"Health check '{name}' failed: {e}")
        
        # Get system metrics if available
        metrics = {}
        if self.metrics:
            try:
                metrics = self.metrics.get_metrics_summary()
            except Exception as e:
                self.logger.warning(f"Failed to get metrics: {e}")
        
        system_status = SystemStatus(
            status=overall_status,
            uptime_seconds=time.time() - self.start_time,
            version=self.version,
            environment=self.environment,
            checks=checks,
            metrics=metrics
        )
        
        return system_status
    
    # Default health check implementations
    async def _check_system_health(self) -> HealthCheck:
        """Check basic system health."""
        try:
            import psutil
            
            # Check memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Check CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # Check disk usage
            disk = psutil.disk_usage('.')
            disk_percent = (disk.used / disk.total) * 100
            
            details = {
                "memory_percent": memory_percent,
                "cpu_percent": cpu_percent,
                "disk_percent": disk_percent,
                "uptime_seconds": time.time() - self.start_time
            }
            
            # Determine status based on resource usage
            if memory_percent > 90 or cpu_percent > 90 or disk_percent > 95:
                status = HealthStatus.UNHEALTHY
                message = "High resource usage detected"
            elif memory_percent > 80 or cpu_percent > 80 or disk_percent > 90:
                status = HealthStatus.DEGRADED
                message = "Elevated resource usage"
            else:
                status = HealthStatus.HEALTHY
                message = "System resources normal"
            
            return HealthCheck(
                name="system",
                status=status,
                message=message,
                details=details
            )
            
        except ImportError:
            return HealthCheck(
                name="system",
                status=HealthStatus.UNKNOWN,
                message="psutil not available for system monitoring"
            )
        except Exception as e:
            return HealthCheck(
                name="system",
                status=HealthStatus.UNHEALTHY,
                message=f"System check failed: {str(e)}"
            )
    
    async def _check_claude_client(self) -> HealthCheck:
        """Check Claude client health."""
        if not self.claude_client:
            return HealthCheck(
                name="claude_client",
                status=HealthStatus.UNKNOWN,
                message="Claude client not available"
            )
        
        try:
            # Check client status
            health = await self.claude_client.health_check()
            
            if health.get("status") == "healthy":
                status = HealthStatus.HEALTHY
                message = "Claude client operational"
            else:
                status = HealthStatus.DEGRADED
                message = health.get("error", "Claude client issues detected")
            
            return HealthCheck(
                name="claude_client",
                status=status,
                message=message,
                details=health
            )
            
        except Exception as e:
            return HealthCheck(
                name="claude_client",
                status=HealthStatus.UNHEALTHY,
                message=f"Claude client check failed: {str(e)}"
            )
    
    async def _check_event_bus(self) -> HealthCheck:
        """Check event bus health."""
        if not self.event_bus:
            return HealthCheck(
                name="event_bus",
                status=HealthStatus.UNKNOWN,
                message="Event bus not available"
            )
        
        try:
            stats = await self.event_bus.get_stats()
            
            queue_size = stats.get("queue_size", 0)
            error_rate = stats.get("error_rate", 0)
            
            if error_rate > 0.1:  # More than 10% error rate
                status = HealthStatus.UNHEALTHY
                message = f"High event error rate: {error_rate:.1%}"
            elif queue_size > 1000:  # Large queue backlog
                status = HealthStatus.DEGRADED
                message = f"Large event queue: {queue_size} events"
            else:
                status = HealthStatus.HEALTHY
                message = "Event bus operational"
            
            return HealthCheck(
                name="event_bus",
                status=status,
                message=message,
                details=stats
            )
            
        except Exception as e:
            return HealthCheck(
                name="event_bus",
                status=HealthStatus.UNHEALTHY,
                message=f"Event bus check failed: {str(e)}"
            )
    
    async def _check_memory_manager(self) -> HealthCheck:
        """Check memory manager health."""
        if not self.memory_manager:
            return HealthCheck(
                name="memory_manager",
                status=HealthStatus.UNKNOWN,
                message="Memory manager not available"
            )
        
        try:
            health = await self.memory_manager.health_check()
            
            status_map = {
                "healthy": HealthStatus.HEALTHY,
                "degraded": HealthStatus.DEGRADED,
                "unhealthy": HealthStatus.UNHEALTHY
            }
            
            status = status_map.get(health.get("status"), HealthStatus.UNKNOWN)
            message = health.get("message", "Memory manager status unknown")
            
            return HealthCheck(
                name="memory_manager",
                status=status,
                message=message,
                details=health
            )
            
        except Exception as e:
            return HealthCheck(
                name="memory_manager",
                status=HealthStatus.UNHEALTHY,
                message=f"Memory manager check failed: {str(e)}"
            )
    
    async def _check_agent_orchestrator(self) -> HealthCheck:
        """Check agent orchestrator health."""
        if not self.agent_orchestrator:
            return HealthCheck(
                name="agent_orchestrator",
                status=HealthStatus.UNKNOWN,
                message="Agent orchestrator not available"
            )
        
        try:
            stats = await self.agent_orchestrator.get_stats()
            
            active_agents = stats.get("active_agents", 0)
            failed_tasks = stats.get("failed_tasks", 0)
            total_tasks = stats.get("total_tasks", 1)
            
            failure_rate = failed_tasks / total_tasks if total_tasks > 0 else 0
            
            if failure_rate > 0.2:  # More than 20% failure rate
                status = HealthStatus.UNHEALTHY
                message = f"High task failure rate: {failure_rate:.1%}"
            elif active_agents == 0:
                status = HealthStatus.DEGRADED
                message = "No active agents"
            else:
                status = HealthStatus.HEALTHY
                message = f"Orchestrator operational with {active_agents} agents"
            
            return HealthCheck(
                name="agent_orchestrator",
                status=status,
                message=message,
                details=stats
            )
            
        except Exception as e:
            return HealthCheck(
                name="agent_orchestrator",
                status=HealthStatus.UNHEALTHY,
                message=f"Agent orchestrator check failed: {str(e)}"
            )
    
    def _setup_routes(self) -> None:
        """Setup FastAPI routes."""
        
        @self.app.get("/health", response_class=JSONResponse)
        async def health_endpoint():
            """Basic health check endpoint."""
            system_status = await self.run_health_checks()
            
            status_code = 200
            if system_status.status == HealthStatus.DEGRADED:
                status_code = 200  # Still return 200 for degraded
            elif system_status.status == HealthStatus.UNHEALTHY:
                status_code = 503  # Service unavailable
            
            return JSONResponse(
                content=system_status.to_dict(),
                status_code=status_code
            )
        
        @self.app.get("/health/live", response_class=PlainTextResponse)
        async def liveness_probe():
            """Kubernetes liveness probe."""
            return PlainTextResponse("OK", status_code=200)
        
        @self.app.get("/health/ready", response_class=JSONResponse)
        async def readiness_probe():
            """Kubernetes readiness probe."""
            system_status = await self.run_health_checks()
            
            if system_status.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]:
                return JSONResponse({"status": "ready"}, status_code=200)
            else:
                return JSONResponse({"status": "not ready"}, status_code=503)
        
        @self.app.get("/status", response_class=JSONResponse)
        async def status_endpoint():
            """Detailed status information."""
            system_status = await self.run_health_checks()
            return JSONResponse(content=system_status.to_dict())
        
        @self.app.get("/metrics/summary", response_class=JSONResponse)
        async def metrics_summary():
            """Metrics summary endpoint."""
            if not self.metrics:
                raise HTTPException(status_code=404, detail="Metrics not available")
            
            try:
                summary = self.metrics.get_metrics_summary()
                return JSONResponse(content=summary)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")
        
        @self.app.get("/info", response_class=JSONResponse)
        async def info_endpoint():
            """System information endpoint."""
            return JSONResponse(content={
                "name": "Claude-Flow",
                "version": self.version,
                "environment": self.environment,
                "uptime_seconds": time.time() - self.start_time,
                "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
                "current_time": datetime.now().isoformat()
            })
        
        @self.app.get("/debug", response_class=JSONResponse)
        async def debug_endpoint():
            """Debug information endpoint."""
            debug_info = {
                "last_health_checks": {
                    name: check.to_dict() 
                    for name, check in self.last_check_results.items()
                },
                "registered_checks": list(self.health_checks.keys()),
                "config": {
                    "host": self.host,
                    "port": self.port,
                    "check_interval": self.check_interval
                }
            }
            
            # Add component status
            components = {}
            for attr_name in ["claude_client", "event_bus", "memory_manager", "agent_orchestrator", "metrics"]:
                component = getattr(self, attr_name, None)
                components[attr_name] = {
                    "available": component is not None,
                    "type": type(component).__name__ if component else None
                }
            
            debug_info["components"] = components
            
            return JSONResponse(content=debug_info)
    
    async def _run_server(self) -> None:
        """Run the FastAPI server."""
        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        
        try:
            await server.serve()
        except asyncio.CancelledError:
            pass
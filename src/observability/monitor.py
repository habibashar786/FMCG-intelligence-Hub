"""
Observability System
Implements logging, tracing, and metrics collection
Using OpenTelemetry, Prometheus, and structured logging
"""
import time
import structlog
from typing import Any, Dict, Optional, Callable
from functools import wraps
from datetime import datetime
from contextlib import contextmanager

from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.resources import Resource
from prometheus_client import Counter, Histogram, Gauge, start_http_server

from config.settings import get_settings


settings = get_settings()


# ============================================================================
# STRUCTURED LOGGING
# ============================================================================

def setup_logging():
    """Configure structured logging with structlog"""
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if settings.log_format == "json" 
            else structlog.dev.ConsoleRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str):
    """Get a structured logger instance"""
    return structlog.get_logger(name)


# ============================================================================
# DISTRIBUTED TRACING
# ============================================================================

class TracingManager:
    """Manages distributed tracing with OpenTelemetry"""
    
    def __init__(self):
        self.settings = get_settings()
        self._setup_tracing()
        self.tracer = trace.get_tracer(__name__)
        self.logger = get_logger(__name__)
    
    def _setup_tracing(self):
        """Setup OpenTelemetry tracing"""
        if not self.settings.enable_tracing:
            return
        
        # Create resource
        resource = Resource.create({
            "service.name": self.settings.app_name,
            "service.version": self.settings.app_version,
            "environment": self.settings.environment
        })
        
        # Create tracer provider
        tracer_provider = TracerProvider(resource=resource)
        
        # Add OTLP exporter
        if self.settings.otlp_endpoint:
            otlp_exporter = OTLPSpanExporter(
                endpoint=self.settings.otlp_endpoint,
                insecure=True  # Use secure=True in production
            )
            span_processor = BatchSpanProcessor(otlp_exporter)
            tracer_provider.add_span_processor(span_processor)
        
        # Set global tracer provider
        trace.set_tracer_provider(tracer_provider)
    
    @contextmanager
    def start_span(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None
    ):
        """Start a new trace span"""
        with self.tracer.start_as_current_span(name) as span:
            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(key, str(value))
            
            self.logger.info(
                "span_started",
                span_name=name,
                trace_id=format(span.get_span_context().trace_id, '032x')
            )
            
            try:
                yield span
            except Exception as e:
                span.set_status(trace.Status(trace.StatusCode.ERROR))
                span.record_exception(e)
                self.logger.error(
                    "span_error",
                    span_name=name,
                    error=str(e)
                )
                raise
            finally:
                self.logger.info(
                    "span_completed",
                    span_name=name
                )
    
    def trace_async(self, span_name: Optional[str] = None):
        """Decorator for tracing async functions"""
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                name = span_name or f"{func.__module__}.{func.__name__}"
                with self.start_span(name, {"function": func.__name__}):
                    return await func(*args, **kwargs)
            return wrapper
        return decorator
    
    def trace_sync(self, span_name: Optional[str] = None):
        """Decorator for tracing sync functions"""
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                name = span_name or f"{func.__module__}.{func.__name__}"
                with self.start_span(name, {"function": func.__name__}):
                    return func(*args, **kwargs)
            return wrapper
        return decorator


# ============================================================================
# METRICS COLLECTION
# ============================================================================

class MetricsCollector:
    """Collects and exports metrics using Prometheus"""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = get_logger(__name__)
        self._setup_metrics()
        self._define_metrics()
    
    def _setup_metrics(self):
        """Setup Prometheus metrics collection"""
        if not self.settings.enable_metrics:
            return
        
        # Create resource
        resource = Resource.create({
            "service.name": self.settings.app_name,
            "service.version": self.settings.app_version,
        })
        
        # Create Prometheus metric reader
        prometheus_reader = PrometheusMetricReader()
        
        # Create meter provider
        meter_provider = MeterProvider(
            resource=resource,
            metric_readers=[prometheus_reader]
        )
        
        # Set global meter provider
        metrics.set_meter_provider(meter_provider)
        
        # Start Prometheus HTTP server
        if self.settings.prometheus_port:
            start_http_server(self.settings.prometheus_port)
            self.logger.info(
                "prometheus_server_started",
                port=self.settings.prometheus_port
            )
    
    def _define_metrics(self):
        """Define Prometheus metrics"""
        # Request metrics
        self.request_counter = Counter(
            'agent_requests_total',
            'Total number of agent requests',
            ['agent_type', 'status']
        )
        
        self.request_duration = Histogram(
            'agent_request_duration_seconds',
            'Request duration in seconds',
            ['agent_type'],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
        )
        
        # Agent metrics
        self.active_agents = Gauge(
            'agent_active_count',
            'Number of currently active agents',
            ['agent_type']
        )
        
        self.agent_errors = Counter(
            'agent_errors_total',
            'Total number of agent errors',
            ['agent_type', 'error_type']
        )
        
        # Tool metrics
        self.tool_calls = Counter(
            'tool_calls_total',
            'Total number of tool calls',
            ['tool_name', 'status']
        )
        
        self.tool_duration = Histogram(
            'tool_execution_duration_seconds',
            'Tool execution duration',
            ['tool_name']
        )
        
        # Memory metrics
        self.memory_size = Gauge(
            'memory_bank_size',
            'Number of items in memory bank'
        )
        
        self.session_count = Gauge(
            'active_sessions_count',
            'Number of active sessions'
        )
        
        # Quality metrics
        self.quality_score = Histogram(
            'agent_quality_score',
            'Agent output quality score',
            ['agent_type'],
            buckets=[0.0, 0.5, 0.7, 0.8, 0.9, 0.95, 1.0]
        )
    
    def record_request(
        self,
        agent_type: str,
        status: str,
        duration: float
    ):
        """Record agent request metrics"""
        self.request_counter.labels(
            agent_type=agent_type,
            status=status
        ).inc()
        
        self.request_duration.labels(
            agent_type=agent_type
        ).observe(duration)
    
    def record_tool_call(
        self,
        tool_name: str,
        status: str,
        duration: float
    ):
        """Record tool execution metrics"""
        self.tool_calls.labels(
            tool_name=tool_name,
            status=status
        ).inc()
        
        self.tool_duration.labels(
            tool_name=tool_name
        ).observe(duration)
    
    def record_error(self, agent_type: str, error_type: str):
        """Record agent error"""
        self.agent_errors.labels(
            agent_type=agent_type,
            error_type=error_type
        ).inc()
    
    def update_active_agents(self, agent_type: str, count: int):
        """Update active agent count"""
        self.active_agents.labels(agent_type=agent_type).set(count)
    
    def record_quality_score(self, agent_type: str, score: float):
        """Record quality score"""
        self.quality_score.labels(agent_type=agent_type).observe(score)


# ============================================================================
# AGENT MONITOR
# ============================================================================

class AgentMonitor:
    """
    Comprehensive agent monitoring
    Combines logging, tracing, and metrics
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.tracing = TracingManager()
        self.metrics = MetricsCollector()
    
    @contextmanager
    def monitor_execution(
        self,
        agent_type: str,
        task: str,
        session_id: str
    ):
        """Monitor agent execution with all observability features"""
        start_time = time.time()
        
        # Start logging context
        self.logger.info(
            "agent_execution_started",
            agent_type=agent_type,
            task=task[:100],  # Truncate long tasks
            session_id=session_id
        )
        
        # Start tracing
        with self.tracing.start_span(
            f"agent.{agent_type}.execute",
            attributes={
                "agent.type": agent_type,
                "session.id": session_id
            }
        ) as span:
            try:
                # Update active agents metric
                self.metrics.update_active_agents(agent_type, 1)
                
                yield {
                    "span": span,
                    "logger": self.logger,
                    "start_time": start_time
                }
                
                # Success metrics
                duration = time.time() - start_time
                self.metrics.record_request(agent_type, "success", duration)
                
                self.logger.info(
                    "agent_execution_completed",
                    agent_type=agent_type,
                    session_id=session_id,
                    duration=duration
                )
                
            except Exception as e:
                # Error handling
                duration = time.time() - start_time
                self.metrics.record_request(agent_type, "error", duration)
                self.metrics.record_error(agent_type, type(e).__name__)
                
                self.logger.error(
                    "agent_execution_failed",
                    agent_type=agent_type,
                    session_id=session_id,
                    error=str(e),
                    duration=duration,
                    exc_info=True
                )
                
                span.set_status(trace.Status(trace.StatusCode.ERROR))
                span.record_exception(e)
                
                raise
            
            finally:
                # Update active agents
                self.metrics.update_active_agents(agent_type, 0)
    
    def log_tool_execution(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        result: Any,
        duration: float,
        success: bool
    ):
        """Log tool execution"""
        self.logger.info(
            "tool_executed",
            tool_name=tool_name,
            parameters=parameters,
            duration=duration,
            success=success
        )
        
        self.metrics.record_tool_call(
            tool_name,
            "success" if success else "error",
            duration
        )
    
    def log_memory_operation(
        self,
        operation: str,
        details: Dict[str, Any]
    ):
        """Log memory operations"""
        self.logger.info(
            "memory_operation",
            operation=operation,
            **details
        )
    
    def record_agent_quality(
        self,
        agent_type: str,
        quality_score: float,
        metrics: Dict[str, Any]
    ):
        """Record agent quality metrics"""
        self.logger.info(
            "agent_quality_recorded",
            agent_type=agent_type,
            quality_score=quality_score,
            metrics=metrics
        )
        
        self.metrics.record_quality_score(agent_type, quality_score)
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get system health status"""
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "tracing_enabled": settings.enable_tracing,
            "metrics_enabled": settings.enable_metrics,
            "logging_configured": True
        }


# ============================================================================
# GLOBAL INSTANCES
# ============================================================================

# Setup logging on import
setup_logging()

# Create global monitor instance
agent_monitor = AgentMonitor()


# ============================================================================
# UTILITY DECORATORS
# ============================================================================

def monitor_async(agent_type: str):
    """Decorator to monitor async agent methods"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(self, task: str, context, **kwargs):
            with agent_monitor.monitor_execution(
                agent_type=agent_type,
                task=task,
                session_id=context.session_id
            ):
                return await func(self, task, context, **kwargs)
        return wrapper
    return decorator


def monitor_tool(tool_name: str):
    """Decorator to monitor tool execution"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                agent_monitor.log_tool_execution(
                    tool_name=tool_name,
                    parameters=kwargs,
                    result=result,
                    duration=duration,
                    success=True
                )
                
                return result
            except Exception as e:
                duration = time.time() - start_time
                agent_monitor.log_tool_execution(
                    tool_name=tool_name,
                    parameters=kwargs,
                    result=None,
                    duration=duration,
                    success=False
                )
                raise
        return wrapper
    return decorator

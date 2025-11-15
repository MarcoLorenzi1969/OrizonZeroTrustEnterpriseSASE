"""
Orizon Zero Trust Connect - Prometheus Metrics
For: Marco @ Syneto/Orizon

Prometheus metrics collection and export for monitoring
"""

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Info,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST
)
from functools import wraps
import time
from typing import Callable
from loguru import logger

# Create custom registry
registry = CollectorRegistry()

# ============================================================================
# COUNTERS (monotonically increasing)
# ============================================================================

# Tunnel metrics
tunnels_created_total = Counter(
    'orizon_tunnels_created_total',
    'Total number of tunnels created',
    ['tunnel_type'],  # ssh, https
    registry=registry
)

tunnels_failed_total = Counter(
    'orizon_tunnels_failed_total',
    'Total number of tunnel creation failures',
    ['tunnel_type', 'reason'],
    registry=registry
)

tunnel_reconnects_total = Counter(
    'orizon_tunnel_reconnects_total',
    'Total number of tunnel reconnection attempts',
    ['tunnel_id', 'success'],
    registry=registry
)

# API request metrics
api_requests_total = Counter(
    'orizon_api_requests_total',
    'Total number of API requests',
    ['method', 'endpoint', 'status'],
    registry=registry
)

api_errors_total = Counter(
    'orizon_api_errors_total',
    'Total number of API errors',
    ['endpoint', 'error_type'],
    registry=registry
)

# Authentication metrics
auth_login_attempts_total = Counter(
    'orizon_auth_login_attempts_total',
    'Total number of login attempts',
    ['success', 'method'],  # password, 2fa
    registry=registry
)

auth_login_failures_total = Counter(
    'orizon_auth_login_failures_total',
    'Total number of failed login attempts',
    ['reason'],  # invalid_password, invalid_2fa, user_not_found
    registry=registry
)

auth_token_issued_total = Counter(
    'orizon_auth_token_issued_total',
    'Total number of JWT tokens issued',
    ['token_type'],  # access, refresh
    registry=registry
)

# ACL metrics
acl_rules_created_total = Counter(
    'orizon_acl_rules_created_total',
    'Total number of ACL rules created',
    ['action'],  # allow, deny
    registry=registry
)

acl_rules_deleted_total = Counter(
    'orizon_acl_rules_deleted_total',
    'Total number of ACL rules deleted',
    registry=registry
)

acl_access_checks_total = Counter(
    'orizon_acl_access_checks_total',
    'Total number of ACL access checks',
    ['result'],  # allow, deny
    registry=registry
)

# Node metrics
nodes_registered_total = Counter(
    'orizon_nodes_registered_total',
    'Total number of nodes registered',
    ['node_type'],
    registry=registry
)

nodes_disconnected_total = Counter(
    'orizon_nodes_disconnected_total',
    'Total number of node disconnections',
    ['reason'],
    registry=registry
)

# WebSocket metrics
websocket_connections_total = Counter(
    'orizon_websocket_connections_total',
    'Total number of WebSocket connections',
    registry=registry
)

websocket_disconnections_total = Counter(
    'orizon_websocket_disconnections_total',
    'Total number of WebSocket disconnections',
    ['reason'],
    registry=registry
)

websocket_messages_sent_total = Counter(
    'orizon_websocket_messages_sent_total',
    'Total number of WebSocket messages sent',
    ['message_type'],
    registry=registry
)

websocket_messages_received_total = Counter(
    'orizon_websocket_messages_received_total',
    'Total number of WebSocket messages received',
    ['message_type'],
    registry=registry
)

# Audit metrics
audit_logs_created_total = Counter(
    'orizon_audit_logs_created_total',
    'Total number of audit logs created',
    ['action', 'severity'],
    registry=registry
)

# ============================================================================
# GAUGES (can go up and down)
# ============================================================================

# Tunnel gauges
active_tunnels = Gauge(
    'orizon_active_tunnels',
    'Number of currently active tunnels',
    ['tunnel_type'],
    registry=registry
)

tunnel_health_status = Gauge(
    'orizon_tunnel_health_status',
    'Health status of tunnels (1=healthy, 0=unhealthy)',
    ['tunnel_id', 'node_id'],
    registry=registry
)

# Node gauges
connected_nodes = Gauge(
    'orizon_connected_nodes',
    'Number of currently connected nodes',
    ['status'],  # online, offline, error
    registry=registry
)

node_cpu_usage = Gauge(
    'orizon_node_cpu_usage_percent',
    'CPU usage percentage of nodes',
    ['node_id', 'node_name'],
    registry=registry
)

node_memory_usage = Gauge(
    'orizon_node_memory_usage_percent',
    'Memory usage percentage of nodes',
    ['node_id', 'node_name'],
    registry=registry
)

node_disk_usage = Gauge(
    'orizon_node_disk_usage_percent',
    'Disk usage percentage of nodes',
    ['node_id', 'node_name'],
    registry=registry
)

# User gauges
active_users = Gauge(
    'orizon_active_users',
    'Number of currently active users',
    ['role'],
    registry=registry
)

active_sessions = Gauge(
    'orizon_active_sessions',
    'Number of active user sessions',
    registry=registry
)

# WebSocket gauges
active_websocket_connections = Gauge(
    'orizon_active_websocket_connections',
    'Number of active WebSocket connections',
    registry=registry
)

# ACL gauges
acl_rules_count = Gauge(
    'orizon_acl_rules_count',
    'Total number of ACL rules',
    ['action', 'is_active'],
    registry=registry
)

# System gauges
database_connections = Gauge(
    'orizon_database_connections',
    'Number of active database connections',
    ['database'],  # postgresql, mongodb, redis
    registry=registry
)

# ============================================================================
# HISTOGRAMS (distributions)
# ============================================================================

# API latency
api_request_duration_seconds = Histogram(
    'orizon_api_request_duration_seconds',
    'API request duration in seconds',
    ['method', 'endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=registry
)

# Tunnel latency
tunnel_latency_seconds = Histogram(
    'orizon_tunnel_latency_seconds',
    'Tunnel latency in seconds',
    ['tunnel_id', 'tunnel_type'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0],
    registry=registry
)

# Database query latency
database_query_duration_seconds = Histogram(
    'orizon_database_query_duration_seconds',
    'Database query duration in seconds',
    ['operation', 'database'],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
    registry=registry
)

# WebSocket message latency
websocket_message_duration_seconds = Histogram(
    'orizon_websocket_message_duration_seconds',
    'WebSocket message processing duration in seconds',
    ['message_type'],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
    registry=registry
)

# ============================================================================
# INFO (static information)
# ============================================================================

app_info = Info(
    'orizon_app',
    'Application information',
    registry=registry
)

# ============================================================================
# METRIC UPDATE HELPERS
# ============================================================================

class MetricsCollector:
    """Helper class for updating metrics"""

    @staticmethod
    def record_tunnel_created(tunnel_type: str):
        """Record tunnel creation"""
        tunnels_created_total.labels(tunnel_type=tunnel_type).inc()
        logger.debug(f"📊 Metric: tunnel_created (type={tunnel_type})")

    @staticmethod
    def record_tunnel_failed(tunnel_type: str, reason: str):
        """Record tunnel failure"""
        tunnels_failed_total.labels(tunnel_type=tunnel_type, reason=reason).inc()
        logger.debug(f"📊 Metric: tunnel_failed (type={tunnel_type}, reason={reason})")

    @staticmethod
    def update_active_tunnels(tunnel_type: str, count: int):
        """Update active tunnel count"""
        active_tunnels.labels(tunnel_type=tunnel_type).set(count)
        logger.debug(f"📊 Metric: active_tunnels={count} (type={tunnel_type})")

    @staticmethod
    def record_api_request(method: str, endpoint: str, status: int, duration: float):
        """Record API request"""
        api_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status=str(status)
        ).inc()

        api_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)

        logger.debug(f"📊 Metric: api_request ({method} {endpoint} {status} {duration:.3f}s)")

    @staticmethod
    def record_login_attempt(success: bool, method: str = "password"):
        """Record login attempt"""
        auth_login_attempts_total.labels(
            success=str(success).lower(),
            method=method
        ).inc()
        logger.debug(f"📊 Metric: login_attempt (success={success}, method={method})")

    @staticmethod
    def record_acl_rule_created(action: str):
        """Record ACL rule creation"""
        acl_rules_created_total.labels(action=action).inc()
        logger.debug(f"📊 Metric: acl_rule_created (action={action})")

    @staticmethod
    def record_acl_access_check(result: str):
        """Record ACL access check"""
        acl_access_checks_total.labels(result=result).inc()
        logger.debug(f"📊 Metric: acl_access_check (result={result})")

    @staticmethod
    def update_connected_nodes(status: str, count: int):
        """Update connected nodes count"""
        connected_nodes.labels(status=status).set(count)
        logger.debug(f"📊 Metric: connected_nodes={count} (status={status})")

    @staticmethod
    def update_node_metrics(node_id: str, node_name: str, cpu: float, memory: float, disk: float):
        """Update node resource metrics"""
        node_cpu_usage.labels(node_id=node_id, node_name=node_name).set(cpu)
        node_memory_usage.labels(node_id=node_id, node_name=node_name).set(memory)
        node_disk_usage.labels(node_id=node_id, node_name=node_name).set(disk)
        logger.debug(
            f"📊 Metric: node_metrics (node={node_name}, "
            f"cpu={cpu}%, mem={memory}%, disk={disk}%)"
        )

    @staticmethod
    def update_active_websockets(count: int):
        """Update active WebSocket connections"""
        active_websocket_connections.set(count)
        logger.debug(f"📊 Metric: active_websockets={count}")

    @staticmethod
    def record_audit_log(action: str, severity: str):
        """Record audit log creation"""
        audit_logs_created_total.labels(action=action, severity=severity).inc()
        logger.debug(f"📊 Metric: audit_log_created (action={action}, severity={severity})")

    @staticmethod
    def set_app_info(version: str, environment: str):
        """Set application info"""
        app_info.info({
            'version': version,
            'environment': environment,
            'name': 'Orizon Zero Trust Connect'
        })
        logger.info(f"📊 Metric: app_info set (version={version}, env={environment})")


# ============================================================================
# DECORATORS FOR AUTOMATIC METRIC COLLECTION
# ============================================================================

def track_api_request(endpoint: str):
    """
    Decorator to automatically track API request metrics

    Usage:
        @track_api_request("/api/v1/users")
        async def get_users():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time

                # Record successful request
                MetricsCollector.record_api_request(
                    method="GET",  # TODO: Get actual method from request
                    endpoint=endpoint,
                    status=200,
                    duration=duration
                )

                return result

            except Exception as e:
                duration = time.time() - start_time

                # Record failed request
                MetricsCollector.record_api_request(
                    method="GET",
                    endpoint=endpoint,
                    status=500,
                    duration=duration
                )

                raise

        return wrapper
    return decorator


def track_database_query(operation: str, database: str = "postgresql"):
    """
    Decorator to track database query duration

    Usage:
        @track_database_query("select", "postgresql")
        async def get_user(db, user_id):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time

                database_query_duration_seconds.labels(
                    operation=operation,
                    database=database
                ).observe(duration)

                return result

            except Exception as e:
                duration = time.time() - start_time

                database_query_duration_seconds.labels(
                    operation=operation,
                    database=database
                ).observe(duration)

                raise

        return wrapper
    return decorator


# ============================================================================
# METRICS EXPORT
# ============================================================================

def get_metrics() -> tuple[bytes, str]:
    """
    Generate Prometheus metrics in text format

    Returns:
        Tuple of (metrics_data, content_type)
    """
    metrics_data = generate_latest(registry)
    return metrics_data, CONTENT_TYPE_LATEST


# Initialize metrics collector
metrics_collector = MetricsCollector()

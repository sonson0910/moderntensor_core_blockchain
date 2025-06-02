from prometheus_client import Counter, Gauge, Histogram, Summary
import time

# Network metrics
TASK_SEND_TOTAL = Counter(
    'validator_task_send_total',
    'Total number of tasks sent',
    ['status']  # success, failure
)

TASK_RECEIVE_TOTAL = Counter(
    'validator_task_receive_total',
    'Total number of tasks received',
    ['status']  # success, timeout, invalid
)

NETWORK_LATENCY = Histogram(
    'validator_network_latency_seconds',
    'Network request latency in seconds',
    ['operation']  # task_send, task_receive
)

# Consensus metrics
CONSENSUS_CYCLE_DURATION = Histogram(
    'validator_consensus_cycle_duration_seconds',
    'Duration of consensus cycles in seconds'
)

ACTIVE_MINERS = Gauge(
    'validator_active_miners',
    'Number of active miners in the network'
)

ACTIVE_VALIDATORS = Gauge(
    'validator_active_validators',
    'Number of active validators in the network'
)

# Performance metrics
TASK_PROCESSING_TIME = Summary(
    'validator_task_processing_seconds',
    'Time spent processing tasks',
    ['operation']  # scoring, validation
)

MEMORY_USAGE = Gauge(
    'validator_memory_usage_bytes',
    'Memory usage of the validator node'
)

# Error metrics
ERROR_COUNTER = Counter(
    'validator_errors_total',
    'Total number of errors',
    ['type']  # network, consensus, validation
)

class MetricsCollector:
    def __init__(self):
        self.start_time = time.time()
        self.cycle_start_time = None

    def record_task_send(self, success: bool):
        """Record task send attempt"""
        TASK_SEND_TOTAL.labels(status='success' if success else 'failure').inc()

    def record_task_receive(self, status: str):
        """Record task receive attempt"""
        TASK_RECEIVE_TOTAL.labels(status=status).inc()

    def record_network_latency(self, operation: str, duration: float):
        """Record network operation latency"""
        NETWORK_LATENCY.labels(operation=operation).observe(duration)

    def start_consensus_cycle(self):
        """Start timing a consensus cycle"""
        self.cycle_start_time = time.time()

    def end_consensus_cycle(self):
        """End timing a consensus cycle"""
        if self.cycle_start_time:
            duration = time.time() - self.cycle_start_time
            CONSENSUS_CYCLE_DURATION.observe(duration)
            self.cycle_start_time = None

    def update_active_nodes(self, miners_count: int, validators_count: int):
        """Update active node counts"""
        ACTIVE_MINERS.set(miners_count)
        ACTIVE_VALIDATORS.set(validators_count)

    def record_task_processing(self, operation: str, duration: float):
        """Record task processing time"""
        TASK_PROCESSING_TIME.labels(operation=operation).observe(duration)

    def record_error(self, error_type: str):
        """Record an error occurrence"""
        ERROR_COUNTER.labels(type=error_type).inc()

    def update_memory_usage(self, bytes_used: int):
        """Update memory usage metric"""
        MEMORY_USAGE.set(bytes_used)

# Create a singleton instance
metrics = MetricsCollector() 
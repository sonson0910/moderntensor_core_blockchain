"""
Metrics module for ModernTensor with proper Prometheus registry management.
"""
import time
from typing import Dict, Optional
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, REGISTRY
from prometheus_client.core import CollectorRegistry as CoreCollectorRegistry
import threading

class MetricsManager:
    """Singleton metrics manager that handles Prometheus registry properly."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        self._initialized = True
        self._registry = None
        self._metrics = {}
        self._setup_metrics()
    
    def _setup_metrics(self):
        """Setup metrics with proper registry management."""
        # Create a new registry to avoid conflicts
        self._registry = CollectorRegistry()
        
        # Define metrics
        self._metrics = {
            'consensus_rounds_total': Counter(
                'consensus_rounds_total',
                'Total number of consensus rounds',
                registry=self._registry
            ),
            'consensus_duration_seconds': Histogram(
                'consensus_duration_seconds',
                'Duration of consensus rounds in seconds',
                registry=self._registry
            ),
            'blockchain_submissions_total': Counter(
                'blockchain_submissions_total',
                'Total number of blockchain submissions',
                ['status'],
                registry=self._registry
            ),
            'tasks_sent_total': Counter(
                'tasks_sent_total',
                'Total number of tasks sent to miners',
                ['status'],
                registry=self._registry
            ),
            'tasks_received_total': Counter(
                'tasks_received_total',
                'Total number of task results received',
                registry=self._registry
            ),
            'p2p_messages_total': Counter(
                'p2p_messages_total',
                'Total number of P2P messages',
                ['type', 'status'],
                registry=self._registry
            ),
            'active_miners': Gauge(
                'active_miners',
                'Number of active miners',
                registry=self._registry
            ),
            'active_validators': Gauge(
                'active_validators',
                'Number of active validators',
                registry=self._registry
            ),
            'miner_scores': Gauge(
                'miner_scores',
                'Current miner scores',
                ['miner_address'],
                registry=self._registry
            ),
            'validator_stakes': Gauge(
                'validator_stakes',
                'Current validator stakes',
                ['validator_address'],
                registry=self._registry
            ),
            'transaction_success_rate': Gauge(
                'transaction_success_rate',
                'Success rate of transactions',
                registry=self._registry
            ),
            'network_latency_seconds': Histogram(
                'network_latency_seconds',
                'Network latency in seconds',
                registry=self._registry
            ),
            'memory_usage_bytes': Gauge(
                'memory_usage_bytes',
                'Memory usage in bytes',
                registry=self._registry
            ),
            'cpu_usage_percent': Gauge(
                'cpu_usage_percent',
                'CPU usage percentage',
                registry=self._registry
            )
        }
    
    def get_metric(self, name: str):
        """Get a metric by name."""
        return self._metrics.get(name)
    
    def get_registry(self):
        """Get the metrics registry."""
        return self._registry
    
    def reset_metrics(self):
        """Reset all metrics - useful for testing."""
        with self._lock:
            self._setup_metrics()
    
    def record_consensus_round(self, duration: float):
        """Record a consensus round."""
        self._metrics['consensus_rounds_total'].inc()
        self._metrics['consensus_duration_seconds'].observe(duration)
    
    def record_blockchain_submission(self, success: bool):
        """Record a blockchain submission."""
        status = 'success' if success else 'failure'
        self._metrics['blockchain_submissions_total'].labels(status=status).inc()
    
    def update_active_miners(self, count: int):
        """Update active miners count."""
        self._metrics['active_miners'].set(count)
    
    def update_active_validators(self, count: int):
        """Update active validators count."""
        self._metrics['active_validators'].set(count)
    
    def update_miner_score(self, miner_address: str, score: float):
        """Update miner score."""
        self._metrics['miner_scores'].labels(miner_address=miner_address).set(score)
    
    def update_validator_stake(self, validator_address: str, stake: float):
        """Update validator stake."""
        self._metrics['validator_stakes'].labels(validator_address=validator_address).set(stake)
    
    def update_transaction_success_rate(self, rate: float):
        """Update transaction success rate."""
        self._metrics['transaction_success_rate'].set(rate)
    
    def record_network_latency(self, latency: float):
        """Record network latency."""
        self._metrics['network_latency_seconds'].observe(latency)
    
    def update_memory_usage(self, memory_bytes: int):
        """Update memory usage."""
        self._metrics['memory_usage_bytes'].set(memory_bytes)
    
    def update_cpu_usage(self, cpu_percent: float):
        """Update CPU usage."""
        self._metrics['cpu_usage_percent'].set(cpu_percent)
    
    def record_task_send(self, success: bool):
        """Record a task send attempt."""
        status = 'success' if success else 'failure'
        self._metrics['tasks_sent_total'].labels(status=status).inc()
    
    def record_task_received(self):
        """Record a task result received."""
        self._metrics['tasks_received_total'].inc()
    
    def record_p2p_message(self, message_type: str, success: bool):
        """Record a P2P message."""
        status = 'success' if success else 'failure'
        self._metrics['p2p_messages_total'].labels(type=message_type, status=status).inc()
    
    def record_error(self, error_type: str = "general"):
        """Record an error occurrence."""
        # For now, just log it. Could add error metrics later if needed
        pass
    
    def update_active_nodes(self, count: int):
        """Update active nodes count - alias for active_validators."""
        self.update_active_validators(count)
    
    def increment_counter(self, name: str, labels: Optional[Dict] = None):
        """Increment a counter metric."""
        if name in self._metrics:
            metric = self._metrics[name]
            if labels:
                metric.labels(**labels).inc()
            else:
                metric.inc()
    
    def set_gauge(self, name: str, value: float, labels: Optional[Dict] = None):
        """Set a gauge metric value."""
        if name in self._metrics:
            metric = self._metrics[name]
            if labels:
                metric.labels(**labels).set(value)
            else:
                metric.set(value)
    
    def observe_histogram(self, name: str, value: float, labels: Optional[Dict] = None):
        """Observe a histogram metric."""
        if name in self._metrics:
            metric = self._metrics[name]
            if labels:
                metric.labels(**labels).observe(value)
            else:
                metric.observe(value)

# Global instance
metrics_manager = MetricsManager()

# Convenience functions
def get_metrics_manager() -> MetricsManager:
    """Get the global metrics manager instance."""
    return metrics_manager

def reset_metrics():
    """Reset all metrics - useful for testing."""
    metrics_manager.reset_metrics()

def record_consensus_round(duration: float):
    """Record a consensus round."""
    metrics_manager.record_consensus_round(duration)

def record_blockchain_submission(success: bool):
    """Record a blockchain submission."""
    metrics_manager.record_blockchain_submission(success)

def update_active_miners(count: int):
    """Update active miners count."""
    metrics_manager.update_active_miners(count)

def update_active_validators(count: int):
    """Update active validators count."""
    metrics_manager.update_active_validators(count)

def update_miner_score(miner_address: str, score: float):
    """Update miner score."""
    metrics_manager.update_miner_score(miner_address, score)

def update_validator_stake(validator_address: str, stake: float):
    """Update validator stake."""
    metrics_manager.update_validator_stake(validator_address, stake)

def update_transaction_success_rate(rate: float):
    """Update transaction success rate."""
    metrics_manager.update_transaction_success_rate(rate)

def record_network_latency(latency: float):
    """Record network latency."""
    metrics_manager.record_network_latency(latency)

def update_memory_usage(memory_bytes: int):
    """Update memory usage."""
    metrics_manager.update_memory_usage(memory_bytes)

def update_cpu_usage(cpu_percent: float):
    """Update CPU usage."""
    metrics_manager.update_cpu_usage(cpu_percent) 
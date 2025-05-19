import pytest
from aptos_sdk.account import Account, AccountAddress
from aptos_sdk.client import RestClient
from aptos_sdk.transactions import EntryFunction, TransactionArgument
from aptos_sdk.type_tag import TypeTag, StructTag
import json
import time

@pytest.fixture
def aptos_client():
    """Create a test client for Aptos."""
    return RestClient("https://fullnode.testnet.aptoslabs.com")

@pytest.fixture
def validator_account():
    """Create a test validator account."""
    return Account.generate()

@pytest.mark.asyncio
async def test_node_health(aptos_client):
    """Test node health check functionality."""
    # Check node health
    health = await aptos_client.health_check()
    assert health is not None
    assert "status" in health
    assert health["status"] == "healthy"
    
    # Check node metrics
    metrics = await aptos_client.get_node_metrics()
    assert metrics is not None
    assert "version" in metrics
    assert "uptime" in metrics
    assert "peers" in metrics

@pytest.mark.asyncio
async def test_validator_health(aptos_client, validator_account):
    """Test validator health monitoring."""
    # Fund validator account
    await aptos_client.fund_account(validator_account.address(), 100_000_000)
    
    # Register validator
    payload = {
        "function": "0x1::validator::register_validator",
        "type_arguments": [],
        "arguments": [
            validator_account.public_key_bytes().hex(),
            "1000000",  # stake amount
            "0x1",  # consensus key
            "0x1",  # validator network address
            "0x1",  # fullnode network address
        ]
    }
    
    txn_hash = await aptos_client.submit_transaction(validator_account, payload)
    txn = await aptos_client.wait_for_transaction(txn_hash)
    assert txn["success"]
    
    # Check validator health
    validator_health = await aptos_client.get_validator_health(validator_account.address())
    assert validator_health is not None
    assert "status" in validator_health
    assert "last_heartbeat" in validator_health
    assert "voting_power" in validator_health

@pytest.mark.asyncio
async def test_network_health(aptos_client):
    """Test network health monitoring."""
    # Get network status
    network_status = await aptos_client.get_network_status()
    assert network_status is not None
    assert "chain_id" in network_status
    assert "ledger_version" in network_status
    assert "latest_block_height" in network_status
    
    # Get network metrics
    network_metrics = await aptos_client.get_network_metrics()
    assert network_metrics is not None
    assert "tps" in network_metrics
    assert "block_time" in network_metrics
    assert "active_validators" in network_metrics

@pytest.mark.asyncio
async def test_performance_metrics(aptos_client):
    """Test performance metrics collection."""
    # Get performance metrics
    performance = await aptos_client.get_performance_metrics()
    assert performance is not None
    assert "cpu_usage" in performance
    assert "memory_usage" in performance
    assert "disk_usage" in performance
    assert "network_io" in performance

@pytest.mark.asyncio
async def test_error_monitoring(aptos_client):
    """Test error monitoring and reporting."""
    # Get error logs
    error_logs = await aptos_client.get_error_logs()
    assert error_logs is not None
    assert isinstance(error_logs, list)
    
    # Get error statistics
    error_stats = await aptos_client.get_error_statistics()
    assert error_stats is not None
    assert "total_errors" in error_stats
    assert "error_types" in error_stats
    assert "error_timeline" in error_stats

@pytest.mark.asyncio
async def test_resource_monitoring(aptos_client):
    """Test resource monitoring."""
    # Get resource usage
    resources = await aptos_client.get_resource_usage()
    assert resources is not None
    assert "cpu" in resources
    assert "memory" in resources
    assert "disk" in resources
    assert "network" in resources
    
    # Get resource limits
    limits = await aptos_client.get_resource_limits()
    assert limits is not None
    assert "cpu_limit" in limits
    assert "memory_limit" in limits
    assert "disk_limit" in limits
    assert "network_limit" in limits

@pytest.mark.asyncio
async def test_alert_system(aptos_client):
    """Test alert system functionality."""
    # Set up alert
    alert_config = {
        "metric": "cpu_usage",
        "threshold": 80,
        "duration": 300,
        "severity": "high"
    }
    
    # Configure alert
    payload = {
        "function": "0x1::monitoring::configure_alert",
        "type_arguments": [],
        "arguments": [
            json.dumps(alert_config)
        ]
    }
    
    txn_hash = await aptos_client.submit_transaction(validator_account, payload)
    txn = await aptos_client.wait_for_transaction(txn_hash)
    assert txn["success"]
    
    # Get active alerts
    alerts = await aptos_client.get_active_alerts()
    assert alerts is not None
    assert isinstance(alerts, list)
    
    # Get alert history
    alert_history = await aptos_client.get_alert_history()
    assert alert_history is not None
    assert isinstance(alert_history, list)

@pytest.mark.asyncio
async def test_continuous_monitoring(aptos_client):
    """Test continuous monitoring functionality."""
    # Start monitoring
    monitoring_config = {
        "interval": 60,
        "metrics": ["cpu", "memory", "network"],
        "duration": 3600
    }
    
    # Configure monitoring
    payload = {
        "function": "0x1::monitoring::start_monitoring",
        "type_arguments": [],
        "arguments": [
            json.dumps(monitoring_config)
        ]
    }
    
    txn_hash = await aptos_client.submit_transaction(validator_account, payload)
    txn = await aptos_client.wait_for_transaction(txn_hash)
    assert txn["success"]
    
    # Wait for some data collection
    time.sleep(120)
    
    # Get monitoring data
    monitoring_data = await aptos_client.get_monitoring_data()
    assert monitoring_data is not None
    assert "metrics" in monitoring_data
    assert "timestamps" in monitoring_data
    assert "values" in monitoring_data 
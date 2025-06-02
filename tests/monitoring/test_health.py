import pytest
from fastapi.testclient import TestClient
from mt_aptos.monitoring.health import app
import psutil
import time

@pytest.fixture
def client():
    return TestClient(app)

def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    
    # Check response structure
    assert "status" in data
    assert "timestamp" in data
    assert "system" in data
    assert "network" in data
    assert "blockchain" in data
    assert "circuit_breaker" in data
    assert "rate_limiter" in data
    
    # Check system metrics
    system = data["system"]
    assert "cpu_percent" in system
    assert "memory_percent" in system
    assert "disk_percent" in system
    
    # Validate metric ranges
    assert 0 <= system["cpu_percent"] <= 100
    assert 0 <= system["memory_percent"] <= 100
    assert 0 <= system["disk_percent"] <= 100

def test_metrics_endpoint(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "HELP" in response.text
    assert "TYPE" in response.text

def test_ready_endpoint(client):
    response = client.get("/ready")
    assert response.status_code == 503  # Should fail without validator node
    
    # Mock validator node
    app.state.validator_node = type("MockNode", (), {
        "miners_info": {"test": "data"},
        "validators_info": {"test": "data"},
        "health_server": True
    })
    
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert all(data["checks"].values())

def test_live_endpoint(client):
    response = client.get("/live")
    assert response.status_code == 503  # Should fail without validator node
    
    # Mock validator node with recent cycle
    app.state.validator_node = type("MockNode", (), {
        "http_client": True,
        "last_cycle_time": time.time()
    })
    
    response = client.get("/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"
    assert all(data["checks"].values()) 
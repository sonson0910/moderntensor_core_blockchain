from fastapi import FastAPI, HTTPException, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import psutil
import time
import httpx
from typing import Dict, Any
from .circuit_breaker import CircuitBreaker
from .rate_limiter import RateLimiter
from mt_aptos.config.settings import settings

app = FastAPI(title="Validator Node Health Check")

# Initialize circuit breaker and rate limiter
circuit_breaker = CircuitBreaker(failure_threshold=5, reset_timeout=60)
rate_limiter = RateLimiter(max_requests=100, time_window=60)

async def check_network_connectivity() -> Dict[str, Any]:
    """Check network connectivity to key endpoints"""
    try:
        async with httpx.AsyncClient() as client:
            # Check Aptos node
            aptos_response = await client.get(settings.APTOS_NODE_URL + "/health")
            aptos_status = aptos_response.status_code == 200
            
            # Check validator API - use dynamic endpoint
            validator_endpoint = settings.get_current_validator_endpoint()
            validator_status = False
            if validator_endpoint:
                try:
                    validator_response = await client.get(validator_endpoint + "/health")
                    validator_status = validator_response.status_code == 200
                except Exception:
                    validator_status = False
            
            return {
                "aptos_node": aptos_status,
                "validator_api": validator_status,
                "validator_endpoint": validator_endpoint,
                "status": "healthy" if aptos_status and validator_status else "degraded"
            }
    except Exception as e:
        return {
            "aptos_node": False,
            "validator_api": False,
            "validator_endpoint": None,
            "status": "unhealthy",
            "error": str(e)
        }

async def check_blockchain_status() -> Dict[str, Any]:
    """Check blockchain status and sync state"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(settings.APTOS_NODE_URL + "/v1")
            data = response.json()
            
            return {
                "chain_id": data.get("chain_id"),
                "ledger_version": data.get("ledger_version"),
                "ledger_timestamp": data.get("ledger_timestamp"),
                "status": "healthy"
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Enhanced health check endpoint"""
    try:
        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Get network status
        network_status = await check_network_connectivity()
        
        # Get blockchain status
        blockchain_status = await check_blockchain_status()
        
        # Get circuit breaker status
        circuit_status = circuit_breaker.get_status()
        
        # Get rate limiter status
        rate_status = rate_limiter.get_status()
        
        return {
            "status": "healthy" if all([
                network_status["status"] == "healthy",
                blockchain_status["status"] == "healthy",
                not circuit_status["is_open"]
            ]) else "degraded",
            "timestamp": time.time(),
            "system": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "disk_percent": disk.percent
            },
            "network": network_status,
            "blockchain": blockchain_status,
            "circuit_breaker": circuit_status,
            "rate_limiter": rate_status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/ready")
async def readiness_check() -> Dict[str, Any]:
    """Readiness check endpoint"""
    try:
        # Check if node is properly initialized
        if not hasattr(app.state, 'validator_node'):
            raise HTTPException(status_code=503, detail="Validator node not initialized")
            
        # Check if metagraph is loaded
        if not app.state.validator_node.miners_info or not app.state.validator_node.validators_info:
            raise HTTPException(status_code=503, detail="Metagraph data not loaded")
            
        # Check if health server is running
        if not app.state.validator_node.health_server:
            raise HTTPException(status_code=503, detail="Health server not running")
            
        # Check circuit breaker status
        if circuit_breaker.is_open:
            raise HTTPException(status_code=503, detail="Circuit breaker is open")
            
        return {
            "status": "ready",
            "timestamp": time.time(),
            "checks": {
                "node_initialized": True,
                "metagraph_loaded": True,
                "health_server_running": True,
                "circuit_breaker_closed": True
            }
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@app.get("/live")
async def liveness_check() -> Dict[str, Any]:
    """Liveness check endpoint"""
    try:
        # Check if node is still running
        if not hasattr(app.state, 'validator_node'):
            raise HTTPException(status_code=503, detail="Validator node not found")
            
        # Check if HTTP client is still connected
        if not app.state.validator_node.http_client:
            raise HTTPException(status_code=503, detail="HTTP client not connected")
            
        # Check if current cycle is progressing
        current_time = time.time()
        if hasattr(app.state.validator_node, 'last_cycle_time'):
            if current_time - app.state.validator_node.last_cycle_time > 300:  # 5 minutes
                raise HTTPException(status_code=503, detail="Node appears to be stuck")
                
        # Check rate limiter status
        if not await rate_limiter.acquire():
            raise HTTPException(status_code=503, detail="Rate limit exceeded")
                
        return {
            "status": "alive",
            "timestamp": current_time,
            "checks": {
                "node_running": True,
                "http_client_connected": True,
                "cycle_progressing": True,
                "rate_limit_ok": True
            }
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e)) 
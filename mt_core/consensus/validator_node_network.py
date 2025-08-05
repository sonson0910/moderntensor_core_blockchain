#!/usr/bin/env python3
"""
ValidatorNode Network Module

This module handles all network-related functionality for ValidatorNode including:
- P2P communication with other validators
- API endpoints for miner results and health checks
- Network health monitoring
- HTTP client management
- Server startup and shutdown

The network module manages all external communication for the validator node.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any

import httpx
from fastapi import FastAPI, HTTPException
import uvicorn

from ..core.datatypes import ValidatorScore, MinerResult, ValidatorInfo
from ..network.app.api.v1.endpoints.validator_health import router as health_router
from ..network.server import TaskModel, ResultModel

logger = logging.getLogger(__name__)

# Constants
HTTP_TIMEOUT = 20.0  # Increased from 10.0s to 20.0s for better task assignment
API_SERVER_PORT = 8001  # Default port, should be overridden by validator configuration
HEALTH_CHECK_INTERVAL = 30
MAX_RETRIES = 3


class ValidatorNodeNetwork:
    """
    Network functionality for ValidatorNode.

    This class handles:
    - P2P communication with validators
    - API server for receiving results
    - Health monitoring and endpoints
    - HTTP client management
    """

    def __init__(self, core_node):
        """
        Initialize network management with reference to core node.

        Args:
            core_node: Reference to the ValidatorNodeCore instance
        """
        self.core = core_node
        self.uid_prefix = core_node.uid_prefix

        # Network components
        self.http_client = None
        self.api_server = None
        self.health_server = None
        self.server_task = None

        # API app
        self.app = None

        # Initialize HTTP client (defer to first use to avoid event loop issues)
        self._http_client_initialized = False

    # === HTTP Client Management ===

    async def _initialize_http_client(self):
        """Initialize the HTTP client for P2P communication."""
        if self._http_client_initialized:
            return

        try:
            self.http_client = httpx.AsyncClient(
                timeout=HTTP_TIMEOUT,
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            )
            self.core.http_client = self.http_client
            self._http_client_initialized = True

            logger.info(f"{self.uid_prefix} HTTP client initialized")

        except Exception as e:
            logger.error(f"{self.uid_prefix} Error initializing HTTP client: {e}")

    async def close_http_client(self):
        """Close the HTTP client."""
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None
            self.core.http_client = None
            logger.info(f"{self.uid_prefix} HTTP client closed")

    # === API Server Management ===

    def create_api_app(self) -> FastAPI:
        """Create the FastAPI application for the validator."""
        app = FastAPI(
            title=f"ValidatorNode API - {self.core.info.uid}",
            description="API endpoints for validator consensus operations",
            version="1.0.0",
        )

        # Include health endpoints
        app.include_router(health_router, prefix="/api/v1")

        # Add validator-specific endpoints
        self._add_validator_endpoints(app)

        return app

    def _add_validator_endpoints(self, app: FastAPI):
        """Add validator-specific endpoints to the API app."""

        @app.post("/result")
        async def receive_result(result_data: dict):
            """Receive result from miner."""
            try:
                # Validate result data
                if not all(
                    key in result_data for key in ["task_id", "miner_uid", "result"]
                ):
                    raise HTTPException(
                        status_code=400, detail="Missing required fields"
                    )

                # Create MinerResult object
                miner_result = MinerResult(
                    task_id=result_data["task_id"],
                    miner_uid=result_data["miner_uid"],
                    result_data=result_data["result"],
                    timestamp=time.time(),
                    validator_uid=self.core.info.uid,
                )

                # Add to results buffer
                from .validator_node_tasks import ValidatorNodeTasks

                tasks_module = ValidatorNodeTasks(self.core)
                success = await tasks_module.add_miner_result(miner_result)

                if success:
                    logger.info(
                        f"{self.uid_prefix} Received result from miner {miner_result.miner_uid}"
                    )
                    return {"status": "success", "message": "Result received"}
                else:
                    raise HTTPException(
                        status_code=400, detail="Failed to process result"
                    )

            except Exception as e:
                logger.error(f"{self.uid_prefix} Error receiving result: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @app.post("/v1/miner/submit_result")
        async def submit_miner_result(result: ResultModel):
            """Receive result from miner using standard endpoint expected by BaseMiner."""
            try:
                # Create MinerResult object from ResultModel
                miner_result = MinerResult(
                    task_id=result.task_id,
                    miner_uid=result.miner_uid,
                    result_data=result.result_data,
                    timestamp_received=time.time(),
                )

                # Add to results buffer - use existing tasks instance if available
                if hasattr(self.core, "tasks") and self.core.tasks:
                    logger.debug(
                        f"{self.uid_prefix} Using existing tasks instance for result {result.task_id}"
                    )
                    success = await self.core.tasks.add_miner_result(miner_result)
                else:
                    # Fallback to new instance
                    logger.debug(
                        f"{self.uid_prefix} Using fallback new tasks instance for result {result.task_id}"
                    )
                    from .validator_node_tasks import ValidatorNodeTasks

                    tasks_module = ValidatorNodeTasks(self.core)
                    success = await tasks_module.add_miner_result(miner_result)

                logger.debug(
                    f"{self.uid_prefix} add_miner_result returned: {success} for task {result.task_id}"
                )

                if success:
                    logger.info(
                        f"{self.uid_prefix} Received result for task {result.task_id} from miner {result.miner_uid}"
                    )
                    return {"message": f"Result for task {result.task_id} received"}
                else:
                    logger.warning(
                        f"{self.uid_prefix} Failed to process result for task {result.task_id} - task may not exist"
                    )
                    raise HTTPException(
                        status_code=400, detail="Failed to process result"
                    )

            except Exception as e:
                logger.error(f"{self.uid_prefix} Error receiving miner result: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @app.post("/consensus/scores")
        async def receive_consensus_scores(scores_data: dict):
            """Receive consensus scores from other validators."""
            try:
                # Validate scores data
                required_fields = ["validator_uid", "slot", "scores"]
                if not all(field in scores_data for field in required_fields):
                    raise HTTPException(
                        status_code=400, detail="Missing required fields"
                    )

                # Parse scores
                validator_uid = scores_data["validator_uid"]
                slot = scores_data["slot"]
                raw_scores = scores_data["scores"]

                # Convert to ValidatorScore objects
                scores = []
                for score_data in raw_scores:
                    score = ValidatorScore(
                        task_id=score_data["task_id"],
                        miner_uid=score_data["miner_uid"],
                        validator_uid=validator_uid,
                        score=score_data["score"],
                        timestamp=score_data["timestamp"],
                        cycle=slot,
                    )
                    scores.append(score)

                # Add to received scores
                from .validator_node_consensus import ValidatorNodeConsensus

                consensus_module = ValidatorNodeConsensus(self.core)
                await consensus_module.add_received_score(validator_uid, slot, scores)

                logger.info(
                    f"{self.uid_prefix} Received {len(scores)} consensus scores from validator {validator_uid}"
                )
                return {"status": "success", "message": "Scores received"}

            except Exception as e:
                logger.error(f"{self.uid_prefix} Error receiving consensus scores: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @app.post("/consensus/receive_scores")
        async def receive_p2p_consensus_scores(request_data: dict):
            """Receive P2P consensus scores from other validators."""
            try:
                # Validate request data
                required_fields = ["broadcast_id", "sender_uid", "scores", "timestamp"]
                if not all(field in request_data for field in required_fields):
                    raise HTTPException(
                        status_code=400,
                        detail="Missing required fields in P2P score broadcast",
                    )

                sender_uid = request_data["sender_uid"]
                broadcast_id = request_data["broadcast_id"]
                raw_scores = request_data["scores"]

                # Convert to ValidatorScore objects
                scores = []
                for score_data in raw_scores:
                    try:
                        score = ValidatorScore(
                            task_id=score_data["task_id"],
                            miner_uid=score_data["miner_uid"],
                            validator_uid=score_data["validator_uid"],
                            score=score_data["score"],
                            timestamp=score_data["timestamp"],
                            cycle=score_data.get("cycle", 0),
                        )
                        scores.append(score)
                    except Exception as parse_error:
                        logger.warning(
                            f"{self.uid_prefix} Failed to parse score from {sender_uid}: {parse_error}"
                        )
                        continue

                if not scores:
                    logger.warning(
                        f"{self.uid_prefix} No valid scores received from {sender_uid}"
                    )
                    return {"status": "error", "message": "No valid scores"}

                # Store received scores for consensus processing
                current_cycle = getattr(self.core, "current_cycle", 0)

                # Use the consensus module to handle received scores
                if hasattr(self.core, "consensus"):
                    await self.core.consensus.add_received_score(
                        sender_uid, current_cycle, scores
                    )
                else:
                    # Fallback: store in received_validator_scores directly
                    async with self.core.received_scores_lock:
                        if current_cycle not in self.core.received_validator_scores:
                            self.core.received_validator_scores[current_cycle] = {}

                        self.core.received_validator_scores[current_cycle][
                            sender_uid
                        ] = {score.task_id: score for score in scores}

                logger.info(
                    f"{self.uid_prefix} Received P2P scores from {sender_uid}: "
                    f"{len(scores)} scores in broadcast {broadcast_id}"
                )

                return {
                    "status": "success",
                    "message": f"Received {len(scores)} scores",
                    "broadcast_id": broadcast_id,
                }

            except Exception as e:
                logger.error(
                    f"{self.uid_prefix} Error receiving P2P consensus scores: {e}"
                )
                raise HTTPException(status_code=500, detail=str(e))

        @app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {
                "status": "healthy",
                "validator_uid": self.core.info.uid,
                "timestamp": time.time(),
                "current_cycle": self.core.current_cycle,
                "miners_count": len(self.core.miners_info),
                "validators_count": len(self.core.validators_info),
            }

        @app.get("/metagraph")
        async def get_metagraph():
            """Get current metagraph data."""
            return {
                "miners": {
                    uid: {
                        "uid": miner.uid,
                        "address": miner.address,
                        "trust_score": getattr(miner, "trust_score", 0.0),
                        "stake": getattr(miner, "stake", 0.0),
                        "api_endpoint": getattr(miner, "api_endpoint", None),
                    }
                    for uid, miner in self.core.miners_info.items()
                },
                "validators": {
                    uid: {
                        "uid": validator.uid,
                        "address": validator.address,
                        "trust_score": getattr(validator, "trust_score", 0.0),
                        "stake": getattr(validator, "stake", 0.0),
                        "api_endpoint": getattr(validator, "api_endpoint", None),
                    }
                    for uid, validator in self.core.validators_info.items()
                },
                "timestamp": time.time(),
            }

        @app.get("/consensus/info")
        async def get_consensus_info():
            """Get consensus information."""
            from .validator_node_consensus import ValidatorNodeConsensus

            consensus_module = ValidatorNodeConsensus(self.core)

            return {
                "current_cycle": self.core.current_cycle,
                "statistics": consensus_module.get_consensus_statistics(),
                "timestamp": time.time(),
            }

        @app.get("/consensus/results/{cycle}")
        async def get_consensus_results(cycle: int):
            """Get consensus results for a specific cycle."""
            try:
                results = await self.core.get_consensus_results_for_cycle(cycle)
                if results:
                    return {
                        "cycle": results.cycle,
                        "publisher_uid": results.publisher_uid,
                        "results": {
                            miner_uid: {
                                "miner_uid": result.miner_uid,
                                "p_adj": result.p_adj,
                                "calculated_incentive": result.calculated_incentive,
                            }
                            for miner_uid, result in results.results.items()
                        },
                        "timestamp": time.time(),
                    }
                else:
                    raise HTTPException(
                        status_code=404, detail="Consensus results not found"
                    )

            except Exception as e:
                logger.error(f"{self.uid_prefix} Error getting consensus results: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @app.get("/api/v1/consensus/result/{cycle_num}")
        async def get_consensus_result_v1(cycle_num: int):
            """Get consensus result for miner API compatibility."""
            # Return mock result for now - in production would query actual data
            return {
                "cycle": cycle_num,
                "score": 0.75,
                "timestamp": int(time.time()),
                "status": "completed",
            }

        @app.get("/scores")
        async def get_scores():
            """Get current scores by slot"""
            try:
                scores_by_slot = {}

                # Get slot scores
                for slot, scores in self.core.slot_scores.items():
                    scores_by_slot[str(slot)] = [
                        {
                            "task_id": score.task_id,
                            "miner_uid": score.miner_uid,
                            "validator_uid": score.validator_uid,
                            "score": score.score,
                            "timestamp": score.timestamp,
                            "cycle": getattr(score, "cycle", slot),
                        }
                        for score in scores
                    ]

                return {
                    "slot_scores": scores_by_slot,
                    "total_slots": len(scores_by_slot),
                    "total_scores": sum(
                        len(scores) for scores in scores_by_slot.values()
                    ),
                    "timestamp": time.time(),
                }

            except Exception as e:
                logger.error(f"{self.uid_prefix} Error getting scores: {e}")
                raise HTTPException(status_code=500, detail=str(e))

    async def start_api_server(self, port: Optional[int] = None):
        """Start the API server."""
        logger.debug(
            f"{self.uid_prefix} start_api_server called with port parameter: {port}"
        )

        # If port is explicitly passed, use it directly!
        if port is not None:
            logger.info(f"{self.uid_prefix} Using explicit port parameter: {port}")
        else:
            # Try to get port from core, then from validator info, finally default
            core_api_port = getattr(self.core, "api_port", None)
            logger.debug(f"{self.uid_prefix} core.api_port: {core_api_port}")

            port = core_api_port
            if (
                port is None
                and hasattr(self.core, "info")
                and hasattr(self.core.info, "api_endpoint")
            ):
                # Extract port from api_endpoint if available
                try:
                    import re

                    endpoint = self.core.info.api_endpoint
                    logger.debug(
                        f"{self.uid_prefix} Extracting port from endpoint: {endpoint}"
                    )
                    port_match = re.search(r":(\d+)", endpoint) if endpoint else None
                    port = int(port_match.group(1)) if port_match else None
                    logger.debug(
                        f"{self.uid_prefix} Extracted port from endpoint: {port}"
                    )
                except (AttributeError, ValueError) as e:
                    logger.debug(
                        f"{self.uid_prefix} Failed to extract port from endpoint: {e}"
                    )
                    pass
            # Final fallback to API_SERVER_PORT
            if port is None:
                port = API_SERVER_PORT
                logger.debug(f"{self.uid_prefix} Using fallback port: {port}")

        logger.info(f"{self.uid_prefix} Starting API server on port {port}")

        try:
            self.app = self.create_api_app()

            # Configure uvicorn
            config = uvicorn.Config(
                self.app, host="0.0.0.0", port=port, log_level="info", loop="asyncio"
            )

            # Start server
            server = uvicorn.Server(config)
            self.server_task = asyncio.create_task(server.serve())

            logger.info(f"{self.uid_prefix} API server started on port {port}")

        except Exception as e:
            logger.error(f"{self.uid_prefix} Error starting API server: {e}")
            raise

    async def stop_api_server(self):
        """Stop the API server."""
        if self.server_task:
            self.server_task.cancel()
            try:
                await self.server_task
            except asyncio.CancelledError:
                pass

            self.server_task = None
            logger.info(f"{self.uid_prefix} API server stopped")

    # === P2P Communication ===

    async def send_p2p_message(
        self, target_validator: ValidatorInfo, endpoint: str, payload: Dict
    ) -> bool:
        """
        Send a P2P message to another validator.

        Args:
            target_validator: Target validator info
            endpoint: API endpoint to call
            payload: Message payload

        Returns:
            True if successful, False otherwise
        """
        if not target_validator.api_endpoint:
            logger.warning(
                f"{self.uid_prefix} No API endpoint for validator {target_validator.uid}"
            )
            return False

        try:
            url = f"{target_validator.api_endpoint.rstrip('/')}/{endpoint.lstrip('/')}"

            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                response = await client.post(
                    url, json=payload, headers={"Content-Type": "application/json"}
                )

                if response.status_code == 200:
                    logger.debug(
                        f"{self.uid_prefix} P2P message sent to {target_validator.uid}: {endpoint}"
                    )
                    return True
                else:
                    logger.warning(
                        f"{self.uid_prefix} P2P message failed to {target_validator.uid}: HTTP {response.status_code}"
                    )
                    return False

        except Exception as e:
            logger.error(
                f"{self.uid_prefix} Error sending P2P message to {target_validator.uid}: {e}"
            )
            return False

    async def broadcast_p2p_message(self, endpoint: str, payload: Dict) -> List[bool]:
        """
        Broadcast a P2P message to all active validators.

        Args:
            endpoint: API endpoint to call
            payload: Message payload

        Returns:
            List of success/failure results
        """
        active_validators = await self._get_active_validators()

        # Filter out self
        target_validators = [
            v for v in active_validators if v.uid != self.core.info.uid
        ]

        if not target_validators:
            logger.warning(f"{self.uid_prefix} No active validators to broadcast to")
            return []

        # Send to all validators concurrently
        tasks = [
            self.send_p2p_message(validator, endpoint, payload)
            for validator in target_validators
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successes
        success_count = sum(
            1 for result in results if isinstance(result, bool) and result
        )
        logger.info(
            f"{self.uid_prefix} P2P broadcast to {endpoint}: {success_count}/{len(target_validators)} successful"
        )

        return results

    async def _get_active_validators(self) -> List[ValidatorInfo]:
        """Get list of active validators."""
        active_validators = []

        for validator_info in self.core.validators_info.values():
            if (
                hasattr(validator_info, "status")
                and validator_info.status == "active"
                and validator_info.api_endpoint
            ):
                active_validators.append(validator_info)

        return active_validators

    # === Health Monitoring ===

    async def start_health_monitor(self):
        """Start health monitoring for other validators."""
        logger.info(f"{self.uid_prefix} Starting health monitoring")

        while True:
            try:
                await self._check_validator_health()
                await asyncio.sleep(HEALTH_CHECK_INTERVAL)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"{self.uid_prefix} Error in health monitoring: {e}")
                await asyncio.sleep(HEALTH_CHECK_INTERVAL)

    async def _check_validator_health(self):
        """Check health of all validators."""
        active_validators = await self._get_active_validators()

        health_tasks = [
            self._check_single_validator_health(validator)
            for validator in active_validators
            if validator.uid != self.core.info.uid
        ]

        if health_tasks:
            results = await asyncio.gather(*health_tasks, return_exceptions=True)

            healthy_count = sum(
                1 for result in results if isinstance(result, bool) and result
            )
            logger.debug(
                f"{self.uid_prefix} Health check: {healthy_count}/{len(health_tasks)} validators healthy"
            )

    async def _check_single_validator_health(self, validator: ValidatorInfo) -> bool:
        """Check health of a single validator."""
        try:
            url = f"{validator.api_endpoint.rstrip('/')}/health"

            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)

                if response.status_code == 200:
                    health_data = response.json()
                    logger.debug(
                        f"{self.uid_prefix} Validator {validator.uid} is healthy"
                    )
                    return True
                else:
                    logger.warning(
                        f"{self.uid_prefix} Validator {validator.uid} health check failed: HTTP {response.status_code}"
                    )
                    return False

        except Exception as e:
            logger.debug(
                f"{self.uid_prefix} Health check failed for validator {validator.uid}: {e}"
            )
            return False

    # === Network Utilities ===

    async def send_task_to_miner(self, miner_endpoint: str, task: TaskModel) -> bool:
        """
        Send a task to a miner.

        Args:
            miner_endpoint: Miner's API endpoint
            task: Task to send

        Returns:
            True if successful, False otherwise
        """
        if not miner_endpoint:
            logger.warning(
                f"{self.uid_prefix} No endpoint provided for task {task.task_id}"
            )
            return False

        try:
            url = f"{miner_endpoint.rstrip('/')}/receive-task"

            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                response = await client.post(
                    url, json=task.dict(), headers={"Content-Type": "application/json"}
                )

                if response.status_code == 200:
                    logger.debug(
                        f"{self.uid_prefix} Task {task.task_id} sent successfully to {miner_endpoint}"
                    )
                    return True
                else:
                    logger.warning(
                        f"{self.uid_prefix} Task {task.task_id} failed: HTTP {response.status_code}"
                    )
                    return False

        except Exception as e:
            logger.error(
                f"{self.uid_prefix} Network error sending task {task.task_id}: {e}"
            )
            return False

    async def get_miner_status(self, miner_endpoint: str) -> Optional[Dict]:
        """
        Get status from a miner.

        Args:
            miner_endpoint: Miner's API endpoint

        Returns:
            Miner status data if successful, None otherwise
        """
        if not miner_endpoint:
            return None

        try:
            url = f"{miner_endpoint.rstrip('/')}/status"

            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                response = await client.get(url)

                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(
                        f"{self.uid_prefix} Failed to get miner status: HTTP {response.status_code}"
                    )
                    return None

        except Exception as e:
            logger.debug(f"{self.uid_prefix} Error getting miner status: {e}")
            return None

    def get_network_statistics(self) -> Dict[str, Any]:
        """Get network statistics."""
        return {
            "http_client_active": self.http_client is not None,
            "api_server_active": self.server_task is not None,
            "validators_count": len(self.core.validators_info),
            "miners_count": len(self.core.miners_info),
        }

    # === Cleanup ===

    async def shutdown(self):
        """Shutdown the network module gracefully."""
        await self.cleanup_network_resources()

    async def cleanup_network_resources(self):
        """Clean up all network resources."""
        logger.info(f"{self.uid_prefix} Cleaning up network resources")

        # Stop API server
        await self.stop_api_server()

        # Close HTTP client
        await self.close_http_client()

        logger.info(f"{self.uid_prefix} Network resources cleaned up")

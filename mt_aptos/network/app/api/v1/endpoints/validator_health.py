# File: moderntensor/mt_aptos/network/app/api/v1/endpoints/validator_health.py

import logging
import time
from typing import Annotated, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mt_aptos.consensus.validator_node_refactored import ValidatorNode
else:
    # Runtime import - avoid circular import
    ValidatorNode = None

from ....dependencies import get_validator_node

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/health",
    summary="Validator Health Check",
    description="Health check endpoint for validator node.",
    status_code=status.HTTP_200_OK,
)
async def get_validator_health(
    node: Annotated["ValidatorNode", Depends(get_validator_node)],
) -> Dict[str, Any]:
    """
    Return health status of the validator node.
    """
    try:
        health_data = {
            "status": "healthy",
            "validator_uid": node.info.uid,
            "validator_address": node.info.address,
            "current_cycle": node.current_cycle,
            "consensus_mode": node.consensus_mode,
            "miners_count": len(node.miners_info) if node.miners_info else 0,
            "validators_count": len(node.validators_info) if node.validators_info else 0,
            "timestamp": time.time(),
        }
        
        logger.debug(f"Health check requested for validator {node.info.uid}")
        return health_data
        
    except Exception as e:
        logger.error(f"Health check failed for validator: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Validator health check failed: {str(e)}"
        )


@router.get(
    "/metagraph",
    summary="Get Metagraph Data",
    description="Get current metagraph data (miners and validators).",
    status_code=status.HTTP_200_OK,
)
async def get_metagraph(
    node: Annotated["ValidatorNode", Depends(get_validator_node)],
) -> Dict[str, Any]:
    """
    Return current metagraph data.
    """
    try:
        metagraph_data = {
            "miners": {},
            "validators": {},
            "timestamp": time.time(),
        }
        
        # Add miners info
        if node.miners_info:
            for uid, miner_info in node.miners_info.items():
                metagraph_data["miners"][uid] = {
                    "uid": miner_info.uid,
                    "address": miner_info.address,
                    "api_endpoint": miner_info.api_endpoint,
                    "trust_score": miner_info.trust_score,
                    "weight": miner_info.weight,
                    "stake": miner_info.stake,
                    "status": miner_info.status,
                }
        
        # Add validators info
        if node.validators_info:
            for uid, validator_info in node.validators_info.items():
                metagraph_data["validators"][uid] = {
                    "uid": validator_info.uid,
                    "address": validator_info.address,
                    "api_endpoint": validator_info.api_endpoint,
                    "trust_score": validator_info.trust_score,
                    "weight": validator_info.weight,
                    "stake": validator_info.stake,
                    "status": validator_info.status,
                }
        
        logger.debug(f"Metagraph data requested for validator {node.info.uid}")
        return metagraph_data
        
    except Exception as e:
        logger.error(f"Failed to get metagraph data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get metagraph data: {str(e)}"
        )


@router.get(
    "/consensus/info",
    summary="Get Consensus Info",
    description="Get current consensus information and status.",
    status_code=status.HTTP_200_OK,
)
async def get_consensus_info(
    node: Annotated["ValidatorNode", Depends(get_validator_node)],
) -> Dict[str, Any]:
    """
    Return current consensus information.
    """
    try:
        consensus_info = {
            "current_cycle": node.current_cycle,
            "consensus_mode": node.consensus_mode,
            "slot_length": node.slot_length,
            "current_slot_phase": node.current_slot_phase.value if hasattr(node.current_slot_phase, 'value') else str(node.current_slot_phase),
            "tasks_sent_count": len(node.tasks_sent) if node.tasks_sent else 0,
            "cycle_scores_count": len(node.cycle_scores) if node.cycle_scores else 0,
            "results_buffer_count": len(node.results_buffer) if node.results_buffer else 0,
            "timestamp": time.time(),
        }
        
        logger.debug(f"Consensus info requested for validator {node.info.uid}")
        return consensus_info
        
    except Exception as e:
        logger.error(f"Failed to get consensus info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get consensus info: {str(e)}"
        )


@router.get(
    "/consensus/results",
    summary="Get Consensus Results",
    description="Get recent consensus results.",
    status_code=status.HTTP_200_OK,
)
async def get_consensus_results(
    node: Annotated["ValidatorNode", Depends(get_validator_node)],
) -> Dict[str, Any]:
    """
    Return recent consensus results.
    """
    try:
        results_data = {
            "current_cycle": node.current_cycle,
            "consensus_cache_count": len(node.consensus_results_cache) if node.consensus_results_cache else 0,
            "recent_results": [],
            "timestamp": time.time(),
        }
        
        # Add recent consensus results if available
        if node.consensus_results_cache:
            for cycle, results in list(node.consensus_results_cache.items())[-5:]:  # Last 5 results
                results_data["recent_results"].append({
                    "cycle": cycle,
                    "results": results,
                })
        
        logger.debug(f"Consensus results requested for validator {node.info.uid}")
        return results_data
        
    except Exception as e:
        logger.error(f"Failed to get consensus results: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get consensus results: {str(e)}"
        ) 
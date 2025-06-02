# sdk/metagraph/metagraph_data.py
import logging
from typing import List, Dict, Any, Optional, Type, Tuple, DefaultDict
from collections import defaultdict  # Import defaultdict
import asyncio

from mt_aptos.async_client import RestClient

# Import các lớp Datum đã cập nhật
from .metagraph_datum import (
    MinerData,
    ValidatorData,
    SubnetDynamicData,
    SubnetStaticData,
    from_move_resource
)

logger = logging.getLogger(__name__)


# --- Functions to get data for Miners ---
async def get_all_miner_data(
    client: RestClient, contract_address: str
) -> List[Dict[str, Any]]:
    """
    Retrieves and processes all miner data from the Aptos blockchain.

    Args:
        client: Aptos REST client.
        contract_address: Contract address for ModernTensor.

    Returns:
        A list of dictionaries, each containing the details of a miner.
        Returns an empty list if no miners are found or if an error occurs.
    """
    logger.info(f"Fetching Miner data from contract: {contract_address}")

    try:
        # Call the view function to get all miners from the contract
        results = await client.view_function(
            contract_address,
            "moderntensor",
            "get_all_miners",
            []
        )
        
        logger.info(f"Found {len(results)} miners in contract")
        
        # Process each miner's data into our expected format
        processed_miners = []
        for miner_resource in results:
            try:
                # Convert resource to our data model
                miner_data = {
                    "uid": miner_resource.get("uid", ""),
                    "subnet_uid": int(miner_resource.get("subnet_uid", -1)),
                    "stake": int(miner_resource.get("stake", 0)),
                    "trust_score": float(miner_resource.get("trust_score", 0.0)),
                    "last_performance": float(miner_resource.get("last_performance", 0.0)),
                    "accumulated_rewards": int(miner_resource.get("accumulated_rewards", 0)),
                    "last_update_time": int(miner_resource.get("last_update_time", 0)),
                    "performance_history_hash": miner_resource.get("performance_history_hash", ""),
                    "wallet_addr_hash": miner_resource.get("wallet_addr_hash", ""),
                    "status": int(miner_resource.get("status", 0)),
                    "registration_time": int(miner_resource.get("registration_time", 0)),
                    "api_endpoint": miner_resource.get("api_endpoint", ""),
                    "weight": float(miner_resource.get("weight", 0.0)),
                }
                processed_miners.append(miner_data)
            except Exception as e:
                logger.warning(f"Failed to process miner data: {e}")
                logger.debug(f"Problematic miner data: {miner_resource}")
                continue
                
        return processed_miners
        
    except Exception as e:
        logger.exception(f"Failed to fetch miners from contract: {e}")
        return []


# --- Functions to get data for Validators ---
async def get_all_validator_data(
    client: RestClient, contract_address: str
) -> List[Dict[str, Any]]:
    """
    Retrieves and processes all validator data from the Aptos blockchain.

    Args:
        client: Aptos REST client.
        contract_address: Contract address for ModernTensor.

    Returns:
        A list of dictionaries, each containing the details of a validator.
        Returns an empty list if no validators are found or if an error occurs.
    """
    logger.info(f"Fetching Validator data from contract: {contract_address}")

    try:
        # Call the view function to get all validators from the contract
        results = await client.view_function(
            contract_address,
            "moderntensor",
            "get_all_validators",
            []
        )
        
        logger.info(f"Found {len(results)} validators in contract")
        
        # Process each validator's data into our expected format
        processed_validators = []
        for validator_resource in results:
            try:
                # Convert resource to our data model
                validator_data = {
                    "uid": validator_resource.get("uid", ""),
                    "subnet_uid": int(validator_resource.get("subnet_uid", -1)),
                    "stake": int(validator_resource.get("stake", 0)),
                    "trust_score": float(validator_resource.get("trust_score", 0.0)),
                    "last_performance": float(validator_resource.get("last_performance", 0.0)),
                    "accumulated_rewards": int(validator_resource.get("accumulated_rewards", 0)),
                    "last_update_time": int(validator_resource.get("last_update_time", 0)),
                    "performance_history_hash": validator_resource.get("performance_history_hash", ""),
                    "wallet_addr_hash": validator_resource.get("wallet_addr_hash", ""),
                    "status": int(validator_resource.get("status", 0)),
                    "registration_time": int(validator_resource.get("registration_time", 0)),
                    "api_endpoint": validator_resource.get("api_endpoint", ""),
                    "weight": float(validator_resource.get("weight", 0.0)),
                }
                processed_validators.append(validator_data)
            except Exception as e:
                logger.warning(f"Failed to process validator data: {e}")
                logger.debug(f"Problematic validator data: {validator_resource}")
                continue
                
        return processed_validators
        
    except Exception as e:
        logger.exception(f"Failed to fetch validators from contract: {e}")
        return []


# --- Functions to get data for Subnets ---
async def get_all_subnet_data(
    client: RestClient, contract_address: str
) -> List[Dict[str, Any]]:
    """
    Retrieves and processes all subnet data from the Aptos blockchain.

    Args:
        client: Aptos REST client.
        contract_address: Contract address for ModernTensor.

    Returns:
        A list of dictionaries, each containing the details of a subnet.
        Returns an empty list if no subnets are found or if an error occurs.
    """
    logger.info(f"Fetching Subnet data from contract: {contract_address}")

    try:
        # Call the view function to get all subnets from the contract
        results = await client.view_function(
            contract_address,
            "moderntensor",
            "get_all_subnets",
            []
        )
        
        logger.info(f"Found {len(results)} subnets in contract")
        
        # Process each subnet's data into our expected format
        processed_subnets = []
        for subnet_resource in results:
            try:
                # For subnets, we might have static and dynamic data combined
                subnet_data = {
                    "net_uid": int(subnet_resource.get("net_uid", -1)),
                    "name": subnet_resource.get("name", ""),
                    "owner_addr": subnet_resource.get("owner_addr", ""),
                    "max_miners": int(subnet_resource.get("max_miners", 0)),
                    "max_validators": int(subnet_resource.get("max_validators", 0)),
                    "immunity_period": int(subnet_resource.get("immunity_period", 0)),
                    "creation_time": int(subnet_resource.get("creation_time", 0)),
                    "description": subnet_resource.get("description", ""),
                    "version": int(subnet_resource.get("version", 0)),
                    "min_stake_miner": int(subnet_resource.get("min_stake_miner", 0)),
                    "min_stake_validator": int(subnet_resource.get("min_stake_validator", 0)),
                    "weight": float(subnet_resource.get("weight", 0.0)),
                    "performance": float(subnet_resource.get("performance", 0.0)),
                    "current_epoch": int(subnet_resource.get("current_epoch", 0)),
                    "registration_open": int(subnet_resource.get("registration_open", 0)),
                }
                processed_subnets.append(subnet_data)
            except Exception as e:
                logger.warning(f"Failed to process subnet data: {e}")
                logger.debug(f"Problematic subnet data: {subnet_resource}")
                continue
                
        return processed_subnets
        
    except Exception as e:
        logger.exception(f"Failed to fetch subnets from contract: {e}")
        return []


# --- Functions to get entity data ---
async def get_entity_data(
    client: RestClient, 
    contract_address: str, 
    entity_type: str, 
    entity_id: str
) -> Optional[Dict[str, Any]]:
    """
    Retrieves and processes data for a specific entity from the Aptos blockchain.

    Args:
        client: Aptos REST client.
        contract_address: Contract address for ModernTensor.
        entity_type: Type of entity ("miner", "validator", "subnet").
        entity_id: Unique identifier for the entity.

    Returns:
        A dictionary containing the entity details, or None if not found.
    """
    logger.info(f"Fetching {entity_type} data for ID: {entity_id}")

    try:
        # Call the appropriate view function based on entity type
        if entity_type.lower() == "miner":
            result = await client.view_function(
                contract_address,
                "moderntensor",
                "get_miner",
                [entity_id]
            )
        elif entity_type.lower() == "validator":
            result = await client.view_function(
                contract_address,
                "moderntensor",
                "get_validator",
                [entity_id]
            )
        elif entity_type.lower() == "subnet":
            result = await client.view_function(
                contract_address,
                "moderntensor",
                "get_subnet",
                [entity_id]
            )
        else:
            logger.error(f"Unsupported entity type: {entity_type}")
            return None

        if result:
            logger.info(f"Found {entity_type} with ID: {entity_id}")
            return result
        else:
            logger.warning(f"No {entity_type} found with ID: {entity_id}")
            return None
            
    except Exception as e:
        logger.exception(f"Failed to fetch {entity_type} data for ID {entity_id}: {e}")
        return None


# --- DEPRECATED Cardano functions (kept for reference only) ---
# These functions are no longer used and should be removed in future versions

def get_all_miner_data_old(*args, **kwargs):
    """[DEPRECATED] Old Cardano implementation, DO NOT USE for Aptos."""
    raise NotImplementedError("This function is deprecated for Aptos. Use get_all_miner_data() instead.")

def get_all_validator_data_old(*args, **kwargs):
    """[DEPRECATED] Old Cardano implementation, DO NOT USE for Aptos."""
    raise NotImplementedError("This function is deprecated for Aptos. Use get_all_validator_data() instead.")

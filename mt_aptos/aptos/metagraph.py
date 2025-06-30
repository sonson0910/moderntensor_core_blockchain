"""
Functions for updating entities in the metagraph on Aptos blockchain.
"""
import logging
import json
import os
from typing import Dict, Any, Optional, List
import time

from mt_aptos.async_client import RestClient
from mt_aptos.account import Account
from mt_aptos.transactions import EntryFunction, TransactionArgument, TransactionPayload

from mt_aptos.config.settings import settings
from mt_aptos.core.datatypes import MinerInfo, ValidatorInfo

logger = logging.getLogger(__name__)


async def update_miner(
    client: RestClient,
    account: Account,
    contract_address: str,
    miner_uid: str,
    updates: Dict[str, Any]
) -> Optional[str]:
    """
    Updates a miner's data in the metagraph on Aptos blockchain.
    
    Args:
        client: Aptos REST client
        account: Account with permissions to update the miner
        contract_address: Address of the ModernTensor contract
        miner_uid: UID of the miner to update
        updates: Dictionary of field names and values to update
        
    Returns:
        Optional[str]: Transaction hash if successful, None otherwise
    """
    try:
        logger.info(f"Updating miner {miner_uid} on Aptos blockchain")
        
        # First get current miner data to only update what's changed
        current_data = await client.view_function(
            contract_address,
            "moderntensor",
            "get_miner",
            [miner_uid]
        )
        
        if not current_data:
            logger.error(f"Miner {miner_uid} not found")
            return None
            
        # Create a full data object with updated fields
        full_data = current_data.copy()
        full_data.update(updates)
        
        # Convert string values to correct types if needed
        if "trust_score" in updates and isinstance(updates["trust_score"], float):
            scaled_trust_score = int(updates["trust_score"] * settings.METAGRAPH_DATUM_INT_DIVISOR)
            full_data["scaled_trust_score"] = scaled_trust_score
            
        if "last_performance" in updates and isinstance(updates["last_performance"], float):
            scaled_last_performance = int(updates["last_performance"] * settings.METAGRAPH_DATUM_INT_DIVISOR)
            full_data["scaled_last_performance"] = scaled_last_performance
            
        # Create transaction arguments
        args = [
            TransactionArgument(miner_uid, TransactionArgument.STRING),
            # Add all other fields that need to be updated
            # The order and types must match the Move function definition
        ]
        
        # Create and submit transaction
        payload = TransactionPayload(
            EntryFunction.natural(
                f"{contract_address}::moderntensor",
                "update_miner",
                [],  # Type arguments (empty for this function)
                args
            )
        )
        
        txn = await client.submit_transaction(account, payload)
        logger.info(f"Submitted miner update transaction: {txn}")
        
        # Wait for transaction confirmation
        await client.wait_for_transaction(txn)
        
        return txn
        
    except Exception as e:
        logger.exception(f"Error updating miner {miner_uid}: {e}")
        return None


async def update_validator(
    client: RestClient,
    account: Account,
    contract_address: str,
    validator_uid: str,
    updates: Dict[str, Any]
) -> Optional[str]:
    """
    Updates a validator's data in the metagraph on Aptos blockchain.
    
    Args:
        client: Aptos REST client
        account: Account with permissions to update the validator
        contract_address: Address of the ModernTensor contract
        validator_uid: UID of the validator to update
        updates: Dictionary of field names and values to update
        
    Returns:
        Optional[str]: Transaction hash if successful, None otherwise
    """
    try:
        logger.info(f"Updating validator {validator_uid} on Aptos blockchain")
        
        # Get current validator data
        current_data = await client.view_function(
            contract_address,
            "moderntensor",
            "get_validator",
            [validator_uid]
        )
        
        if not current_data:
            logger.error(f"Validator {validator_uid} not found")
            return None
            
        # Create a full data object with updated fields
        full_data = current_data.copy()
        full_data.update(updates)
        
        # Convert string values to correct types if needed
        if "trust_score" in updates and isinstance(updates["trust_score"], float):
            scaled_trust_score = int(updates["trust_score"] * settings.METAGRAPH_DATUM_INT_DIVISOR)
            full_data["scaled_trust_score"] = scaled_trust_score
            
        if "last_performance" in updates and isinstance(updates["last_performance"], float):
            scaled_last_performance = int(updates["last_performance"] * settings.METAGRAPH_DATUM_INT_DIVISOR)
            full_data["scaled_last_performance"] = scaled_last_performance
        
        # Create transaction arguments
        args = [
            TransactionArgument(validator_uid, TransactionArgument.STRING),
            # Add all other fields that need to be updated
        ]
        
        # Create and submit transaction
        payload = TransactionPayload(
            EntryFunction.natural(
                f"{contract_address}::moderntensor",
                "update_validator",
                [],  # Type arguments (empty for this function)
                args
            )
        )
        
        txn = await client.submit_transaction(account, payload)
        logger.info(f"Submitted validator update transaction: {txn}")
        
        # Wait for transaction confirmation
        await client.wait_for_transaction(txn)
        
        return txn
        
    except Exception as e:
        logger.exception(f"Error updating validator {validator_uid}: {e}")
        return None


async def register_miner(
    client: RestClient,
    account: Account,
    contract_address: str,
    subnet_uid: int,
    api_endpoint: str,
    stake_amount: int
) -> Optional[str]:
    """
    Registers a new miner in the metagraph on Aptos blockchain.
    
    Args:
        client: Aptos REST client
        account: Account to register as miner
        contract_address: Address of the ModernTensor contract
        subnet_uid: ID of the subnet to join
        api_endpoint: URL endpoint where the miner can be reached
        stake_amount: Amount to stake (in smallest units)
        
    Returns:
        Optional[str]: Transaction hash if successful, None otherwise
    """
    try:
        logger.info(f"Registering new miner for account {account.address().hex()} in subnet {subnet_uid}")
        
        # Create transaction arguments
        args = [
            TransactionArgument(subnet_uid, TransactionArgument.U64),
            TransactionArgument(api_endpoint, TransactionArgument.STRING),
            TransactionArgument(stake_amount, TransactionArgument.U64),
        ]
        
        # Create and submit transaction
        payload = TransactionPayload(
            EntryFunction.natural(
                f"{contract_address}::moderntensor",
                "register_miner",
                [],  # Type arguments (empty for this function)
                args
            )
        )
        
        txn = await client.submit_transaction(account, payload)
        logger.info(f"Submitted miner registration transaction: {txn}")
        
        # Wait for transaction confirmation
        await client.wait_for_transaction(txn)
        
        return txn
        
    except Exception as e:
        logger.exception(f"Error registering miner: {e}")
        return None


async def register_validator(
    client: RestClient,
    account: Account,
    contract_address: str,
    subnet_uid: int,
    api_endpoint: str,
    stake_amount: int
) -> Optional[str]:
    """
    Registers a new validator in the metagraph on Aptos blockchain.
    
    Args:
        client: Aptos REST client
        account: Account to register as validator
        contract_address: Address of the ModernTensor contract
        subnet_uid: ID of the subnet to join
        api_endpoint: URL endpoint where the validator can be reached
        stake_amount: Amount to stake (in smallest units)
        
    Returns:
        Optional[str]: Transaction hash if successful, None otherwise
    """
    try:
        logger.info(f"Registering new validator for account {account.address().hex()} in subnet {subnet_uid}")
        
        # Create transaction arguments
        args = [
            TransactionArgument(subnet_uid, TransactionArgument.U64),
            TransactionArgument(api_endpoint, TransactionArgument.STRING),
            TransactionArgument(stake_amount, TransactionArgument.U64),
        ]
        
        # Create and submit transaction
        payload = TransactionPayload(
            EntryFunction.natural(
                f"{contract_address}::moderntensor",
                "register_validator",
                [],  # Type arguments (empty for this function)
                args
            )
        )
        
        txn = await client.submit_transaction(account, payload)
        logger.info(f"Submitted validator registration transaction: {txn}")
        
        # Wait for transaction confirmation
        await client.wait_for_transaction(txn)
        
        return txn
        
    except Exception as e:
        logger.exception(f"Error registering validator: {e}")
        return None


async def get_all_miners(
    client: RestClient,
    contract_address: str,
    subnet_uid: Optional[int] = None
) -> List[MinerInfo]:
    """
    Gets all miners registered in the metagraph by checking known addresses.
    
    Args:
        client: Aptos REST client
        contract_address: Address of the ModernTensor contract
        subnet_uid: Optional subnet ID to filter miners by subnet
        
    Returns:
        List[MinerInfo]: List of miner information
    """
    try:
        logger.info(f"Getting all miners from contract {contract_address}")
        
        # Known miner addresses from config
        known_miner_addresses = []
        
        # Get all MINER_*_ADDRESS from environment
        for key, value in os.environ.items():
            if key.startswith("MINER_") and key.endswith("_ADDRESS") and value:
                known_miner_addresses.append(value)
        
        # Also check legacy MINER_ADDRESS
        miner_addr = os.getenv("MINER_ADDRESS")
        if miner_addr and miner_addr not in known_miner_addresses:
            known_miner_addresses.append(miner_addr)
            
        logger.info(f"Checking {len(known_miner_addresses)} known miner addresses: {known_miner_addresses}")
        
        result = []
        for miner_address in known_miner_addresses:
            try:
                # Check if this address is registered as a miner
                is_miner_response = await client.view(
                    f"{contract_address}::full_moderntensor::is_miner",
                    [],
                    [miner_address]
                )
                
                # Parse bytes response to JSON
                if isinstance(is_miner_response, bytes):
                    is_miner_data = json.loads(is_miner_response.decode())
                else:
                    is_miner_data = is_miner_response
                
                if is_miner_data and len(is_miner_data) > 0 and is_miner_data[0]:
                    # Get miner info
                    miner_info_response = await client.view(
                        f"{contract_address}::full_moderntensor::get_miner_info",
                        [],
                        [miner_address]
                    )
                    
                    # Parse bytes response to JSON
                    if isinstance(miner_info_response, bytes):
                        miner_data = json.loads(miner_info_response.decode())
                    else:
                        miner_data = miner_info_response
                    
                    if miner_data and len(miner_data) > 0:
                        try:
                            miner_info_raw = miner_data[0]
                            logger.debug(f"Creating MinerInfo for {miner_address} with data: {miner_info_raw}")
                            
                            # Convert raw data to MinerInfo
                            miner = MinerInfo(
                                uid=miner_info_raw.get("uid", ""),
                                address=miner_address,
                                api_endpoint=miner_info_raw.get("api_endpoint", ""),
                                trust_score=int(miner_info_raw.get("trust_score", 0)) / 100_000_000,  # Scale down from 1e8
                                stake=int(miner_info_raw.get("stake", 0)) / 100_000_000,  # Convert from octas 
                                status=int(miner_info_raw.get("status", 0)),
                                subnet_uid=int(miner_info_raw.get("subnet_uid", 0)),
                                registration_time=int(miner_info_raw.get("registration_time", 0)),
                                weight=int(miner_info_raw.get("weight", 0)) / 100_000_000,  # Scale down from 1e8
                                performance_history=[],  # Empty for now
                                wallet_addr_hash=miner_info_raw.get("wallet_addr_hash", ""),
                                performance_history_hash=miner_info_raw.get("performance_history_hash", "")
                            )
                            
                            # Filter by subnet if specified
                            if subnet_uid is None or miner.subnet_uid == subnet_uid:
                                result.append(miner)
                                logger.info(f"✅ Found miner: {miner.uid} at {miner_address}")
                            else:
                                logger.debug(f"Miner {miner.uid} filtered out (subnet {miner.subnet_uid} != {subnet_uid})")
                                
                        except Exception as creation_error:
                            logger.error(f"Failed to create MinerInfo for {miner_address}: {creation_error}")
                            logger.error(f"Raw data: {miner_info_raw}")
                            continue
                        
            except Exception as e:
                logger.debug(f"Address {miner_address} is not a registered miner: {e}")
                continue
                
        logger.info(f"Found {len(result)} registered miners")
        return result
        
    except Exception as e:
        logger.exception(f"Error getting all miners: {e}")
        return []


async def get_all_validators(
    client: RestClient,
    contract_address: str,
    subnet_uid: Optional[int] = None
) -> List[ValidatorInfo]:
    """
    Gets all validators registered in the metagraph by checking known addresses.
    
    Args:
        client: Aptos REST client
        contract_address: Address of the ModernTensor contract
        subnet_uid: Optional subnet ID to filter validators by subnet
        
    Returns:
        List[ValidatorInfo]: List of validator information
    """
    try:
        logger.info(f"Getting all validators from contract {contract_address}")
        
        # Known validator addresses from config
        known_validator_addresses = []
        
        # Get all VALIDATOR_*_ADDRESS from environment
        for key, value in os.environ.items():
            if key.startswith("VALIDATOR_") and key.endswith("_ADDRESS") and value:
                known_validator_addresses.append(value)
        
        # Also check legacy VALIDATOR_ADDRESS
        validator_addr = os.getenv("VALIDATOR_ADDRESS")
        if validator_addr and validator_addr not in known_validator_addresses:
            known_validator_addresses.append(validator_addr)
            
        logger.info(f"Checking {len(known_validator_addresses)} known validator addresses: {known_validator_addresses}")
        
        result = []
        for validator_address in known_validator_addresses:
            try:
                # Check if this address is registered as a validator
                is_validator_response = await client.view(
                    f"{contract_address}::full_moderntensor::is_validator",
                    [],
                    [validator_address]
                )
                
                # Parse bytes response to JSON
                if isinstance(is_validator_response, bytes):
                    is_validator_data = json.loads(is_validator_response.decode())
                else:
                    is_validator_data = is_validator_response
                
                if is_validator_data and len(is_validator_data) > 0 and is_validator_data[0]:
                    # Get validator info
                    validator_info_response = await client.view(
                        f"{contract_address}::full_moderntensor::get_validator_info",
                        [],
                        [validator_address]
                    )
                    
                    # Parse bytes response to JSON
                    if isinstance(validator_info_response, bytes):
                        validator_data = json.loads(validator_info_response.decode())
                    else:
                        validator_data = validator_info_response
                    
                    if validator_data and len(validator_data) > 0:
                        validator_info_raw = validator_data[0]
                        
                        # Convert raw data to ValidatorInfo
                        validator = ValidatorInfo(
                            uid=validator_info_raw.get("uid", ""),
                            address=validator_address,
                            api_endpoint=validator_info_raw.get("api_endpoint", ""),
                            trust_score=int(validator_info_raw.get("trust_score", 0)) / 100_000_000,  # Scale down from 1e8
                            stake=int(validator_info_raw.get("stake", 0)) / 100_000_000,  # Convert from octas
                            status=int(validator_info_raw.get("status", 0)),
                            subnet_uid=int(validator_info_raw.get("subnet_uid", 0)),
                            registration_time=int(validator_info_raw.get("registration_time", 0)),
                            last_performance=int(validator_info_raw.get("last_performance", 0)) / 100_000_000,  # Scale down from 1e8
                            weight=int(validator_info_raw.get("weight", 0)) / 100_000_000,  # Scale down from 1e8
                            performance_history=[],  # Empty for now
                            wallet_addr_hash=validator_info_raw.get("wallet_addr_hash", ""),
                            performance_history_hash=validator_info_raw.get("performance_history_hash", "")
                        )
                        
                        # Filter by subnet if specified
                        if subnet_uid is None or validator.subnet_uid == subnet_uid:
                            result.append(validator)
                            logger.info(f"✅ Found validator: {validator.uid} at {validator_address}")
                        
            except Exception as e:
                logger.debug(f"Address {validator_address} is not a registered validator: {e}")
                continue
                
        logger.info(f"Found {len(result)} registered validators")
        return result
        
    except Exception as e:
        logger.exception(f"Error getting all validators: {e}")
        return [] 
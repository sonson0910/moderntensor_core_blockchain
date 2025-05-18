"""
Functions for updating entities in the metagraph on Aptos blockchain.
"""
import logging
from typing import Dict, Any, Optional, List
import time

from aptos_sdk.async_client import RestClient
from aptos_sdk.account import Account
from aptos_sdk.transactions import EntryFunction, TransactionArgument, TransactionPayload

from .metagraph_datum import MinerData, ValidatorData, to_move_resource
from sdk.config.settings import settings

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
        
        # Similar implementation as update_miner but for validators
        # First get current validator data
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
            
        # Create and submit transaction similar to update_miner
        # ...
        
        # Placeholder for actual transaction submission
        txn = "0xdummy_transaction_hash"
        logger.info(f"Submitted validator update transaction: {txn}")
        
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
        
        # Similar implementation as register_miner but for validators
        # ...
        
        # Placeholder for actual transaction submission
        txn = "0xdummy_transaction_hash"
        logger.info(f"Submitted validator registration transaction: {txn}")
        
        return txn
        
    except Exception as e:
        logger.exception(f"Error registering validator: {e}")
        return None 
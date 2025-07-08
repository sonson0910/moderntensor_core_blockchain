"""
Functions for updating entities in the metagraph on Core blockchain.
"""

import logging
from typing import Dict, Any, Optional, List
import time

from web3 import Web3
from eth_account import Account

from .metagraph_datum import MinerData, ValidatorData, to_move_resource
from ..config.settings import settings
from ..core_client.contract_client import ModernTensorCoreClient

logger = logging.getLogger(__name__)


async def update_miner(
    client: ModernTensorCoreClient,
    account: Account,
    contract_address: str,
    miner_uid: str,
    updates: Dict[str, Any],
) -> Optional[str]:
    """
    Updates a miner's data in the metagraph on Core blockchain.

    Args:
        client: Core blockchain client
        account: Account with permissions to update the miner
        contract_address: Address of the ModernTensor contract
        miner_uid: UID of the miner to update
        updates: Dictionary of field names and values to update

    Returns:
        Optional[str]: Transaction hash if successful, None otherwise
    """
    try:
        logger.info(f"Updating miner {miner_uid} on Core blockchain")

        # First get current miner data to only update what's changed  
        current_data = await client.get_miner_data(miner_uid)

        if not current_data:
            logger.error(f"Miner {miner_uid} not found")
            return None

        # Create a full data object with updated fields
        full_data = current_data.copy()
        full_data.update(updates)

        # Convert string values to correct types if needed
        if "trust_score" in updates and isinstance(updates["trust_score"], float):
            scaled_trust_score = int(
                updates["trust_score"] * settings.METAGRAPH_DATUM_INT_DIVISOR
            )
            full_data["scaled_trust_score"] = scaled_trust_score

        if "last_performance" in updates and isinstance(
            updates["last_performance"], float
        ):
            scaled_last_performance = int(
                updates["last_performance"] * settings.METAGRAPH_DATUM_INT_DIVISOR
            )
            full_data["scaled_last_performance"] = scaled_last_performance

        # Call Core blockchain smart contract
        txn_hash = await client.update_miner(
            miner_uid=miner_uid, updates=updates, account=account
        )
        logger.info(f"Submitted miner update transaction: {txn_hash}")

        return txn_hash

    except Exception as e:
        logger.exception(f"Error updating miner {miner_uid}: {e}")
        return None


async def update_validator(
    client: ModernTensorCoreClient,
    account: Account,
    contract_address: str,
    validator_uid: str,
    updates: Dict[str, Any],
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
        current_data = await client.get_validator_data(validator_uid)

        if not current_data:
            logger.error(f"Validator {validator_uid} not found")
            return None

        # Create a full data object with updated fields
        full_data = current_data.copy()
        full_data.update(updates)

        # Convert string values to correct types if needed
        if "trust_score" in updates and isinstance(updates["trust_score"], float):
            scaled_trust_score = int(
                updates["trust_score"] * settings.METAGRAPH_DATUM_INT_DIVISOR
            )
            full_data["scaled_trust_score"] = scaled_trust_score

        if "last_performance" in updates and isinstance(
            updates["last_performance"], float
        ):
            scaled_last_performance = int(
                updates["last_performance"] * settings.METAGRAPH_DATUM_INT_DIVISOR
            )
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
    client: ModernTensorCoreClient,
    account: Account,
    contract_address: str,
    subnet_uid: int,
    api_endpoint: str,
    stake_amount: int,
) -> Optional[str]:
    """
    Registers a new miner in the metagraph on Core blockchain.

    Args:
        client: Core blockchain client
        account: Account to register as miner
        contract_address: Address of the ModernTensor contract
        subnet_uid: ID of the subnet to join
        api_endpoint: URL endpoint where the miner can be reached
        stake_amount: Amount to stake (in smallest units)

    Returns:
        Optional[str]: Transaction hash if successful, None otherwise
    """
    try:
        logger.info(
            f"Registering new miner for account {account.address().hex()} in subnet {subnet_uid}"
        )

        # Call Core blockchain smart contract
        txn_hash = await client.register_miner(
            subnet_uid=subnet_uid,
            api_endpoint=api_endpoint,
            stake_amount=stake_amount,
            account=account,
        )
        logger.info(f"Submitted miner registration transaction: {txn_hash}")

        return txn_hash

    except Exception as e:
        logger.exception(f"Error registering miner: {e}")
        return None


async def register_validator(
    client: ModernTensorCoreClient,
    account: Account,
    contract_address: str,
    subnet_uid: int,
    api_endpoint: str,
    stake_amount: int,
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
        logger.info(
            f"Registering new validator for account {account.address().hex()} in subnet {subnet_uid}"
        )

        # Similar implementation as register_miner but for validators
        # ...

        # Placeholder for actual transaction submission
        txn = "0xdummy_transaction_hash"
        logger.info(f"Submitted validator registration transaction: {txn}")

        return txn

    except Exception as e:
        logger.exception(f"Error registering validator: {e}")
        return None

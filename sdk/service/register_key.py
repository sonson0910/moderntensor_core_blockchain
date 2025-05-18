from typing import Optional, Dict, Any
from aptos_sdk.account import Account
from aptos_sdk.async_client import RestClient
from aptos_sdk.transactions import EntryFunction, TransactionArgument, TransactionPayload

from sdk.config.settings import settings, logger


async def register_validator(
    client: RestClient,
    account: Account,
    contract_address: str,
    subnet_uid: int,
    api_endpoint: str,
    stake_amount: int = 0,
) -> str:
    """
    Registers an account as a validator in the specified subnet.

    This function creates and submits a transaction to register the account as
    a validator in the ModernTensor contract on the Aptos blockchain.

    Args:
        client (RestClient): The Aptos REST client
        account (Account): The account to register as a validator
        contract_address (str): The address of the ModernTensor contract
        subnet_uid (int): The ID of the subnet to join
        api_endpoint (str): The API endpoint URL for this validator
        stake_amount (int, optional): Amount of coins to stake in smallest unit. Defaults to 0.

    Returns:
        str: The transaction hash of the submitted transaction

    Raises:
        Exception: If the transaction submission fails
    """
    # Format the contract address
    if not contract_address.startswith("0x"):
        contract_address = f"0x{contract_address}"

    # Create transaction arguments
    args = [
        TransactionArgument(subnet_uid, TransactionArgument.U64),
        TransactionArgument(api_endpoint, TransactionArgument.STRING),
        TransactionArgument(stake_amount, TransactionArgument.U64),
    ]

    # Create transaction payload
    payload = TransactionPayload(
        EntryFunction.natural(
            f"{contract_address}::moderntensor",
            "register_validator",
            [],  # Type arguments (empty for this function)
            args
        )
    )

    try:
        # Submit transaction
        logger.info(f"Submitting register_validator transaction for account {account.address().hex()}")
        txn_hash = await client.submit_transaction(account, payload)
        
        # Wait for transaction confirmation
        await client.wait_for_transaction(txn_hash)
        
        logger.info(f"Successfully registered as validator in subnet {subnet_uid}")
        return txn_hash
    except Exception as e:
        logger.error(f"Failed to register as validator: {e}")
        raise


async def register_miner(
    client: RestClient,
    account: Account,
    contract_address: str,
    subnet_uid: int,
    api_endpoint: str,
    stake_amount: int = 0,
) -> str:
    """
    Registers an account as a miner in the specified subnet.

    This function creates and submits a transaction to register the account as
    a miner in the ModernTensor contract on the Aptos blockchain.

    Args:
        client (RestClient): The Aptos REST client
        account (Account): The account to register as a miner
        contract_address (str): The address of the ModernTensor contract
        subnet_uid (int): The ID of the subnet to join
        api_endpoint (str): The API endpoint URL for this miner
        stake_amount (int, optional): Amount of coins to stake in smallest unit. Defaults to 0.

    Returns:
        str: The transaction hash of the submitted transaction

    Raises:
        Exception: If the transaction submission fails
    """
    # Format the contract address
    if not contract_address.startswith("0x"):
        contract_address = f"0x{contract_address}"

    # Create transaction arguments
    args = [
        TransactionArgument(subnet_uid, TransactionArgument.U64),
        TransactionArgument(api_endpoint, TransactionArgument.STRING),
        TransactionArgument(stake_amount, TransactionArgument.U64),
    ]

    # Create transaction payload
    payload = TransactionPayload(
        EntryFunction.natural(
            f"{contract_address}::moderntensor",
            "register_miner",
            [],  # Type arguments (empty for this function)
            args
        )
    )

    try:
        # Submit transaction
        logger.info(f"Submitting register_miner transaction for account {account.address().hex()}")
        txn_hash = await client.submit_transaction(account, payload)
        
        # Wait for transaction confirmation
        await client.wait_for_transaction(txn_hash)
        
        logger.info(f"Successfully registered as miner in subnet {subnet_uid}")
        return txn_hash
    except Exception as e:
        logger.error(f"Failed to register as miner: {e}")
        raise

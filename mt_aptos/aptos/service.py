"""
Aptos service functions for ModernTensor.

This module provides various service functions to interact with Aptos blockchain:
- Staking operations (stake, unstake, claim rewards)
- Transaction operations (sending coins, tokens, transaction submission)
"""

from typing import Optional, Dict, Any, List
from ..account import Account
from ..async_client import RestClient
from ..transactions import (
    EntryFunction,
    TransactionArgument,
    TransactionPayload,
    SignedTransaction
)

from ..config.settings import settings, logger


# Staking Service Functions
async def stake_tokens(
    client: RestClient,
    account: Account,
    contract_address: str,
    amount: int,
    subnet_uid: Optional[int] = None
) -> str:
    """
    Stakes tokens in the ModernTensor staking contract.

    Args:
        client (RestClient): The Aptos REST client
        account (Account): The account performing the staking
        contract_address (str): The address of the ModernTensor contract
        amount (int): Amount of tokens to stake (in smallest unit)
        subnet_uid (int, optional): The subnet ID to stake in. If None, stakes in the default pool.

    Returns:
        str: The transaction hash of the staking transaction

    Raises:
        Exception: If the transaction submission fails
    """
    # Format the contract address
    if not contract_address.startswith("0x"):
        contract_address = f"0x{contract_address}"

    # Create transaction arguments
    args = [
        TransactionArgument(amount, TransactionArgument.U64),
    ]
    
    # Add subnet_uid if provided
    if subnet_uid is not None:
        args.append(TransactionArgument(subnet_uid, TransactionArgument.U64))

    # Function name depends on whether subnet_uid is provided
    function_name = "stake_tokens" if subnet_uid is None else "stake_in_subnet"

    # Create transaction payload
    payload = TransactionPayload(
        EntryFunction.natural(
            f"{contract_address}::moderntensor",
            function_name,
            [],  # Type arguments (empty for this function)
            args
        )
    )

    try:
        # Submit transaction
        logger.info(f"Submitting {function_name} transaction for account {account.address().hex()}")
        txn_hash = await client.submit_transaction(account, payload)
        
        # Wait for transaction confirmation
        await client.wait_for_transaction(txn_hash)
        
        logger.info(f"Successfully staked {amount} tokens")
        return txn_hash
    except Exception as e:
        logger.error(f"Failed to stake tokens: {e}")
        raise


async def unstake_tokens(
    client: RestClient,
    account: Account,
    contract_address: str,
    amount: int,
    subnet_uid: Optional[int] = None
) -> str:
    """
    Unstakes tokens from the ModernTensor staking contract.

    Args:
        client (RestClient): The Aptos REST client
        account (Account): The account performing the unstaking
        contract_address (str): The address of the ModernTensor contract
        amount (int): Amount of tokens to unstake (in smallest unit)
        subnet_uid (int, optional): The subnet ID to unstake from. If None, unstakes from the default pool.

    Returns:
        str: The transaction hash of the unstaking transaction

    Raises:
        Exception: If the transaction submission fails
    """
    # Format the contract address
    if not contract_address.startswith("0x"):
        contract_address = f"0x{contract_address}"

    # Create transaction arguments
    args = [
        TransactionArgument(amount, TransactionArgument.U64),
    ]
    
    # Add subnet_uid if provided
    if subnet_uid is not None:
        args.append(TransactionArgument(subnet_uid, TransactionArgument.U64))

    # Function name depends on whether subnet_uid is provided
    function_name = "unstake_tokens" if subnet_uid is None else "unstake_from_subnet"

    # Create transaction payload
    payload = TransactionPayload(
        EntryFunction.natural(
            f"{contract_address}::moderntensor",
            function_name,
            [],  # Type arguments (empty for this function)
            args
        )
    )

    try:
        # Submit transaction
        logger.info(f"Submitting {function_name} transaction for account {account.address().hex()}")
        txn_hash = await client.submit_transaction(account, payload)
        
        # Wait for transaction confirmation
        await client.wait_for_transaction(txn_hash)
        
        logger.info(f"Successfully unstaked {amount} tokens")
        return txn_hash
    except Exception as e:
        logger.error(f"Failed to unstake tokens: {e}")
        raise


async def claim_rewards(
    client: RestClient,
    account: Account,
    contract_address: str,
    subnet_uid: Optional[int] = None
) -> str:
    """
    Claims staking rewards from the ModernTensor staking contract.

    Args:
        client (RestClient): The Aptos REST client
        account (Account): The account claiming rewards
        contract_address (str): The address of the ModernTensor contract
        subnet_uid (int, optional): The subnet ID to claim rewards from. If None, claims from the default pool.

    Returns:
        str: The transaction hash of the claim transaction

    Raises:
        Exception: If the transaction submission fails
    """
    # Format the contract address
    if not contract_address.startswith("0x"):
        contract_address = f"0x{contract_address}"

    # Create transaction arguments
    args = []
    
    # Add subnet_uid if provided
    if subnet_uid is not None:
        args.append(TransactionArgument(subnet_uid, TransactionArgument.U64))

    # Function name depends on whether subnet_uid is provided
    function_name = "claim_rewards" if subnet_uid is None else "claim_subnet_rewards"

    # Create transaction payload
    payload = TransactionPayload(
        EntryFunction.natural(
            f"{contract_address}::moderntensor",
            function_name,
            [],  # Type arguments (empty for this function)
            args
        )
    )

    try:
        # Submit transaction
        logger.info(f"Submitting {function_name} transaction for account {account.address().hex()}")
        txn_hash = await client.submit_transaction(account, payload)
        
        # Wait for transaction confirmation
        await client.wait_for_transaction(txn_hash)
        
        logger.info(f"Successfully claimed rewards")
        return txn_hash
    except Exception as e:
        logger.error(f"Failed to claim rewards: {e}")
        raise


async def get_staking_info(
    client: RestClient,
    account_address: str,
    contract_address: str,
    subnet_uid: Optional[int] = None
) -> Dict[str, Any]:
    """
    Retrieves staking information for an account.

    Args:
        client (RestClient): The Aptos REST client
        account_address (str): The address to query staking info for
        contract_address (str): The address of the ModernTensor contract
        subnet_uid (int, optional): The subnet ID to query info for. If None, retrieves info from the default pool.

    Returns:
        Dict[str, Any]: Staking information including:
            - staked_amount: Amount of tokens staked
            - pending_rewards: Pending rewards available for claiming
            - staking_period: Duration user has been staking
            - other relevant staking metrics
    """
    # Format addresses
    if not account_address.startswith("0x"):
        account_address = f"0x{account_address}"
    if not contract_address.startswith("0x"):
        contract_address = f"0x{contract_address}"

    # Determine the resource name based on whether subnet staking is being queried
    resource_type = (
        f"{contract_address}::moderntensor::StakeInfo" 
        if subnet_uid is None else 
        f"{contract_address}::moderntensor::SubnetStakeInfo"
    )
    
    try:
        # Get the staking resource from the account
        resource = await client.account_resource(account_address, resource_type)
        
        if not resource or "data" not in resource:
            logger.warning(f"No staking data found for {account_address}")
            return {
                "staked_amount": 0,
                "pending_rewards": 0,
                "staking_period": 0
            }
            
        staking_data = resource["data"]
        
        # Process and return the data
        result = {
            "staked_amount": int(staking_data.get("amount", 0)),
            "pending_rewards": int(staking_data.get("pending_rewards", 0)),
            "staking_period": int(staking_data.get("staking_period", 0)),
            # Add other relevant fields from the resource
            "last_claim_time": int(staking_data.get("last_claim_time", 0)),
        }
        
        if subnet_uid is not None:
            result["subnet_uid"] = subnet_uid
            
        return result
    except Exception as e:
        logger.error(f"Failed to get staking info: {e}")
        return {
            "staked_amount": 0,
            "pending_rewards": 0,
            "staking_period": 0,
            "error": str(e)
        }


# Transaction Service Functions
async def send_coin(
    client: RestClient,
    sender: Account,
    recipient_address: str,
    amount: int,
) -> str:
    """
    Sends Aptos Coin (APT) to the specified recipient.

    Args:
        client (RestClient): The Aptos REST client
        sender (Account): The sender's account
        recipient_address (str): The recipient's address
        amount (int): Amount of APT to send in smallest unit (octa, 1 APT = 10^8 octas)

    Returns:
        str: The transaction hash of the submitted transaction

    Raises:
        Exception: If the transaction submission fails
    """
    # Format recipient address
    if not recipient_address.startswith("0x"):
        recipient_address = f"0x{recipient_address}"

    # Create transaction payload for coin transfer
    payload = TransactionPayload(
        EntryFunction.natural(
            "0x1::coin",
            "transfer",
            [TransactionArgument.type_tag("0x1::aptos_coin::AptosCoin")],
            [
                TransactionArgument(recipient_address, TransactionArgument.ADDRESS),
                TransactionArgument(amount, TransactionArgument.U64),
            ]
        )
    )

    try:
        # Submit transaction
        logger.info(f"Sending {amount} octas from {sender.address().hex()} to {recipient_address}")
        txn_hash = await client.submit_transaction(sender, payload)
        
        # Wait for transaction confirmation
        await client.wait_for_transaction(txn_hash)
        
        logger.info(f"Successfully sent coins. Transaction hash: {txn_hash}")
        return txn_hash
    except Exception as e:
        logger.error(f"Failed to send coins: {e}")
        raise


async def send_token(
    client: RestClient,
    sender: Account,
    recipient_address: str,
    token_address: str,
    token_name: str,
    amount: int,
) -> str:
    """
    Sends a specified token to the recipient.

    Args:
        client (RestClient): The Aptos REST client
        sender (Account): The sender's account 
        recipient_address (str): The recipient's address
        token_address (str): The address of the token contract
        token_name (str): The name of the token
        amount (int): Amount of tokens to send in smallest unit

    Returns:
        str: The transaction hash of the submitted transaction

    Raises:
        Exception: If the transaction submission fails
    """
    # Format addresses
    if not recipient_address.startswith("0x"):
        recipient_address = f"0x{recipient_address}"
    if not token_address.startswith("0x"):
        token_address = f"0x{token_address}"

    # Create transaction payload for token transfer
    payload = TransactionPayload(
        EntryFunction.natural(
            "0x1::coin",
            "transfer",
            [TransactionArgument.type_tag(f"{token_address}::{token_name}::{token_name}")],
            [
                TransactionArgument(recipient_address, TransactionArgument.ADDRESS),
                TransactionArgument(amount, TransactionArgument.U64),
            ]
        )
    )

    try:
        # Submit transaction
        logger.info(f"Sending {amount} tokens from {sender.address().hex()} to {recipient_address}")
        txn_hash = await client.submit_transaction(sender, payload)
        
        # Wait for transaction confirmation
        await client.wait_for_transaction(txn_hash)
        
        logger.info(f"Successfully sent tokens. Transaction hash: {txn_hash}")
        return txn_hash
    except Exception as e:
        logger.error(f"Failed to send tokens: {e}")
        raise


async def submit_transaction(
    client: RestClient,
    account: Account,
    payload: TransactionPayload,
    max_gas_amount: Optional[int] = None,
    gas_unit_price: Optional[int] = None,
) -> str:
    """
    Submits a transaction to the Aptos blockchain with optional gas parameters.

    Args:
        client (RestClient): The Aptos REST client
        account (Account): The account performing the transaction
        payload (TransactionPayload): The transaction payload
        max_gas_amount (int, optional): Maximum gas amount to use for the transaction
        gas_unit_price (int, optional): Gas unit price in octas

    Returns:
        str: The transaction hash of the submitted transaction

    Raises:
        Exception: If the transaction submission fails
    """
    try:
        # Get account sequences
        sender_account = await client.account(account.address())
        sequence_number = int(sender_account["sequence_number"])
        
        # Get chain ID
        chain_id = await client.chain_id()
        
        # Create the raw transaction
        raw_transaction = await client.create_bcs_transaction(
            account, 
            payload,
            max_gas_amount=max_gas_amount,
            gas_unit_price=gas_unit_price
        )
        
        # Submit the transaction
        txn_hash = await client.submit_bcs_transaction(raw_transaction)
        
        # Wait for transaction confirmation
        await client.wait_for_transaction(txn_hash)
        
        logger.info(f"Transaction {txn_hash} submitted and confirmed")
        return txn_hash
    except Exception as e:
        logger.error(f"Failed to submit transaction: {e}")
        raise


async def get_transaction_details(
    client: RestClient,
    txn_hash: str
) -> Dict[str, Any]:
    """
    Retrieves details about a transaction by hash.

    Args:
        client (RestClient): The Aptos REST client
        txn_hash (str): The transaction hash to retrieve

    Returns:
        Dict[str, Any]: Dictionary containing transaction details
    """
    # Format hash
    if not txn_hash.startswith("0x"):
        txn_hash = f"0x{txn_hash}"
    
    try:
        # Get transaction details
        txn_details = await client.transaction_by_hash(txn_hash)
        return txn_details
    except Exception as e:
        logger.error(f"Failed to get transaction details for {txn_hash}: {e}")
        return {"error": str(e)}


async def get_account_transactions(
    client: RestClient,
    address: str,
    limit: int = 25
) -> List[Dict[str, Any]]:
    """
    Retrieves transactions for a specific account.

    Args:
        client (RestClient): The Aptos REST client
        address (str): The account address
        limit (int, optional): Maximum number of transactions to return. Defaults to 25.

    Returns:
        List[Dict[str, Any]]: List of transaction data dictionaries
    """
    # Format address
    if not address.startswith("0x"):
        address = f"0x{address}"
    
    try:
        # Get account transactions
        txns = await client.account_transactions(address, limit=limit)
        return txns
    except Exception as e:
        logger.error(f"Failed to get transactions for account {address}: {e}")
        return [] 
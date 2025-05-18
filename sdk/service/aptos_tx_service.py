from typing import Optional, Dict, Any, List
from aptos_sdk.account import Account
from aptos_sdk.async_client import RestClient
from aptos_sdk.transactions import (
    EntryFunction,
    TransactionArgument,
    TransactionPayload,
    SignedTransaction
)

from sdk.config.settings import settings, logger


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
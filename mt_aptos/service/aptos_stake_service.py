from typing import Optional, Dict, Any
from mt_aptos.account import Account
from mt_aptos.async_client import RestClient
from mt_aptos.transactions import EntryFunction, TransactionArgument, TransactionPayload

from mt_aptos.config.settings import settings, logger


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
            # Include other fields as needed based on the actual data structure
        }
        
        logger.info(f"Retrieved staking info for {account_address}: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to get staking information: {e}")
        # Return default values on error
        return {
            "staked_amount": 0,
            "pending_rewards": 0,
            "staking_period": 0,
            "error": str(e)
        } 
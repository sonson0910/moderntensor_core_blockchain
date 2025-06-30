from typing import Optional, Dict, Any
from mt_aptos.account import Account
from mt_aptos.async_client import RestClient
from mt_aptos.transactions import EntryFunction, TransactionArgument, TransactionPayload

from mt_aptos.config.settings import settings, logger


async def register_validator(
    client: RestClient,
    account: Account,
    contract_address: str,
    subnet_uid: int,
    api_endpoint: str,
    stake_amount: int = 0,
    uid: Optional[str] = None,
    wallet_addr_hash: Optional[str] = None,
) -> str:
    """
    Registers an account as a validator in the specified subnet using full ModernTensor contract.

    This function creates and submits a transaction to register the account as
    a validator in the ModernTensor contract on the Aptos blockchain with complete data structure.

    Args:
        client (RestClient): The Aptos REST client
        account (Account): The account to register as a validator
        contract_address (str): The address of the ModernTensor contract
        subnet_uid (int): The ID of the subnet to join
        api_endpoint (str): The API endpoint URL for this validator
        stake_amount (int, optional): Amount of coins to stake in smallest unit. Defaults to 0.
        uid (str, optional): Unique identifier. Auto-generated if not provided.
        wallet_addr_hash (str, optional): Wallet address hash. Auto-generated if not provided.

    Returns:
        str: The transaction hash of the submitted transaction

    Raises:
        Exception: If the transaction submission fails
    """
    # Format the contract address
    if not contract_address.startswith("0x"):
        contract_address = f"0x{contract_address}"

    # Generate UID if not provided
    if uid is None:
        import hashlib
        import time
        uid_data = f"validator_{str(account.address())}_{subnet_uid}_{int(time.time())}"
        uid = hashlib.sha256(uid_data.encode()).hexdigest()[:32]

    # Generate wallet address hash if not provided
    if wallet_addr_hash is None:
        import hashlib
        wallet_addr_hash = hashlib.sha256(str(account.address()).encode()).hexdigest()[:32]

    # Create transaction payload for moderntensor_fa contract (deployed contract)
    from aptos_sdk.bcs import Serializer
    
    # Properly serialize arguments with correct types using BCS
    def serialize_string(s: str) -> bytes:
        ser = Serializer()
        ser.str(s)
        return ser.output()
    
    def serialize_u64(val: int) -> bytes:
        ser = Serializer()
        ser.u64(val)
        return ser.output()
    
    args = [
        serialize_string(uid),
        serialize_u64(subnet_uid),
        serialize_u64(stake_amount),
        serialize_string(api_endpoint),
        serialize_string(wallet_addr_hash),
    ]
    
    # Use proper BCS serialization for mixed argument types
    from aptos_sdk.bcs import Serializer
    from aptos_sdk.account_address import AccountAddress
    from aptos_sdk.transactions import ModuleId
    
    # Serialize arguments with correct types using BCS
    def serialize_string(s: str) -> bytes:
        ser = Serializer()
        ser.str(s)
        return ser.output()
    
    def serialize_u64(val: int) -> bytes:
        ser = Serializer()
        ser.u64(val)
        return ser.output()
    
    # Create serialized arguments with proper types
    serialized_args = [
        serialize_string(uid),           # String
        serialize_u64(subnet_uid),       # u64 raw bytes
        serialize_u64(stake_amount),     # u64 raw bytes  
        serialize_string(api_endpoint),  # String
        serialize_string(wallet_addr_hash) # String
    ]
    
    # Create module ID properly
    module_id = ModuleId(
        AccountAddress.from_str(contract_address),
        "full_moderntensor"
    )
    
    # Create entry function with BCS serialized arguments
    entry_function = EntryFunction(
        module_id,
        "register_validator", 
        [],  # Type arguments (empty for this function)
        serialized_args  # Properly serialized arguments
    )
    
    payload = TransactionPayload(entry_function)

    try:
        # Submit transaction
        logger.info(f"Submitting register_validator transaction for account {str(account.address())}")
        
        # Create and sign transaction
        signed_transaction = await client.create_bcs_signed_transaction(account, payload)
        txn_hash = await client.submit_bcs_transaction(signed_transaction)
        
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
    uid: Optional[str] = None,
    wallet_addr_hash: Optional[str] = None,
) -> str:
    """
    Registers an account as a miner in the specified subnet using full ModernTensor contract.

    This function creates and submits a transaction to register the account as
    a miner in the ModernTensor contract on the Aptos blockchain with complete data structure.

    Args:
        client (RestClient): The Aptos REST client
        account (Account): The account to register as a miner
        contract_address (str): The address of the ModernTensor contract
        subnet_uid (int): The ID of the subnet to join
        api_endpoint (str): The API endpoint URL for this miner
        stake_amount (int, optional): Amount of coins to stake in smallest unit. Defaults to 0.
        uid (str, optional): Unique identifier. Auto-generated if not provided.
        wallet_addr_hash (str, optional): Wallet address hash. Auto-generated if not provided.

    Returns:
        str: The transaction hash of the submitted transaction

    Raises:
        Exception: If the transaction submission fails
    """
    # Format the contract address
    if not contract_address.startswith("0x"):
        contract_address = f"0x{contract_address}"

    # Generate UID if not provided
    if uid is None:
        import hashlib
        import time
        uid_data = f"miner_{str(account.address())}_{subnet_uid}_{int(time.time())}"
        uid = hashlib.sha256(uid_data.encode()).hexdigest()[:32]

    # Generate wallet address hash if not provided
    if wallet_addr_hash is None:
        import hashlib
        wallet_addr_hash = hashlib.sha256(str(account.address()).encode()).hexdigest()[:32]

    # Create transaction payload for moderntensor_fa contract (deployed contract)
    from aptos_sdk.bcs import Serializer
    
    # Properly serialize arguments with correct types using BCS
    def serialize_string(s: str) -> bytes:
        ser = Serializer()
        ser.str(s)
        return ser.output()
    
    def serialize_u64(val: int) -> bytes:
        ser = Serializer()
        ser.u64(val)
        return ser.output()
    
    args = [
        serialize_string(uid),
        serialize_u64(subnet_uid),
        serialize_u64(stake_amount),
        serialize_string(api_endpoint),
        serialize_string(wallet_addr_hash),
    ]
    
    # Use proper BCS serialization for mixed argument types
    from aptos_sdk.bcs import Serializer
    from aptos_sdk.account_address import AccountAddress
    from aptos_sdk.transactions import ModuleId
    
    # Serialize arguments with correct types using BCS
    def serialize_string(s: str) -> bytes:
        ser = Serializer()
        ser.str(s)
        return ser.output()
    
    def serialize_u64(val: int) -> bytes:
        ser = Serializer()
        ser.u64(val)
        return ser.output()
    
    # Create serialized arguments with proper types
    serialized_args = [
        serialize_string(uid),           # String
        serialize_u64(subnet_uid),       # u64 raw bytes
        serialize_u64(stake_amount),     # u64 raw bytes
        serialize_string(api_endpoint),  # String
        serialize_string(wallet_addr_hash) # String
    ]
    
    # Create module ID properly
    module_id = ModuleId(
        AccountAddress.from_str(contract_address),
        "full_moderntensor"
    )
    
    # Create entry function with BCS serialized arguments
    entry_function = EntryFunction(
        module_id,
        "register_miner",
        [],  # Type arguments (empty for this function)
        serialized_args  # Properly serialized arguments
    )
    
    payload = TransactionPayload(entry_function)

    try:
        # Submit transaction
        logger.info(f"Submitting register_miner transaction for account {str(account.address())}")
        
        # Create and sign transaction
        signed_transaction = await client.create_bcs_signed_transaction(account, payload)
        txn_hash = await client.submit_bcs_transaction(signed_transaction)
        
        # Wait for transaction confirmation
        await client.wait_for_transaction(txn_hash)
        
        logger.info(f"Successfully registered as miner in subnet {subnet_uid}")
        return txn_hash
    except Exception as e:
        logger.error(f"Failed to register as miner: {e}")
        raise

from typing import Optional, Dict, Any
from web3 import Web3
from eth_account import Account

from ..config.settings import settings, logger
from ..core_client.contract_client import ModernTensorCoreClient


async def register_validator(
    client: ModernTensorCoreClient,
    account: Account,
    contract_address: str,
    subnet_uid: int,
    api_endpoint: str,
    stake_amount: int = 0,
    uid: Optional[str] = None,
    wallet_addr_hash: Optional[str] = None,
) -> str:
    """
    Registers an account as a validator in the specified subnet using ModernTensor contract.

    This function creates and submits a transaction to register the account as
    a validator in the ModernTensor contract on the Core blockchain.

    Args:
        client (ModernTensorCoreClient): The Core blockchain client
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

        uid_data = f"validator_{str(account.address)}_{subnet_uid}_{int(time.time())}"
        uid = hashlib.sha256(uid_data.encode()).hexdigest()[:32]

    # Generate wallet address hash if not provided
    if wallet_addr_hash is None:
        import hashlib

        wallet_addr_hash = hashlib.sha256(str(account.address).encode()).hexdigest()[
            :32
        ]

    try:
        # Submit transaction using Core blockchain client
        logger.info(
            f"Submitting register_validator transaction for account {account.address}"
        )

        txn_hash = await client.register_validator(
            subnet_uid=subnet_uid,
            api_endpoint=api_endpoint,
            stake_amount=stake_amount,
            account=account,
            uid=uid,
            wallet_addr_hash=wallet_addr_hash,
        )

        logger.info(f"Successfully registered as validator in subnet {subnet_uid}")
        return txn_hash
    except Exception as e:
        logger.error(f"Failed to register as validator: {e}")
        raise


async def register_miner(
    client: ModernTensorCoreClient,
    account: Account,
    contract_address: str,
    subnet_uid: int,
    api_endpoint: str,
    stake_amount: int = 0,
    uid: Optional[str] = None,
    wallet_addr_hash: Optional[str] = None,
) -> str:
    """
    Registers an account as a miner in the specified subnet using ModernTensor contract.

    This function creates and submits a transaction to register the account as
    a miner in the ModernTensor contract on the Core blockchain.

    Args:
        client (ModernTensorCoreClient): The Core blockchain client
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

        uid_data = f"miner_{str(account.address)}_{subnet_uid}_{int(time.time())}"
        uid = hashlib.sha256(uid_data.encode()).hexdigest()[:32]

    # Generate wallet address hash if not provided
    if wallet_addr_hash is None:
        import hashlib

        wallet_addr_hash = hashlib.sha256(str(account.address).encode()).hexdigest()[
            :32
        ]

    try:
        # Submit transaction using Core blockchain client
        logger.info(
            f"Submitting register_miner transaction for account {account.address}"
        )

        txn_hash = await client.register_miner(
            subnet_uid=subnet_uid,
            api_endpoint=api_endpoint,
            stake_amount=stake_amount,
            account=account,
            uid=uid,
            wallet_addr_hash=wallet_addr_hash,
        )

        logger.info(f"Successfully registered as miner in subnet {subnet_uid}")
        return txn_hash
    except Exception as e:
        logger.error(f"Failed to register as miner: {e}")
        raise

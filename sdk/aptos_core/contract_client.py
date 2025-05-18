"""
Aptos contract client for interacting with ModernTensor smart contracts on Aptos blockchain.
This replaces BlockFrostChainContext and PyCardano-specific functionality.
"""

import logging
import time
from typing import List, Dict, Any, Optional, Union, Tuple
import asyncio

from aptos_sdk.account import Account
from aptos_sdk.async_client import RestClient
from aptos_sdk.bcs import Serializer
from aptos_sdk.transactions import (
    EntryFunction,
    TransactionArgument,
    TransactionPayload,
    SignedTransaction,
)
from aptos_sdk.type_tag import TypeTag, StructTag

from sdk.core.datatypes import MinerInfo, ValidatorInfo
from sdk.config.settings import settings

logger = logging.getLogger(__name__)


class AptosContractClient:
    """
    Client for interacting with ModernTensor smart contracts on Aptos blockchain.
    Handles transaction submission, resource fetching, and other blockchain operations.
    """

    def __init__(
        self,
        client: RestClient,
        account: Account,
        contract_address: str,
        max_gas_amount: int = 100000,
        gas_unit_price: int = 100,
    ):
        """
        Initialize the Aptos contract client.

        Args:
            client (RestClient): Aptos REST client instance
            account (Account): Aptos account to use for transactions
            contract_address (str): ModernTensor contract address on Aptos
            max_gas_amount (int): Maximum gas amount for transactions
            gas_unit_price (int): Gas unit price for transactions
        """
        self.client = client
        self.account = account
        self.contract_address = contract_address
        self.max_gas_amount = max_gas_amount
        self.gas_unit_price = gas_unit_price

    async def get_account_resources(self, address: str) -> List[Dict]:
        """
        Get all resources for an account.

        Args:
            address (str): Account address to get resources for

        Returns:
            List[Dict]: List of resources
        """
        try:
            resources = await self.client.get_account_resources(address)
            return resources
        except Exception as e:
            logger.error(f"Failed to get resources for account {address}: {e}")
            return []

    async def submit_transaction(
        self,
        function_name: str,
        type_args: List[TypeTag],
        args: List[TransactionArgument],
    ) -> str:
        """
        Submit a transaction to call a Move function.

        Args:
            function_name (str): Name of the function to call
            type_args (List[TypeTag]): Type arguments for the function
            args (List[TransactionArgument]): Arguments for the function

        Returns:
            str: Transaction hash if successful, None otherwise
        """
        try:
            payload = EntryFunction.natural(
                f"{self.contract_address}::moderntensor",
                function_name,
                type_args,
                args,
            )

            txn_hash = await self.client.submit_transaction(
                self.account, TransactionPayload(payload)
            )
            
            # Wait for transaction to be confirmed
            await self.client.wait_for_transaction(txn_hash)
            return txn_hash
        except Exception as e:
            logger.error(f"Failed to submit transaction {function_name}: {e}")
            return None

    async def find_resource_by_uid(
        self,
        account_address: str,
        resource_type: str,
        uid_bytes: bytes,
    ) -> Optional[Dict[str, Any]]:
        """
        Find a resource by its UID.

        Args:
            account_address (str): Address of the account that might have the resource
            resource_type (str): Type of resource to look for
            uid_bytes (bytes): UID as bytes to search for

        Returns:
            Optional[Dict[str, Any]]: Resource data if found, None otherwise
        """
        logger.debug(
            f"Searching for resource {resource_type} with UID {uid_bytes.hex()} for account {account_address}..."
        )
        
        try:
            # Format resource full path
            full_resource_type = f"{self.contract_address}::{resource_type}"
            
            # Get resources from account
            resources = await self.client.get_account_resources(account_address)
            
            # Filter resources by type
            for resource in resources:
                if resource["type"] == full_resource_type:
                    # Check UID
                    if resource["data"].get("uid") == uid_bytes.hex():
                        return resource["data"]
            
            logger.warning(
                f"Resource {resource_type} with UID {uid_bytes.hex()} not found for account {account_address}."
            )
            return None
            
        except Exception as e:
            logger.error(
                f"Failed to fetch resources for {account_address} while searching for {resource_type} with UID {uid_bytes.hex()}: {e}"
            )
            return None

    async def update_miner_info(
        self, miner_uid: str, performance: float, trust_score: float
    ) -> Optional[str]:
        """
        Update miner performance and trust score.

        Args:
            miner_uid (str): UID of the miner to update
            performance (float): New performance score
            trust_score (float): New trust score

        Returns:
            Optional[str]: Transaction hash if successful, None otherwise
        """
        try:
            # Convert UID from hex to bytes for serialization
            uid_bytes = bytes.fromhex(miner_uid)
            
            # Prepare arguments
            args = [
                TransactionArgument(uid_bytes, Serializer.bytes),
                TransactionArgument(performance, Serializer.f64),
                TransactionArgument(trust_score, Serializer.f64),
            ]
            
            return await self.submit_transaction(
                "update_miner_performance",
                [],  # No type arguments
                args,
            )
        except Exception as e:
            logger.error(f"Failed to update miner info for {miner_uid}: {e}")
            return None

    async def update_validator_info(
        self, validator_uid: str, performance: float, trust_score: float
    ) -> Optional[str]:
        """
        Update validator performance and trust score.

        Args:
            validator_uid (str): UID of the validator to update
            performance (float): New performance score
            trust_score (float): New trust score

        Returns:
            Optional[str]: Transaction hash if successful, None otherwise
        """
        try:
            # Convert UID from hex to bytes for serialization
            uid_bytes = bytes.fromhex(validator_uid)
            
            # Prepare arguments
            args = [
                TransactionArgument(uid_bytes, Serializer.bytes),
                TransactionArgument(performance, Serializer.f64),
                TransactionArgument(trust_score, Serializer.f64),
            ]
            
            return await self.submit_transaction(
                "update_validator_performance",
                [],  # No type arguments
                args,
            )
        except Exception as e:
            logger.error(f"Failed to update validator info for {validator_uid}: {e}")
            return None

    async def get_miner_info(self, miner_uid: str) -> Optional[MinerInfo]:
        """
        Get miner information from blockchain.

        Args:
            miner_uid (str): UID of the miner to get info for

        Returns:
            Optional[MinerInfo]: MinerInfo object if found, None otherwise
        """
        try:
            uid_bytes = bytes.fromhex(miner_uid)
            
            # Find miner resource in registry
            registry_address = self.contract_address
            miner_data = await self.find_resource_by_uid(
                registry_address,
                "miner::MinerInfo",
                uid_bytes,
            )
            
            if not miner_data:
                logger.warning(f"Miner {miner_uid} not found in registry")
                return None
            
            # Convert resource data to MinerInfo
            miner_info = MinerInfo(
                uid=miner_uid,
                address=miner_data.get("owner", ""),
                api_endpoint=miner_data.get("api_endpoint", ""),
                trust_score=float(miner_data.get("trust_score", 0.0)),
                weight=float(miner_data.get("weight", 0.0)),
                stake=float(miner_data.get("stake", 0.0)),
                status=int(miner_data.get("status", 1)),  # 1 is STATUS_ACTIVE
                subnet_uid=int(miner_data.get("subnet_id", 0)),
                registration_slot=int(miner_data.get("registration_slot", 0)),
            )
            
            return miner_info
            
        except Exception as e:
            logger.error(f"Failed to get miner info for {miner_uid}: {e}")
            return None

    async def get_validator_info(self, validator_uid: str) -> Optional[ValidatorInfo]:
        """
        Get validator information from blockchain.

        Args:
            validator_uid (str): UID of the validator to get info for

        Returns:
            Optional[ValidatorInfo]: ValidatorInfo object if found, None otherwise
        """
        try:
            uid_bytes = bytes.fromhex(validator_uid)
            
            # Find validator resource in registry
            registry_address = self.contract_address
            validator_data = await self.find_resource_by_uid(
                registry_address,
                "validator::ValidatorInfo",
                uid_bytes,
            )
            
            if not validator_data:
                logger.warning(f"Validator {validator_uid} not found in registry")
                return None
            
            # Convert resource data to ValidatorInfo
            validator_info = ValidatorInfo(
                uid=validator_uid,
                address=validator_data.get("owner", ""),
                api_endpoint=validator_data.get("api_endpoint", ""),
                trust_score=float(validator_data.get("trust_score", 0.0)),
                weight=float(validator_data.get("weight", 0.0)),
                stake=float(validator_data.get("stake", 0.0)),
                last_performance=float(validator_data.get("last_performance", 0.0)),
                status=int(validator_data.get("status", 1)),  # 1 is STATUS_ACTIVE
                subnet_uid=int(validator_data.get("subnet_id", 0)),
                registration_slot=int(validator_data.get("registration_slot", 0)),
            )
            
            return validator_info
            
        except Exception as e:
            logger.error(f"Failed to get validator info for {validator_uid}: {e}")
            return None

    async def get_all_miners(self) -> Dict[str, MinerInfo]:
        """
        Get all miners from blockchain.

        Returns:
            Dict[str, MinerInfo]: Dictionary mapping miner UIDs to MinerInfo objects
        """
        try:
            # Get miners registry resource
            resources = await self.client.get_account_resources(self.contract_address)
            miners_registry = None
            
            for resource in resources:
                if "MinerRegistry" in resource["type"]:
                    miners_registry = resource["data"]
                    break
            
            if not miners_registry:
                logger.warning("Miners registry not found")
                return {}
            
            # Get miner UIDs from registry
            miner_uids = miners_registry.get("miner_uids", [])
            
            # Get miner info for each UID
            miners_info = {}
            for uid_hex in miner_uids:
                miner_info = await self.get_miner_info(uid_hex)
                if miner_info:
                    miners_info[uid_hex] = miner_info
            
            return miners_info
            
        except Exception as e:
            logger.error(f"Failed to get all miners: {e}")
            return {}

    async def get_all_validators(self) -> Dict[str, ValidatorInfo]:
        """
        Get all validators from blockchain.

        Returns:
            Dict[str, ValidatorInfo]: Dictionary mapping validator UIDs to ValidatorInfo objects
        """
        try:
            # Get validators registry resource
            resources = await self.client.get_account_resources(self.contract_address)
            validators_registry = None
            
            for resource in resources:
                if "ValidatorRegistry" in resource["type"]:
                    validators_registry = resource["data"]
                    break
            
            if not validators_registry:
                logger.warning("Validators registry not found")
                return {}
            
            # Get validator UIDs from registry
            validator_uids = validators_registry.get("validator_uids", [])
            
            # Get validator info for each UID
            validators_info = {}
            for uid_hex in validator_uids:
                validator_info = await self.get_validator_info(uid_hex)
                if validator_info:
                    validators_info[uid_hex] = validator_info
            
            return validators_info
            
        except Exception as e:
            logger.error(f"Failed to get all validators: {e}")
            return {}

    async def get_current_slot(self) -> int:
        """
        Get current blockchain slot/timestamp.
        In Aptos, we use block height or timestamp as equivalent.

        Returns:
            int: Current blockchain timestamp
        """
        try:
            ledger_info = await self.client.get_ledger_information()
            return int(ledger_info["block_height"])
        except Exception as e:
            logger.error(f"Failed to get current slot: {e}")
            return int(time.time())  # Fallback to system time

# Function to create a new Aptos client
async def create_aptos_client(
    contract_address: str,
    node_url: str = "https://fullnode.testnet.aptoslabs.com/v1",
    private_key: Optional[str] = None,
) -> Tuple[AptosContractClient, RestClient, Account]:
    """
    Create a new Aptos contract client.

    Args:
        contract_address (str): ModernTensor contract address on Aptos
        node_url (str): URL of the Aptos node to connect to
        private_key (Optional[str]): Private key for signing transactions

    Returns:
        Tuple[AptosContractClient, RestClient, Account]: Contract client, REST client, and Account
    """
    # Create REST client
    rest_client = RestClient(node_url)
    
    # Create or load account
    if private_key:
        account = Account.load_key(private_key)
    else:
        # Use private key from settings if available
        account = Account.load_key(settings.APTOS_PRIVATE_KEY)
    
    # Create contract client
    contract_client = AptosContractClient(
        rest_client,
        account,
        contract_address,
    )
    
    return contract_client, rest_client, account 
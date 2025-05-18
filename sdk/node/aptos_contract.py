"""
Aptos contract interaction for ModernTensor node operations.

This module provides node-specific functionality for interacting with ModernTensor contracts on Aptos.
"""

from typing import Dict, Any, List, Optional
from aptos_sdk.account import Account
from aptos_sdk.async_client import RestClient
from aptos_sdk.transactions import (
    EntryFunction,
    TransactionArgument,
    TransactionPayload
)

from sdk.config.settings import settings, logger
from sdk.aptos import ModernTensorClient


class AptosContractManager:
    """Manager for interacting with ModernTensor contracts on Aptos."""
    
    def __init__(
        self, 
        account: Account, 
        client: RestClient,
        contract_address: str = None
    ):
        """
        Initialize the Aptos contract manager.
        
        Args:
            account (Account): The Aptos account to use for transactions
            client (RestClient): The Aptos REST client
            contract_address (str, optional): ModernTensor contract address
        """
        self.account = account
        self.client = client
        self.contract_address = contract_address or settings.APTOS_CONTRACT_ADDRESS
        
        # Ensure contract address has 0x prefix
        if not self.contract_address.startswith("0x"):
            self.contract_address = f"0x{self.contract_address}"
            
        # Create ModernTensorClient instance
        self.moderntensor_client = ModernTensorClient(
            account=account,
            client=client,
            contract_address=self.contract_address
        )
    
    async def get_subnet_info(self, subnet_uid: int) -> Dict[str, Any]:
        """
        Get information about a subnet.
        
        Args:
            subnet_uid (int): The subnet UID
            
        Returns:
            Dict[str, Any]: Subnet information
        """
        return await self.moderntensor_client.get_subnet_info(subnet_uid)
    
    async def get_miner_info(self, miner_uid: bytes) -> Dict[str, Any]:
        """
        Get information about a miner.
        
        Args:
            miner_uid (bytes): The miner UID
            
        Returns:
            Dict[str, Any]: Miner information
        """
        return await self.moderntensor_client.get_miner_info(miner_uid)
    
    async def get_validator_info(self, validator_uid: bytes) -> Dict[str, Any]:
        """
        Get information about a validator.
        
        Args:
            validator_uid (bytes): The validator UID
            
        Returns:
            Dict[str, Any]: Validator information
        """
        return await self.moderntensor_client.get_validator_info(validator_uid)
    
    async def submit_miner_result(
        self, 
        task_uid: bytes, 
        result_hash: bytes, 
        subnet_uid: int
    ) -> str:
        """
        Submit a result for a mining task.
        
        Args:
            task_uid (bytes): The task UID
            result_hash (bytes): Hash of the result
            subnet_uid (int): The subnet UID
            
        Returns:
            str: Transaction hash
        """
        return await self.moderntensor_client.submit_miner_result(
            task_uid=task_uid,
            result_hash=result_hash,
            subnet_uid=subnet_uid
        )
    
    async def submit_validator_score(
        self,
        miner_uid: bytes,
        task_uid: bytes,
        score: int,
        subnet_uid: int
    ) -> str:
        """
        Submit a validation score for a miner result.
        
        Args:
            miner_uid (bytes): The miner UID
            task_uid (bytes): The task UID
            score (int): Score value (0-100)
            subnet_uid (int): The subnet UID
            
        Returns:
            str: Transaction hash
        """
        return await self.moderntensor_client.submit_validator_score(
            miner_uid=miner_uid,
            task_uid=task_uid,
            score=score,
            subnet_uid=subnet_uid
        )

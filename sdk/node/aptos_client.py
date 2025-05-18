"""
Aptos client for ModernTensor node operations.

This module provides a client wrapper around the Aptos SDK for node-specific operations.
"""

from typing import Dict, Any, Optional
from aptos_sdk.account import Account
from aptos_sdk.async_client import RestClient

from sdk.config.settings import settings, logger


class AptosClient:
    """Client for interacting with the Aptos blockchain."""
    
    def __init__(
        self, 
        account: Account = None, 
        network: str = None,
        node_url: str = None
    ):
        """
        Initialize the Aptos client.
        
        Args:
            account (Account, optional): The Aptos account to use for transactions
            network (str, optional): The network to connect to (mainnet, testnet, devnet, local)
            node_url (str, optional): Custom node URL to use instead of network
        """
        self.account = account
        
        # Set up the REST client
        if node_url:
            self.node_url = node_url
        else:
            network = network or settings.APTOS_NETWORK
            if network == "mainnet":
                self.node_url = "https://fullnode.mainnet.aptoslabs.com/v1"
            elif network == "testnet":
                self.node_url = "https://fullnode.testnet.aptoslabs.com/v1"
            elif network == "devnet":
                self.node_url = "https://fullnode.devnet.aptoslabs.com/v1"
            else:
                # Default to local node
                self.node_url = "http://localhost:8080/v1"
        
        self.client = RestClient(self.node_url)
    
    async def get_account_resources(self, address: Optional[str] = None) -> Dict[str, Any]:
        """
        Get all resources for an account.
        
        Args:
            address (str, optional): The account address. If None, uses the client's account.
            
        Returns:
            Dict[str, Any]: The account resources
        """
        addr = address or self.account.address().hex()
        if not addr.startswith("0x"):
            addr = f"0x{addr}"
            
        return await self.client.account_resources(addr)
    
    async def get_account_balance(self, address: Optional[str] = None) -> int:
        """
        Get the APT balance for an account.
        
        Args:
            address (str, optional): The account address. If None, uses the client's account.
            
        Returns:
            int: The account balance in octas
        """
        addr = address or self.account.address().hex()
        resources = await self.get_account_resources(addr)
        
        # Find the CoinStore resource
        for resource in resources:
            if resource["type"] == "0x1::coin::CoinStore<0x1::aptos_coin::AptosCoin>":
                return int(resource["data"]["coin"]["value"])
        
        return 0

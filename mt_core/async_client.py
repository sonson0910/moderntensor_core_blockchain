"""
Core blockchain async client implementation for ModernTensor
Provides async HTTP client functionality for Core blockchain interactions
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
import aiohttp
import json
from web3 import Web3, AsyncWeb3
from web3.providers import HTTPProvider
from eth_account import Account

from .config.config_loader import get_config

logger = logging.getLogger(__name__)


class CoreAsyncClient:
    """Async client for Core blockchain interactions"""

    def __init__(self, rpc_url: str = None, timeout: int = 30):
        if rpc_url is None:
            config = get_config()
            rpc_url = config.get_node_url()
        self.rpc_url = rpc_url
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None
        self.web3 = None

    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    async def connect(self):
        """Initialize async connection"""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(timeout=timeout)

        # Initialize Web3 provider with sync HTTPProvider
        provider = HTTPProvider(self.rpc_url)
        self.web3 = Web3(provider)
        logger.info(f"Connected to Core blockchain: {self.rpc_url}")

    async def close(self):
        """Close async connections"""
        if self.session:
            await self.session.close()
            self.session = None
        logger.info("Core async client disconnected")

    async def get_balance(self, address: str) -> float:
        """Get ETH balance for address"""
        if not self.web3:
            await self.connect()

        balance_wei = self.web3.eth.get_balance(address)
        return self.web3.from_wei(balance_wei, "ether")

    async def get_token_balance(self, address: str, token_address: str) -> float:
        """Get ERC20 token balance"""
        if not self.web3:
            await self.connect()

        # ERC20 balanceOf function call
        contract_abi = [
            {
                "constant": True,
                "inputs": [{"name": "owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "", "type": "uint256"}],
                "type": "function",
            },
            {
                "constant": True,
                "inputs": [],
                "name": "decimals",
                "outputs": [{"name": "", "type": "uint8"}],
                "type": "function",
            },
        ]

        contract = self.web3.eth.contract(address=token_address, abi=contract_abi)

        balance_raw = contract.functions.balanceOf(address).call()
        decimals = contract.functions.decimals().call()

        return balance_raw / (10**decimals)

    async def send_transaction(self, signed_transaction) -> str:
        """Send signed transaction"""
        if not self.web3:
            await self.connect()

        tx_hash = self.web3.eth.send_raw_transaction(signed_transaction.rawTransaction)
        return tx_hash.hex()

    async def wait_for_transaction(
        self, tx_hash: str, timeout: int = 120
    ) -> Dict[str, Any]:
        """Wait for transaction confirmation"""
        if not self.web3:
            await self.connect()

        receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)
        return dict(receipt)

    async def call_contract_function(
        self,
        contract_address: str,
        function_abi: Dict,
        function_name: str,
        args: List = None,
    ) -> Any:
        """Call read-only contract function"""
        if not self.web3:
            await self.connect()

        contract = self.web3.eth.contract(address=contract_address, abi=[function_abi])
        function = getattr(contract.functions, function_name)

        if args:
            return function(*args).call()
        else:
            return function().call()

    async def estimate_gas(self, transaction: Dict) -> int:
        """Estimate gas for transaction"""
        if not self.web3:
            await self.connect()

        return self.web3.eth.estimate_gas(transaction)

    async def get_transaction_count(self, address: str) -> int:
        """Get nonce for address"""
        if not self.web3:
            await self.connect()

        return self.web3.eth.get_transaction_count(address)

    async def get_gas_price(self) -> int:
        """Get current gas price"""
        if not self.web3:
            await self.connect()

        return self.web3.eth.gas_price


# Convenience functions
async def get_async_client(rpc_url: str = None) -> CoreAsyncClient:
    """Get connected async client"""
    client = CoreAsyncClient(rpc_url)
    await client.connect()
    return client


async def execute_async_call(rpc_url: str, call_func):
    """Execute async call with auto cleanup"""
    async with CoreAsyncClient(rpc_url) as client:
        return await call_func(client)

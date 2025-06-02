"""
Context provider for Aptos blockchain interaction.
Replaces the Cardano-specific context used in the original implementation.
"""

import logging
from typing import Optional, Tuple

from mt_aptos.async_client import RestClient
from mt_aptos.account import Account

from mt_aptos.config.settings import settings
from .contract_client import AptosContractClient, create_aptos_client

logger = logging.getLogger(__name__)


async def get_aptos_context(
    node_url: Optional[str] = None,
    private_key: Optional[str] = None,
    contract_address: Optional[str] = None,
) -> Tuple[AptosContractClient, RestClient, Account]:
    """
    Returns a context for interacting with the Aptos blockchain.

    Args:
        node_url (Optional[str]): URL of the Aptos node to connect to. Defaults to settings.APTOS_NODE_URL.
        private_key (Optional[str]): Private key for signing transactions. Defaults to settings.APTOS_PRIVATE_KEY.
        contract_address (Optional[str]): ModernTensor contract address. Defaults to settings.APTOS_CONTRACT_ADDRESS.

    Returns:
        Tuple[AptosContractClient, RestClient, Account]: Contract client, REST client, and Account
    """
    # Use settings if parameters are not provided
    node_url = node_url or getattr(settings, "APTOS_NODE_URL", "https://fullnode.testnet.aptoslabs.com/v1")
    contract_address = contract_address or getattr(settings, "APTOS_CONTRACT_ADDRESS", None)
    
    if not contract_address:
        raise ValueError("Contract address must be provided or set in settings.APTOS_CONTRACT_ADDRESS")
    
    logger.info(
        f"Initializing Aptos context with node_url={node_url}, contract_address={contract_address}"
    )
    
    # Create client
    client, rest_client, account = await create_aptos_client(
        contract_address=contract_address,
        node_url=node_url,
        private_key=private_key,
    )
    
    return client, rest_client, account 
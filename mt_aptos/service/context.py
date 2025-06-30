# sdk/service/context.py

from mt_aptos.async_client import RestClient
from mt_aptos.config.settings import settings, logger


async def get_aptos_context(network_type="testnet"):
    """
    Returns a REST client for interacting with the Aptos blockchain.

    This function creates and configures an Aptos REST client to
    connect to either testnet, devnet, or mainnet.

    Args:
        network_type (str): The network to connect to: "testnet", "devnet",
                        or "mainnet". Default is "testnet".

    Raises:
        ValueError: If an unsupported network type is specified.

    Returns:
        RestClient: An Aptos REST client configured for the specified network.
    """
    # Determine the base URL depending on the network type
    if network_type.lower() == "mainnet":
        base_url = "https://fullnode.mainnet.aptoslabs.com/v1"
    elif network_type.lower() == "testnet":
        base_url = "https://fullnode.testnet.aptoslabs.com/v1"
    elif network_type.lower() == "devnet":
        base_url = "https://fullnode.devnet.aptoslabs.com/v1"
    else:
        raise ValueError(f"Unsupported Aptos network type: {network_type}")

    # Initialize the REST client with the appropriate base URL
    client = RestClient(base_url)
    
    try:
        # Test the connection by fetching the chain ID
        chain_id = await client.chain_id()
        logger.info(f"Connected to Aptos {network_type} (Chain ID: {chain_id})")
        return client
    except Exception as e:
        logger.error(f"Failed to connect to Aptos {network_type}: {e}")
        raise


# Legacy alias for backward compatibility
get_chain_context = get_aptos_context

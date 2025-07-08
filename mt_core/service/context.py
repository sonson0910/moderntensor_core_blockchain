# sdk/service/context.py

from ..core_client.contract_client import ModernTensorCoreClient
from ..config.settings import settings, logger


async def get_core_context(network_type="testnet"):
    """
    Returns a Core blockchain client for interacting with the Core blockchain.

    This function creates and configures a Core blockchain client to
    connect to either testnet or mainnet.

    Args:
        network_type (str): The network to connect to: "testnet" or "mainnet".
                           Default is "testnet".

    Raises:
        ValueError: If an unsupported network type is specified.

    Returns:
        ModernTensorCoreClient: A Core blockchain client configured for the specified network.
    """
    # Determine the RPC URL depending on the network type
    if network_type.lower() == "mainnet":
        rpc_url = "https://rpc.coredao.org"
    elif network_type.lower() == "testnet":
        rpc_url = "https://rpc.test.btcs.network"
    else:
        raise ValueError(f"Unsupported Core network type: {network_type}")

        # Initialize Web3 connection
    from web3 import Web3

    w3 = Web3(Web3.HTTPProvider(rpc_url))

    try:
        # Test the connection by fetching the chain ID
        chain_id = w3.eth.chain_id
        logger.info(f"Connected to Core {network_type} (Chain ID: {chain_id})")

        # Initialize the Core client with the Web3 instance
        client = ModernTensorCoreClient(
            w3=w3,
            contract_address=getattr(
                settings,
                "CONTRACT_ADDRESS",
                "0x0000000000000000000000000000000000000000",
            ),
            account=None,  # No account needed for query operations
        )

        return client
    except Exception as e:
        logger.error(f"Failed to connect to Core {network_type}: {e}")
        raise


# Legacy alias for backward compatibility
get_chain_context = get_core_context

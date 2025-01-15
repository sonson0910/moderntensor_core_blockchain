# sdk/service/context.py

import os
from pycardano import BlockFrostChainContext, Network

def get_blockfrost_chain_context(project_id: str, network: Network):
    """
    Creates and returns a BlockFrostChainContext object.

    This function determines the appropriate Blockfrost API base URL 
    depending on whether the given network is MAINNET or TESTNET. It then 
    initializes a BlockFrostChainContext instance with the provided 
    project_id (which is your API key for Blockfrost) and the corresponding 
    base URL.

    Args:
        project_id (str): The Blockfrost project ID (API key) associated with your account.
        network (Network): A pycardano Network enum (MAINNET or TESTNET).

    Returns:
        BlockFrostChainContext: An instance of BlockFrostChainContext configured for 
                                the specified network.
    """
    # Select the base Blockfrost API URL depending on the network
    base_url = (
        "https://cardano-mainnet.blockfrost.io/api/"
        if network == Network.MAINNET
        else "https://cardano-preprod.blockfrost.io/api/"
    )
    # Initialize and return the context object
    return BlockFrostChainContext(project_id=project_id, base_url=base_url)


def get_chain_context(
    method: str = "blockfrost",
    project_id: str = "",
    network: Network = Network.TESTNET
):
    """
    Returns a chain context object for interacting with the Cardano blockchain.

    Currently, only the "blockfrost" method is supported, which uses the 
    BlockFrostChainContext class from pycardano. The function is designed 
    to be extensible, so additional methods could be implemented in the future.

    Args:
        method (str): The name of the method to use for chain context creation.
                      Default is "blockfrost".
        project_id (str): The Blockfrost project ID (API key). 
                          Required if method is "blockfrost".
        network (Network): The Cardano network to connect to 
                           (MAINNET or TESTNET). Default is TESTNET.

    Raises:
        ValueError: If an unsupported method is specified.

    Returns:
        BlockFrostChainContext: If method is "blockfrost", returns a context configured
                                for the specified network.
    """
    # For now, we only support using Blockfrost
    if method == "blockfrost":
        # Create and return a BlockFrostChainContext
        return get_blockfrost_chain_context(project_id, network)
    else:
        # If an unsupported method is requested, raise an error
        raise ValueError(f"Unsupported chain context method: {method}")

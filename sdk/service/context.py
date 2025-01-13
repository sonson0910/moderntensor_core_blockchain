# sdk/service/context.py

import os
from pycardano import BlockFrostChainContext, Network

def get_blockfrost_chain_context(project_id: str, network: Network):
    """
    Return BlockFrostChainContext based on project_id and network (MAINNET / TESTNET).
    """
    base_url = (
        "https://cardano-mainnet.blockfrost.io/api/"
        if network == Network.MAINNET
        else "https://cardano-preprod.blockfrost.io/api/"
    )
    return BlockFrostChainContext(project_id=project_id, base_url=base_url)

def get_chain_context(
    method: str = "blockfrost",
    project_id: str = "",
    network: Network = Network.TESTNET
):
    """
    Only supports "blockfrost".
    """
    if method == "blockfrost":
        return get_blockfrost_chain_context(project_id, network)
    else:
        raise ValueError(f"Unsupported chain context method: {method}")

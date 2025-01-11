# sdk/node/cardano_service/context.py

import os
from pycardano import BlockFrostChainContext, OgmiOSChainContext, Network

def get_blockfrost_chain_context(project_id: str, network: Network):
    """
    Trả về BlockFrostChainContext theo project_id và network (MAINNET / TESTNET).
    """
    base_url = (
        "https://cardano-mainnet.blockfrost.io/api/v0"
        if network == Network.MAINNET
        else "https://cardano-preprod.blockfrost.io/api/v0"
    )
    return BlockFrostChainContext(project_id=project_id, base_url=base_url)

def get_ogmios_chain_context(ogmios_host: str, ogmios_port: int, network: Network):
    """
    Ví dụ: Tạo OgmiOSChainContext nếu bạn kết nối node local qua Ogmios.
    """
    return OgmiOSChainContext(f"ws://{ogmios_host}:{ogmios_port}", network=network)

def get_chain_context(
    method: str = "blockfrost",
    project_id: str = "",
    host: str = "localhost",
    port: int = 1337,
    network: Network = Network.TESTNET
):
    """
    Hàm tiện ích: Tùy method "blockfrost" hoặc "ogmios" => trả về chain_context.
    """
    if method == "blockfrost":
        return get_blockfrost_chain_context(project_id, network)
    elif method == "ogmios":
        return get_ogmios_chain_context(host, port, network)
    else:
        raise ValueError(f"Unsupported chain context method: {method}")

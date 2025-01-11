# sdk/node/cardano_service/query_service.py

import logging
from typing import Dict
from pycardano import Address, Value

logger = logging.getLogger(__name__)

def get_address_info(address_str: str, chain_context) -> Dict:
    """
    Lấy thông tin UTxO, tổng lovelace, token balances cho 1 địa chỉ.
    chain_context: BlockFrostChainContext / OgmiOSChainContext
    """
    address = Address.from_primitive(address_str)
    utxos = chain_context.utxos(address)

    total_lovelace = 0
    token_balances = {}

    for utxo in utxos:
        val: Value = utxo.output.amount
        total_lovelace += val.coin
        if val.multi_asset:
            for policy, asset_map in val.multi_asset.items():
                for asset_name, amt in asset_map.items():
                    key = (policy, asset_name)
                    token_balances[key] = token_balances.get(key, 0) + amt

    result = {
        "address": address_str,
        "lovelace": total_lovelace,
        "tokens": token_balances,
        "utxo_count": len(utxos),
    }
    logger.info(f"[get_address_info] {result}")
    return result

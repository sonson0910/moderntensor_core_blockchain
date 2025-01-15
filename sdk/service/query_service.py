# sdk/node/cardano_service/query_service.py

import logging
from typing import Dict
from pycardano import Address, Value

logger = logging.getLogger(__name__)

def get_address_info(address_str: str, chain_context) -> Dict:
    """
    Retrieve information about a Cardano address, including:
      - The total amount of lovelace (ADA) held at the address.
      - The balances of any additional native tokens.
      - The total number of UTxOs (unspent transaction outputs).

    Args:
        address_str (str): A bech32 or base58-encoded Cardano address.
        chain_context: A chain context, such as a BlockFrostChainContext or OgmiOSChainContext,
                       which provides the ability to query UTxOs.

    Returns:
        Dict: A dictionary containing:
              {
                "address": <the original address_str>,
                "lovelace": <total ADA in lovelace>,
                "tokens": {
                    (policy_id, asset_name): amount,
                    ...
                },
                "utxo_count": <number_of_utxos>
              }
    """
    # Convert the address string into a pycardano Address object
    address = Address.from_primitive(address_str)

    # Query the UTxOs for the address using the provided chain_context
    utxos = chain_context.utxos(address)

    # Initialize counters for total lovelace and token balances
    total_lovelace = 0
    token_balances = {}

    # Loop through each UTxO to aggregate lovelace and multi-asset tokens
    for utxo in utxos:
        val: Value = utxo.output.amount  # The Value object in pycardano represents coin + multi-asset
        # Add this UTxO's coin (lovelace) amount to the running total
        total_lovelace += val.coin
        
        # If there are any native tokens in this UTxO (multi_asset), aggregate them
        if val.multi_asset:
            for policy, asset_map in val.multi_asset.items():
                for asset_name, amt in asset_map.items():
                    # Use a (policy, asset_name) tuple as the key in the token_balances dict
                    key = (policy, asset_name)
                    token_balances[key] = token_balances.get(key, 0) + amt

    # Prepare the result dictionary
    result = {
        "address": address_str,
        "lovelace": total_lovelace,
        "tokens": token_balances,
        "utxo_count": len(utxos),
    }
    
    # Log the result for debugging or informational purposes
    logger.info(f"[get_address_info] {result}")
    
    # Return the summarized address information
    return result

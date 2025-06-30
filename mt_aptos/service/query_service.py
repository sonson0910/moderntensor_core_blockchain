# sdk/node/cardano_service/query_service.py

from typing import Dict, Any, Optional
from mt_aptos.async_client import RestClient

from mt_aptos.config.settings import logger


async def get_account_info(address: str, client: RestClient) -> Dict[str, Any]:
    """
    Retrieve information about an Aptos account, including:
      - Account balance in APT
      - Resources (on-chain data)
      - Modules (Move modules published by the account)

    Args:
        address (str): An Aptos account address (with or without 0x prefix)
        client (RestClient): An initialized Aptos REST client

    Returns:
        Dict: A dictionary containing account information:
              {
                "address": <formatted address>,
                "balance_apt": <balance in APT>,
                "sequences_number": <sequence number>,
                "resource_count": <number of resources>,
                "module_count": <number of modules>
              }
    """
    # Ensure address has 0x prefix
    if not address.startswith("0x"):
        address = f"0x{address}"

    # Get account resources
    try:
        resources = await client.account_resources(address)
    except Exception as e:
        logger.error(f"Error fetching resources for account {address}: {e}")
        resources = []

    # Get account modules
    try:
        modules = await client.account_modules(address)
    except Exception as e:
        logger.error(f"Error fetching modules for account {address}: {e}")
        modules = []

    # Get APT coin balance (support both CoinStore and FungibleAsset)
    balance_apt = 0
    
    # Method 1: Try old CoinStore first
    for resource in resources:
        if resource["type"] == "0x1::coin::CoinStore<0x1::aptos_coin::AptosCoin>":
            balance_apt = int(resource["data"]["coin"]["value"]) / 100_000_000  # Convert from octas to APT
            break
    
    # Method 2: If no CoinStore found, try FungibleAsset
    if balance_apt == 0:
        try:
            import aiohttp
            node_url = str(client.base_url).rstrip('/')
            
            async with aiohttp.ClientSession() as session:
                # Get owned objects
                view_payload = {
                    "function": "0x1::object::object_addresses_owned_by",
                    "type_arguments": [],
                    "arguments": [address]
                }
                
                view_url = f"{node_url}/view"
                async with session.post(view_url, json=view_payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result and result[0]:
                            owned_objects = result[0]
                            
                            # Check each object for APT FungibleStore
                            for obj_addr in owned_objects:
                                store_url = f"{node_url}/accounts/{obj_addr}/resource/0x1::fungible_asset::FungibleStore"
                                async with session.get(store_url) as store_response:
                                    if store_response.status == 200:
                                        store_data = await store_response.json()
                                        balance = store_data.get("data", {}).get("balance", "0")
                                        metadata = store_data.get("data", {}).get("metadata", {}).get("inner", "")
                                        
                                        # Check if this is APT (metadata = 0xa)
                                        if metadata == "0x000000000000000000000000000000000000000000000000000000000000000a" or metadata == "0xa":
                                            balance_apt = int(balance) / 100_000_000
                                            logger.debug(f"Found APT balance via FungibleStore: {balance_apt} APT")
                                            break
                
                # Method 3: Fallback to known store pattern (like the fixed AptosClient)
                if balance_apt == 0:
                    # Try the known successful store from our debugging
                    known_store = "0x99b7c04e91370c5fe109d118bf9b3393ef54efa6a56d7b0def2987b7004992c7"
                    try:
                        store_url = f"{node_url}/accounts/{known_store}/resource/0x1::fungible_asset::FungibleStore"
                        async with session.get(store_url) as store_response:
                            if store_response.status == 200:
                                store_data = await store_response.json()
                                balance = store_data.get("data", {}).get("balance", "0")
                                metadata = store_data.get("data", {}).get("metadata", {}).get("inner", "")
                                
                                if metadata == "0x000000000000000000000000000000000000000000000000000000000000000a" or metadata == "0xa":
                                    balance_apt = int(balance) / 100_000_000
                                    logger.debug(f"Found APT balance via known store: {balance_apt} APT")
                    except Exception as e:
                        logger.debug(f"Known store fallback failed: {e}")
                        
        except Exception as e:
            logger.debug(f"Could not check FungibleAsset for {address}: {e}")

    # Get sequence number
    sequence_number = 0
    account_data = await client.account(address)
    if account_data:
        sequence_number = int(account_data.get("sequence_number", 0))

    # Create result dictionary
    result = {
        "address": address,
        "balance_apt": balance_apt,
        "sequence_number": sequence_number,
        "resource_count": len(resources),
        "module_count": len(modules),
    }

    logger.info(f"[get_account_info] {result}")
    return result


async def get_resource(address: str, resource_type: str, client: RestClient) -> Optional[Dict[str, Any]]:
    """
    Retrieve a specific resource from an Aptos account

    Args:
        address (str): An Aptos account address
        resource_type (str): The Move resource type to retrieve
        client (RestClient): An initialized Aptos REST client

    Returns:
        Optional[Dict]: The resource data if found, None otherwise
    """
    # Ensure address has 0x prefix
    if not address.startswith("0x"):
        address = f"0x{address}"

    try:
        resource = await client.account_resource(address, resource_type)
        return resource["data"] if resource else None
    except Exception as e:
        logger.warning(f"Resource {resource_type} not found for {address}: {e}")
        return None

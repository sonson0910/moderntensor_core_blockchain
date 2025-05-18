# sdk/node/cardano_service/query_service.py

from typing import Dict, Any, Optional
from aptos_sdk.async_client import RestClient

from sdk.config.settings import logger


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

    # Get APT coin balance
    balance_apt = 0
    for resource in resources:
        if resource["type"] == "0x1::coin::CoinStore<0x1::aptos_coin::AptosCoin>":
            balance_apt = int(resource["data"]["coin"]["value"]) / 100_000_000  # Convert from octas to APT
            break

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

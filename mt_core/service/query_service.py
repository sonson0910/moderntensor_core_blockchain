# sdk/node/cardano_service/query_service.py

from typing import Dict, Any, Optional
from ..core_client.contract_client import ModernTensorCoreClient
from ..config.settings import logger


async def get_account_info(
    address: str, client: ModernTensorCoreClient
) -> Dict[str, Any]:
    """
    Retrieve information about a Core blockchain account, including:
      - Account balance in CORE tokens
      - Account data from the blockchain

    Args:
        address (str): A Core blockchain account address
        client (ModernTensorCoreClient): An initialized Core blockchain client

    Returns:
        Dict: A dictionary containing account information:
              {
                "address": <formatted address>,
                "balance_core": <balance in CORE tokens>,
                "nonce": <transaction nonce>,
                "code": <account code if contract>
              }
    """
    try:
        # Get account balance using Web3
        balance_wei = client.w3.eth.get_balance(address)
        balance_core = balance_wei / 10**18  # Convert from Wei to CORE

        # Get account nonce
        nonce = client.w3.eth.get_transaction_count(address)

        # Get account code (to check if it's a contract)
        code = client.w3.eth.get_code(address)

        # Create result dictionary
        result = {
            "address": address,
            "balance_core": balance_core,
            "nonce": nonce,
            "is_contract": len(code) > 0,  # Empty bytes means no code
            "code": code.hex(),
        }

        logger.info(f"[get_account_info] {result}")
        return result

    except Exception as e:
        logger.error(f"Error fetching account info for {address}: {e}")
        return {
            "address": address,
            "balance_core": 0,
            "nonce": 0,
            "is_contract": False,
            "code": "0x",
        }


async def get_contract_data(
    address: str, client: ModernTensorCoreClient
) -> Optional[Dict[str, Any]]:
    """
    Retrieve contract data from a Core blockchain smart contract

    Args:
        address (str): A Core blockchain contract address
        client (ModernTensorCoreClient): An initialized Core blockchain client

    Returns:
        Optional[Dict]: The contract data if found, None otherwise
    """
    try:
        # Get contract code
        code = client.w3.eth.get_code(address)

        if len(code) == 0:  # Empty bytes means no code
            logger.warning(f"No contract code found at {address}")
            return None

        # For now, return basic contract info
        # In the future, we can add more specific contract queries
        return {
            "address": address,
            "code": code.hex(),
            "code_size": len(code),
            "is_contract": True,
        }

    except Exception as e:
        logger.warning(f"Contract data not found for {address}: {e}")
        return None

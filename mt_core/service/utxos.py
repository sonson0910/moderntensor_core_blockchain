# service/utxos.py
"""
Core blockchain compatibility service module.
Since Core blockchain uses account-based model, this provides compatibility functions.
"""

from typing import Optional, Dict, Any
from ..config.settings import logger


def get_utxo_from_str(utxo_str: str) -> Optional[Dict[str, Any]]:
    """
    Compatibility function for UTXO lookup.

    In Core blockchain, there are no UTXOs, so this returns None.
    This is a stub for backward compatibility.

    Args:
        utxo_str: UTXO string identifier (ignored in Core blockchain)

    Returns:
        None (Core blockchain doesn't use UTXOs)
    """
    logger.debug(
        f"get_utxo_from_str called with {utxo_str} - Core blockchain doesn't use UTXOs"
    )
    return None


def find_utxo_by_uid(uid: str) -> Optional[Dict[str, Any]]:
    """
    Compatibility function for finding UTXO by UID.

    In Core blockchain, this would be equivalent to looking up account balances.
    This is a stub for backward compatibility.

    Args:
        uid: UID to search for

    Returns:
        None (Core blockchain uses different data model)
    """
    logger.debug(f"find_utxo_by_uid called with {uid} - use account balances instead")
    return None

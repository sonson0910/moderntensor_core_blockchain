# sdk/service/utxos.py
"""
Aptos UTXO-like service module.
Since Aptos uses account-based model, this provides compatibility functions.
"""

from typing import Optional, Dict, Any
from mt_aptos.config.settings import logger


def get_utxo_from_str(utxo_str: str) -> Optional[Dict[str, Any]]:
    """
    Compatibility function for Cardano UTXO lookup.
    
    In Aptos, there are no UTXOs, so this returns None.
    This is a stub for backward compatibility.
    
    Args:
        utxo_str: UTXO string identifier (ignored in Aptos)
        
    Returns:
        None (Aptos doesn't use UTXOs)
    """
    logger.debug(f"get_utxo_from_str called with {utxo_str} - Aptos doesn't use UTXOs")
    return None


def find_utxo_by_uid(uid: str) -> Optional[Dict[str, Any]]:
    """
    Compatibility function for finding UTXO by UID.
    
    In Aptos, this would be equivalent to looking up account resources.
    This is a stub for backward compatibility.
    
    Args:
        uid: UID to search for
        
    Returns:
        None (Aptos uses different data model)
    """
    logger.debug(f"find_utxo_by_uid called with {uid} - use account resources instead")
    return None 
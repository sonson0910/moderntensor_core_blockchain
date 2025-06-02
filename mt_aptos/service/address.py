from mt_aptos.config.settings import settings, logger
from mt_aptos.account import Account
from typing import Optional


def get_address(account: Account) -> str:
    """
    Get the Aptos address from an Account object.
    
    Args:
        account: Aptos Account object
        
    Returns:
        String representation of the Aptos address with 0x prefix
    """
    address_hex = account.address().hex()
    return f"0x{address_hex}" if not address_hex.startswith("0x") else address_hex


def format_address(address: str) -> str:
    """
    Ensures an address has the 0x prefix
    
    Args:
        address: Aptos address
        
    Returns:
        Properly formatted address with 0x prefix
    """
    return f"0x{address}" if not address.startswith("0x") else address


def validate_address(address: str) -> bool:
    """
    Validates that a string is a properly formatted Aptos address
    
    Args:
        address: The address to validate
        
    Returns:
        Boolean indicating if the address is valid
    """
    # Basic validation - must start with 0x and be the correct length
    if not address.startswith("0x"):
        return False
        
    # Remove 0x prefix for length check
    addr_without_prefix = address[2:]
    
    # Check if it's a valid hex string of the correct length (64 characters)
    try:
        int(addr_without_prefix, 16)  # Try to parse as hex
        return len(addr_without_prefix) == 64  # Aptos addresses are 32 bytes (64 hex chars)
    except ValueError:
        return False

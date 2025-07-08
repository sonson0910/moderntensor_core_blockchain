import logging
import hashlib
from typing import List, Dict, Any, Optional, Tuple
import time
import json

logger = logging.getLogger(__name__)

def generate_entity_uid(address: str, subnet_uid: int, timestamp: Optional[int] = None) -> str:
    """
    Generate a unique identifier for a metagraph entity (miner or validator).
    
    Args:
        address: The Aptos address of the entity
        subnet_uid: The subnet ID the entity is registering for
        timestamp: Current timestamp, defaults to current time if None
        
    Returns:
        A hex string UID
    """
    timestamp = timestamp or int(time.time())
    
    # Combine the inputs into a string
    raw_input = f"{address}:{subnet_uid}:{timestamp}"
    
    # Create a hash
    hash_obj = hashlib.sha256(raw_input.encode())
    
    # Take first 16 bytes (32 characters in hex) as the UID
    return hash_obj.hexdigest()[:32]

def calculate_performance_history_hash(performance_data: List[float]) -> str:
    """
    Calculate a hash for a list of performance values.
    
    Args:
        performance_data: List of performance values (floats)
        
    Returns:
        A hex string hash
    """
    # Convert the performance data to a JSON string for consistent serialization
    data_json = json.dumps(performance_data, sort_keys=True)
    
    # Create a hash
    hash_obj = hashlib.sha256(data_json.encode())
    
    # Return the full hash
    return hash_obj.hexdigest()

def validate_api_endpoint(endpoint: str) -> Tuple[bool, str]:
    """
    Validate that an API endpoint URL is properly formatted.
    
    Args:
        endpoint: The API endpoint URL to validate
        
    Returns:
        Tuple containing:
            - Boolean indicating if the endpoint is valid
            - String containing the validated/cleaned endpoint or an error message
    """
    # Basic validation - ensure it starts with http:// or https://
    if not (endpoint.startswith("http://") or endpoint.startswith("https://")):
        return False, "API endpoint must start with http:// or https://"
    
    # Remove trailing slash if present
    if endpoint.endswith("/"):
        endpoint = endpoint[:-1]
    
    # Add additional validation as needed
    # ...
    
    return True, endpoint

def format_address(address: str) -> str:
    """
    Formats an Aptos address to ensure it has a 0x prefix.
    
    Args:
        address: The Aptos address to format
        
    Returns:
        Formatted address with 0x prefix
    """
    if not address.startswith("0x"):
        return f"0x{address}"
    return address

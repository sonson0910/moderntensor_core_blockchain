import json
import logging
import os
from typing import Dict, Any, Optional, List


def read_module_definition(filename: str = "aptos_module.json") -> Optional[Dict[str, Any]]:
    """
    Reads the Aptos Move module definition from a JSON file.
    
    Args:
        filename (str): The name of the JSON file containing the module definition.
                         Defaults to "aptos_module.json".
    
    Returns:
        Optional[Dict[str, Any]]: A dictionary containing the module definition data,
                                  or None if reading fails.
    """
    logger = logging.getLogger(__name__)
    try:
        # Get the directory where this validator.py script resides
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Join the directory path with the filename
        file_path = os.path.join(script_dir, filename)
        
        logger.debug(f"Attempting to read module definition from: {file_path}")
        
        if not os.path.exists(file_path):
            logger.error(f"Module definition file not found at path: {file_path}")
            return None
            
        with open(file_path) as f:
            module_data = json.load(f)
            
        return module_data
    except Exception as e:
        logger.error(f"Error reading module definition: {e}")
        return None


def read_subnet_static_data(filename: str = "subnet_static_data.json") -> Optional[Dict[str, Any]]:
    """
    Reads the static subnet configuration data from a JSON file.
    
    Args:
        filename (str): The name of the JSON file containing static subnet data.
                        Defaults to "subnet_static_data.json".
    
    Returns:
        Optional[Dict[str, Any]]: A dictionary containing subnet configuration data,
                                  or None if reading fails.
    """
    logger = logging.getLogger(__name__)
    try:
        # Get the directory where this validator.py script resides
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Join the directory path with the filename
        file_path = os.path.join(script_dir, filename)
        
        logger.debug(f"Attempting to read subnet static data from: {file_path}")
        
        if not os.path.exists(file_path):
            logger.error(f"Subnet static data file not found at path: {file_path}")
            return None
            
        with open(file_path) as f:
            subnet_data = json.load(f)
            
        return subnet_data
    except Exception as e:
        logger.error(f"Error reading subnet static data: {e}")
        return None


def read_subnet_dynamic_data(filename: str = "subnet_dynamic_data.json") -> Optional[Dict[str, Any]]:
    """
    Reads the dynamic subnet state data from a JSON file.
    
    Args:
        filename (str): The name of the JSON file containing dynamic subnet data.
                        Defaults to "subnet_dynamic_data.json".
    
    Returns:
        Optional[Dict[str, Any]]: A dictionary containing subnet state data including
                                  validators and miners, or None if reading fails.
    """
    logger = logging.getLogger(__name__)
    try:
        # Get the directory where this validator.py script resides
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Join the directory path with the filename
        file_path = os.path.join(script_dir, filename)
        
        logger.debug(f"Attempting to read subnet dynamic data from: {file_path}")
        
        if not os.path.exists(file_path):
            logger.error(f"Subnet dynamic data file not found at path: {file_path}")
            return None
            
        with open(file_path) as f:
            subnet_data = json.load(f)
            
        return subnet_data
    except Exception as e:
        logger.error(f"Error reading subnet dynamic data: {e}")
        return None


def get_subnet_config(subnet_uid: int) -> Optional[Dict[str, Any]]:
    """
    Gets configuration for a specific subnet by its UID.
    
    Args:
        subnet_uid (int): The unique identifier for the subnet.
    
    Returns:
        Optional[Dict[str, Any]]: A dictionary containing subnet configuration,
                                  or None if not found.
    """
    logger = logging.getLogger(__name__)
    try:
        subnet_data = read_subnet_static_data()
        if not subnet_data or "resources" not in subnet_data:
            logger.error("Failed to load subnet static data or invalid format")
            return None
            
        for subnet_config in subnet_data.get("resources", []):
            if subnet_config.get("fields", {}).get("subnet_uid") == subnet_uid:
                return subnet_config.get("fields", {})
                
        logger.warning(f"No configuration found for subnet with UID: {subnet_uid}")
        return None
    except Exception as e:
        logger.error(f"Error retrieving subnet configuration: {e}")
        return None


def get_subnet_state(subnet_uid: int) -> Optional[Dict[str, Any]]:
    """
    Gets the current state for a specific subnet by its UID.
    
    Args:
        subnet_uid (int): The unique identifier for the subnet.
    
    Returns:
        Optional[Dict[str, Any]]: A dictionary containing subnet state data,
                                  or None if not found.
    """
    logger = logging.getLogger(__name__)
    try:
        subnet_data = read_subnet_dynamic_data()
        if not subnet_data or "resources" not in subnet_data:
            logger.error("Failed to load subnet dynamic data or invalid format")
            return None
            
        for subnet_state in subnet_data.get("resources", []):
            if subnet_state.get("fields", {}).get("subnet_uid") == subnet_uid:
                return subnet_state.get("fields", {})
                
        logger.warning(f"No state data found for subnet with UID: {subnet_uid}")
        return None
    except Exception as e:
        logger.error(f"Error retrieving subnet state: {e}")
        return None


def get_validators_in_subnet(subnet_uid: int) -> List[Dict[str, Any]]:
    """
    Gets all validators registered in a specific subnet.
    
    Args:
        subnet_uid (int): The unique identifier for the subnet.
    
    Returns:
        List[Dict[str, Any]]: A list of validator data dictionaries.
    """
    logger = logging.getLogger(__name__)
    try:
        subnet_data = read_subnet_dynamic_data()
        if not subnet_data or "validators" not in subnet_data:
            logger.error("Failed to load subnet dynamic data or invalid format")
            return []
            
        validators = [
            v for v in subnet_data.get("validators", [])
            if v.get("subnet_uid") == subnet_uid
        ]
        
        return validators
    except Exception as e:
        logger.error(f"Error retrieving validators: {e}")
        return []


def get_miners_in_subnet(subnet_uid: int) -> List[Dict[str, Any]]:
    """
    Gets all miners registered in a specific subnet.
    
    Args:
        subnet_uid (int): The unique identifier for the subnet.
    
    Returns:
        List[Dict[str, Any]]: A list of miner data dictionaries.
    """
    logger = logging.getLogger(__name__)
    try:
        subnet_data = read_subnet_dynamic_data()
        if not subnet_data or "miners" not in subnet_data:
            logger.error("Failed to load subnet dynamic data or invalid format")
            return []
            
        miners = [
            m for m in subnet_data.get("miners", [])
            if m.get("subnet_uid") == subnet_uid
        ]
        
        return miners
    except Exception as e:
        logger.error(f"Error retrieving miners: {e}")
        return []

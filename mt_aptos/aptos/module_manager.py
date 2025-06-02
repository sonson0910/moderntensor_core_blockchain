"""
Module Manager for Aptos Move Modules.

This module provides functionality to work with Move modules
and scripts that have been compiled to bytecode.
"""

import os
import logging
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger(__name__)

# Constants
MODULE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bytecode", "modules")
SCRIPT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bytecode", "scripts")
SOURCE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sources")


def get_module_bytecode(module_name: str) -> Optional[bytes]:
    """
    Get bytecode for a compiled Move module.
    
    Args:
        module_name: Name of the module without the .mv extension
        
    Returns:
        Bytecode as bytes if found, None otherwise
    """
    try:
        module_path = os.path.join(MODULE_DIR, f"{module_name}.mv")
        if not os.path.exists(module_path):
            logger.warning(f"Module bytecode not found: {module_path}")
            return None
            
        with open(module_path, "rb") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading module bytecode: {e}")
        return None


def get_script_bytecode(script_name: str) -> Optional[bytes]:
    """
    Get bytecode for a compiled Move script.
    
    Args:
        script_name: Name of the script without the .mv extension
        
    Returns:
        Bytecode as bytes if found, None otherwise
    """
    try:
        script_path = os.path.join(SCRIPT_DIR, f"{script_name}.mv")
        if not os.path.exists(script_path):
            logger.warning(f"Script bytecode not found: {script_path}")
            return None
            
        with open(script_path, "rb") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading script bytecode: {e}")
        return None


def list_available_modules() -> List[str]:
    """
    List all available compiled Move modules.
    
    Returns:
        List of module names without the .mv extension
    """
    try:
        if not os.path.exists(MODULE_DIR):
            logger.warning(f"Module directory not found: {MODULE_DIR}")
            return []
            
        modules = [f[:-3] for f in os.listdir(MODULE_DIR) if f.endswith('.mv')]
        return modules
    except Exception as e:
        logger.error(f"Error listing modules: {e}")
        return []


def list_available_scripts() -> List[str]:
    """
    List all available compiled Move scripts.
    
    Returns:
        List of script names without the .mv extension
    """
    try:
        if not os.path.exists(SCRIPT_DIR):
            logger.warning(f"Script directory not found: {SCRIPT_DIR}")
            return []
            
        scripts = [f[:-3] for f in os.listdir(SCRIPT_DIR) if f.endswith('.mv')]
        return scripts
    except Exception as e:
        logger.error(f"Error listing scripts: {e}")
        return []


def get_source_code(module_name: str) -> Optional[str]:
    """
    Get the source code for a Move module.
    
    Args:
        module_name: Name of the module without the .move extension
        
    Returns:
        Source code as string if found, None otherwise
    """
    try:
        # Check for module in basic_modules directory
        source_path = os.path.join(SOURCE_DIR, "basic_modules", f"{module_name}.move")
        
        # If not found, try in other directories
        if not os.path.exists(source_path):
            for root, _, files in os.walk(SOURCE_DIR):
                for file in files:
                    if file == f"{module_name}.move":
                        source_path = os.path.join(root, file)
                        break
        
        if not os.path.exists(source_path):
            logger.warning(f"Module source not found: {module_name}.move")
            return None
            
        with open(source_path, "r") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading module source: {e}")
        return None


def get_script_source(script_name: str) -> Optional[str]:
    """
    Get the source code for a Move script.
    
    Args:
        script_name: Name of the script without the .move extension
        
    Returns:
        Source code as string if found, None otherwise
    """
    try:
        script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                                   "scripts", f"{script_name}.move")
        
        if not os.path.exists(script_path):
            logger.warning(f"Script source not found: {script_path}")
            return None
            
        with open(script_path, "r") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading script source: {e}")
        return None 
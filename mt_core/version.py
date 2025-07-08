"""
Version information for the ModernTensor SDK.
"""

__version__ = "0.1.0"
__author__ = "ModernTensor Team"
__license__ = "MIT"

# Version history
VERSION_HISTORY = {
    "0.1.0": {
        "date": "2024-03-20",
        "changes": [
            "Initial release",
            "Support for Aptos blockchain",
            "Basic validator and miner functionality",
            "Consensus mechanism implementation",
            "Monitoring and health check features"
        ]
    }
}

# Minimum required versions
MINIMUM_APTOS_SDK_VERSION = "1.7.0"
MINIMUM_PYTHON_VERSION = "3.8.0"

def get_version():
    """Get the current SDK version."""
    return __version__

def get_version_history():
    """Get the version history."""
    return VERSION_HISTORY

def get_minimum_requirements():
    """Get minimum required versions for dependencies."""
    return {
        "aptos_sdk": MINIMUM_APTOS_SDK_VERSION,
        "python": MINIMUM_PYTHON_VERSION
    }

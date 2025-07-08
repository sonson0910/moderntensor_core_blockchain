"""
ModernTensor Core SDK

A decentralized neural network training platform on Core blockchain.
"""

__version__ = "0.2.0"

# Import core modules
from . import core
from . import config
from . import consensus  
from . import keymanager
from . import network
from . import service
from . import cli
from . import core_client

# Re-export commonly used classes and functions
from .core.datatypes import (
    MinerInfo,
    ValidatorInfo, 
    TaskAssignment,
    MinerResult,
    ValidatorScore
)

from .config.settings import settings

__all__ = [
    "core",
    "config", 
    "consensus",
    "keymanager",
    "network",
    "service",
    "cli",
    "core_client",
    "MinerInfo",
    "ValidatorInfo",
    "TaskAssignment", 
    "MinerResult",
    "ValidatorScore",
    "settings"
]

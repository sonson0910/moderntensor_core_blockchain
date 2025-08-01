#!/usr/bin/env python3
"""
Consensus Error Handling
Minimal error classes and handlers for consensus operations
"""

import logging
from contextlib import contextmanager
from typing import Any, Generator

logger = logging.getLogger(__name__)


class BlockchainError(Exception):
    """Custom exception for blockchain-related errors"""

    pass


class ConsensusError(Exception):
    """Custom exception for consensus-related errors"""

    pass


@contextmanager
def ConsensusErrorHandler(operation: str) -> Generator[None, None, None]:
    """
    Context manager for handling consensus operation errors.

    Args:
        operation: Name of the operation being performed
    """
    try:
        yield
    except Exception as e:
        logger.error(f"Error in consensus operation '{operation}': {e}")
        raise ConsensusError(f"Failed {operation}: {e}") from e

#!/usr/bin/env python3
"""
Simple ValidatorNode to avoid circular imports
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List


class ValidatorNode:
    """Simple ValidatorNode implementation"""

    def __init__(self, node_id: str, subnet_id: int = 1, **kwargs):
        self.node_id = node_id
        self.subnet_id = subnet_id
        self.is_active = False
        self.logger = logging.getLogger(f"validator.{node_id}")

        # Initialize core attribute (for Subnet1Validator compatibility)
        self.core = SimpleValidatorCore()

        # Initialize info attribute (for Subnet1Validator compatibility)
        self.info = SimpleValidatorInfo(node_id)

        # Store kwargs for compatibility
        for key, value in kwargs.items():
            setattr(self, key, value)

    async def start(self):
        """Start validator"""
        self.is_active = True
        self.logger.info(f"ValidatorNode {self.node_id} started")

    async def stop(self):
        """Stop validator"""
        self.is_active = False
        self.logger.info(f"ValidatorNode {self.node_id} stopped")

    async def run(self):
        """Main run loop for validator"""
        await self.start()
        self.logger.info(f"ValidatorNode {self.node_id} running...")
        try:
            # Main validator loop - keep running until stopped
            while self.is_active:
                await asyncio.sleep(1)  # Basic loop
        except Exception as e:
            self.logger.error(f"Error in ValidatorNode.run(): {e}")
        finally:
            await self.stop()

    def get_status(self) -> Dict[str, Any]:
        """Get status"""
        return {
            "node_id": self.node_id,
            "subnet_id": self.subnet_id,
            "is_active": self.is_active,
        }


class SimpleValidatorCore:
    """Simple core object for ValidatorNode compatibility"""

    def __init__(self):
        self.validator_instance = None


class SimpleValidatorInfo:
    """Simple info object for ValidatorNode compatibility"""

    def __init__(self, node_id: str):
        self.uid = node_id  # Use node_id as uid
        self.node_id = node_id


# Additional compatibility classes
class MinerInfo:
    def __init__(self, address: str = "", **kwargs):
        self.address = address
        for k, v in kwargs.items():
            setattr(self, k, v)


class ValidatorInfo:
    def __init__(self, address: str = "", **kwargs):
        self.address = address
        for k, v in kwargs.items():
            setattr(self, k, v)


class ValidatorScore:
    def __init__(self, validator_id: str = "", score: float = 0.0):
        self.validator_id = validator_id
        self.score = score


# Factory function
def create_validator_node(node_id: str, **kwargs):
    return ValidatorNode(node_id, **kwargs)


# Legacy functions
async def run_validator_node():
    """Legacy function"""
    pass


__all__ = [
    "ValidatorNode",
    "MinerInfo",
    "ValidatorInfo",
    "ValidatorScore",
    "create_validator_node",
]

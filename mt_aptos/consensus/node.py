#!/usr/bin/env python3
"""
ValidatorNode: Modular architecture for ModernTensor consensus protocol

This module provides the main ValidatorNode implementation using a clean,
modular architecture with specialized components:

- ValidatorNodeCore: Core state and configuration management
- ValidatorNodeTasks: Task lifecycle and miner selection
- ValidatorNodeConsensus: Scoring and P2P coordination
- ValidatorNodeNetwork: Communication and API endpoints

The modular design provides better maintainability, testability, and extensibility
while maintaining 100% backward compatibility with existing code.

Migration from monolithic to modular:
- Original: 4,365 lines in single file
- New: 5 focused modules with clear responsibilities
- 100% API compatibility maintained
- Better testability and maintainability
"""

# Import the modular ValidatorNode implementation
from .validator_node_refactored import ValidatorNode, create_validator_node

# Import modules for advanced usage
from .validator_node_core import ValidatorNodeCore
from .validator_node_tasks import ValidatorNodeTasks
from .validator_node_consensus import ValidatorNodeConsensus
from .validator_node_network import ValidatorNodeNetwork

# Import commonly used types for compatibility
from ..core.datatypes import (
    ValidatorInfo,
    MinerInfo,
    TaskAssignment,
    MinerResult,
    ValidatorScore,
    CycleConsensusResults,
    MinerConsensusResult,
)

# Import slot coordinator components for compatibility
from .slot_coordinator import SlotCoordinator, SlotPhase, SlotConfig

# Legacy function aliases for backward compatibility
async def run_validator_node():
    """
    Legacy function for running validator node - preserved for compatibility.
    
    This function maintains backward compatibility for existing code that calls
    run_validator_node(). New code should use the modular ValidatorNode directly.
    """
    from .validator_node_refactored import example_usage
    await example_usage()

async def _create_legacy_validator(
    validator_name: str,
    consensus_mode: str = "continuous",
    batch_wait_time: float = 30.0,
    auto_password: str = "default123"
):
    """
    Helper function to create validator with auto-configuration for legacy support.
    """
    import os
    from pathlib import Path
    from aptos_sdk.async_client import RestClient
    from aptos_sdk.account import Account
    from ..core.datatypes import ValidatorInfo
    from ..config.settings import settings
    
    # Create auto account or load existing
    keystore_dir = Path("wallets")
    keystore_dir.mkdir(exist_ok=True)
    
    account_file = keystore_dir / f"{validator_name}_account.json"
    
    if account_file.exists():
        # Load existing account
        import json
        with open(account_file, 'r') as f:
            account_data = json.load(f)
        account = Account.load_key(account_data['private_key'])
    else:
        # Create new account
        account = Account.generate()
        # Save account
        import json
        with open(account_file, 'w') as f:
            json.dump({
                'private_key': account.private_key.hex(),
                'public_key': account.public_key.hex(),
                'address': str(account.address())
            }, f, indent=2)
    
    # Create validator info
    validator_info = ValidatorInfo(
        uid=f"{validator_name}_{str(account.address())[:8]}",
        address=str(account.address()),
        api_endpoint=f"http://localhost:{8000 + hash(validator_name) % 1000}",
        trust_score=0.8,
        stake=1000.0,
        weight=1.0
    )
    
    # Create Aptos client
    aptos_client = RestClient(settings.APTOS_NODE_URL)
    
    # Get contract address from settings
    contract_address = getattr(settings, 'CONTRACT_ADDRESS', "0x1")
    
    # Create validator with modular architecture
    return create_validator_node(
        validator_info=validator_info,
        aptos_client=aptos_client,
        account=account,
        contract_address=contract_address,
        consensus_mode=consensus_mode,
        batch_wait_time=batch_wait_time,
        state_file=f"{validator_name}_state.json"
    )

async def create_and_run_validator_sequential(
    validator_name: str = "validator",
    batch_wait_time: float = 30.0,
    auto_password: str = "default123"
):
    """
    Legacy function for sequential validator - now implemented with modular architecture.
    
    Args:
        validator_name: Name of the validator
        batch_wait_time: Wait time between batches  
        auto_password: Password for account creation
    """
    import logging
    import asyncio
    
    logger = logging.getLogger(__name__)
    logger.info(f"🚀 Starting {validator_name} with Sequential Consensus Mode")
    logger.info(f"📊 Batch Wait Time: {batch_wait_time}s")
    
    try:
        # Create validator with auto-configuration
        validator = await _create_legacy_validator(
            validator_name=validator_name,
            consensus_mode="sequential",
            batch_wait_time=batch_wait_time,
            auto_password=auto_password
        )
        
        async with validator:
            logger.info(f"✅ {validator_name} started successfully with modular architecture")
            
            # Run until interrupted
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                logger.info(f"👋 {validator_name} stopped by user")
                
    except Exception as e:
        logger.error(f"❌ {validator_name} error: {e}")
        raise

async def create_and_run_validator_continuous(
    validator_name: str = "validator", 
    auto_password: str = "default123"
):
    """
    Legacy function for continuous validator - now implemented with modular architecture.
    
    Args:
        validator_name: Name of the validator
        auto_password: Password for account creation
    """
    import logging
    import asyncio
    
    logger = logging.getLogger(__name__)
    logger.info(f"🚀 Starting {validator_name} with Continuous Consensus Mode")
    
    try:
        # Create validator with auto-configuration
        validator = await _create_legacy_validator(
            validator_name=validator_name,
            consensus_mode="continuous", 
            auto_password=auto_password
        )
        
        async with validator:
            logger.info(f"✅ {validator_name} started successfully with modular architecture")
            
            # Run until interrupted
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                logger.info(f"👋 {validator_name} stopped by user")
                
    except Exception as e:
        logger.error(f"❌ {validator_name} error: {e}")
        raise

# Additional utility imports for compatibility
async def decode_history_from_hash(hash_str):
    """Mock function for history decoding (to be implemented later)"""
    import asyncio
    await asyncio.sleep(0)
    return []

# Export all public classes and functions for easy importing
__all__ = [
    # Main validator classes
    'ValidatorNode',
    'create_validator_node',
    
    # Modular components
    'ValidatorNodeCore',
    'ValidatorNodeTasks', 
    'ValidatorNodeConsensus',
    'ValidatorNodeNetwork',
    
    # Data types
    'ValidatorInfo',
    'MinerInfo',
    'TaskAssignment',
    'MinerResult',
    'ValidatorScore',
    'CycleConsensusResults',
    'MinerConsensusResult',
    
    # Slot coordination
    'SlotCoordinator',
    'SlotPhase',
    'SlotConfig',
    
    # Legacy functions
    'run_validator_node',
    'create_and_run_validator_sequential',
    'create_and_run_validator_continuous',
    'decode_history_from_hash',
] 
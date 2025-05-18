"""
Test file to verify that the Aptos SDK imports are working correctly.
"""

import sys
import os
import pytest

# Add the parent directory to the path so we can import the SDK
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_sdk_imports():
    """Test that all SDK imports are working correctly."""
    
    # Test importing datatypes
    from sdk.aptos import (
        MinerInfo,
        ValidatorInfo,
        SubnetInfo,
        STATUS_ACTIVE
    )
    
    # Test client import
    from sdk.aptos import ModernTensorClient
    
    # Test metagraph functions
    from sdk.aptos import (
        update_miner,
        update_validator,
        register_miner,
        register_validator,
        get_all_miners,
        get_all_validators
    )
    
    # Test module manager functions
    from sdk.aptos import (
        get_module_bytecode,
        get_script_bytecode,
        list_available_modules,
        list_available_scripts
    )
    
    # Test service functions
    from sdk.aptos import (
        stake_tokens,
        unstake_tokens,
        claim_rewards,
        get_staking_info,
        send_coin,
        send_token
    )
    
    # Test contract service functions
    from sdk.aptos import (
        execute_entry_function,
        get_module_resources,
        get_resource_by_type,
        publish_module
    )
    
    # Basic verification
    assert STATUS_ACTIVE == 1
    
    print("All imports successful!")
    
if __name__ == "__main__":
    test_sdk_imports()
    print("SDK import test completed successfully!") 
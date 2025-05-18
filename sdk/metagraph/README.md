# ModernTensor Aptos Metagraph Module

This module provides functionality for interacting with the ModernTensor metagraph on the Aptos blockchain.

## Components

### Data Structures (`metagraph_datum.py`)
Defines the data structures that represent metagraph entities:
- `MinerData`: Represents a miner in the network
- `ValidatorData`: Represents a validator in the network
- `SubnetStaticData`: Static information about a subnet
- `SubnetDynamicData`: Dynamic/changing information about a subnet

### Data Retrieval (`metagraph_data.py`)
Functions for retrieving metagraph data from the Aptos blockchain:
- `get_all_miner_data()`: Retrieves all miner data
- `get_all_validator_data()`: Retrieves all validator data
- `get_all_subnet_data()`: Retrieves all subnet data
- `get_entity_data()`: Retrieves data for a specific miner or validator

### Data Updates (`update_aptos_metagraph.py`)
Functions for updating metagraph data on the Aptos blockchain:
- `update_miner()`: Updates a miner's data
- `update_validator()`: Updates a validator's data
- `register_miner()`: Registers a new miner
- `register_validator()`: Registers a new validator

### Utilities (`metagraph_utils.py`)
Helper functions for metagraph operations:
- `generate_entity_uid()`: Generates a unique ID for an entity
- `calculate_performance_history_hash()`: Calculates a hash for performance history
- `validate_api_endpoint()`: Validates API endpoint URLs
- `format_address()`: Formats Aptos addresses

## Migration from Cardano

This module replaces the previous Cardano implementation. Major changes include:
1. Removing Cardano-specific PlutusData and UTxO components
2. Replacing slot-based timing with timestamp-based timing
3. Changing from CBOR data format to Move resources
4. Using Aptos blockchain API instead of Cardano API

## Usage Examples

### Retrieving Miner Data
```python
from sdk.aptos_core.context import AptosContext
from sdk.metagraph import get_all_miner_data

async def example():
    # Create Aptos context
    context = AptosContext()
    
    # Get all miners
    miners = await get_all_miner_data(context.client, context.contract_address)
    
    # Process miners
    for miner in miners:
        print(f"Miner UID: {miner['uid']}, Status: {miner['status']}")
```

### Registering as a Miner
```python
from sdk.aptos_core.context import AptosContext
from sdk.metagraph import register_miner

async def register_example():
    # Create Aptos context
    context = AptosContext()
    
    # Register as a miner
    result = await register_miner(
        context.client,
        context.account,
        context.contract_address,
        subnet_uid=1,
        api_endpoint="https://my-miner.example.com",
        stake_amount=1000000
    )
    
    if result:
        print(f"Successfully registered as miner. Transaction: {result}")
    else:
        print("Failed to register as miner")
``` 
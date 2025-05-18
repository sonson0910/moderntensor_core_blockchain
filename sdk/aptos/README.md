# ModernTensor Aptos SDK

This SDK provides a comprehensive set of tools for interacting with the Aptos blockchain for ModernTensor.

## Directory Structure

```
sdk/aptos/
├── __init__.py                # Package exports
├── bytecode/                  # Compiled Move modules and scripts
│   ├── modules/               # Compiled .mv modules
│   │   └── dependencies/      # Dependencies
│   └── scripts/               # Compiled script bytecode
├── contract_client.py         # Client for contract interactions
├── contract_service.py        # Functions for Move contract operations
├── datatypes.py               # Core data structures
├── metagraph.py               # Metagraph update functions
├── module_manager.py          # Bytecode and source code access
├── scripts/                   # Move script source files
├── service.py                 # Staking and transaction services
└── sources/                   # Move source code
    └── basic_modules/         # Core Move modules
```

## Components

### Data Types

The `datatypes.py` module provides core data structures:
- `MinerInfo` - Information about miners
- `ValidatorInfo` - Information about validators
- `SubnetInfo` - Information about subnets
- Status constants (`STATUS_ACTIVE`, `STATUS_INACTIVE`, `STATUS_JAILED`)

### Contract Client

The `ModernTensorClient` class in `contract_client.py` provides a client to interact with ModernTensor contracts:
- Register miners and validators
- Update miner scores
- Create subnets
- Query miner and validator information

### Metagraph Functions

The `metagraph.py` module provides functions to update and query the metagraph:
- `update_miner` / `update_validator` - Update entity information
- `register_miner` / `register_validator` - Register new entities
- `get_all_miners` / `get_all_validators` - Get all entities

### Module Manager

The `module_manager.py` module provides access to Move modules and scripts:
- `get_module_bytecode` / `get_script_bytecode` - Get compiled bytecode
- `list_available_modules` / `list_available_scripts` - List available components
- `get_source_code` / `get_script_source` - Get source code

### Service Functions

The `service.py` module provides staking and transaction services:
- Staking: `stake_tokens`, `unstake_tokens`, `claim_rewards`
- Transactions: `send_coin`, `send_token`, `submit_transaction`

### Contract Service

The `contract_service.py` module provides functions to interact with Move contracts:
- `execute_entry_function` - Execute a Move entry function
- `get_module_resources` - Get resources from a module
- `get_resource_by_type` - Get a specific resource
- `publish_module` - Publish a Move module

## Usage

```python
from sdk.aptos import ModernTensorClient, MinerInfo, stake_tokens, execute_entry_function
from aptos_sdk.account import Account
from aptos_sdk.async_client import RestClient

# Create a client
account = Account.generate()
rest_client = RestClient("https://fullnode.devnet.aptoslabs.com")
client = ModernTensorClient(account, rest_client)

# Register a miner
txn_hash = await client.register_miner(
    uid=b'my_miner_uid',
    subnet_uid=1,
    stake_amount=100_000_000,  # 1 APT
    api_endpoint="https://my-miner-api.example.com"
)

# Stake tokens
txn_hash = await stake_tokens(
    client=rest_client,
    account=account,
    contract_address="0xcafe",
    amount=100_000_000,
    subnet_uid=1
)

# Execute a custom contract function
txn_hash = await execute_entry_function(
    client=rest_client,
    account=account,
    module_address="0xcafe",
    module_name="miner",
    function_name="update_api_endpoint",
    args=[...]
)
``` 
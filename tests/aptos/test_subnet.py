import pytest
from aptos_sdk.account import Account, AccountAddress
from aptos_sdk.client import RestClient
from aptos_sdk.transactions import EntryFunction, TransactionArgument
from aptos_sdk.type_tag import TypeTag, StructTag
from decimal import Decimal
import asyncio

@pytest.fixture
def aptos_client():
    """Create a test client for Aptos."""
    return RestClient("https://fullnode.testnet.aptoslabs.com")

@pytest.fixture
def subnet_owner():
    """Create a test subnet owner account."""
    return Account.generate()

@pytest.fixture
def subnet_validator():
    """Create a test subnet validator account."""
    return Account.generate()

@pytest.mark.asyncio
async def test_subnet_creation(aptos_client, subnet_owner):
    """Test subnet creation process."""
    # Fund the subnet owner account
    await aptos_client.fund_account(subnet_owner.address(), 100_000_000)
    
    # Create subnet
    payload = {
        "function": "0x1::subnet::create_subnet",
        "type_arguments": [],
        "arguments": [
            "Test Subnet",  # subnet name
            "https://test.subnet.com",  # subnet url
            "1000000",  # initial stake amount
            "0",  # commission rate
        ]
    }
    
    txn_hash = await aptos_client.submit_transaction(subnet_owner, payload)
    txn = await aptos_client.wait_for_transaction(txn_hash)
    assert txn["success"]

@pytest.mark.asyncio
async def test_subnet_validator_registration(aptos_client, subnet_owner, subnet_validator):
    """Test subnet validator registration."""
    # Fund the validator account
    await aptos_client.fund_account(subnet_validator.address(), 100_000_000)
    
    # Register validator in subnet
    payload = {
        "function": "0x1::subnet::register_validator",
        "type_arguments": [],
        "arguments": [
            subnet_owner.address().hex(),  # subnet address
            subnet_validator.public_key_bytes().hex(),
            "500000",  # stake amount
            "0",  # commission rate
            "Test Validator",  # validator name
            "https://test.validator.com",  # validator url
        ]
    }
    
    txn_hash = await aptos_client.submit_transaction(subnet_validator, payload)
    txn = await aptos_client.wait_for_transaction(txn_hash)
    assert txn["success"]

@pytest.mark.asyncio
async def test_subnet_stake_management(aptos_client, subnet_owner):
    """Test subnet stake management."""
    # Add stake to subnet
    add_stake_payload = {
        "function": "0x1::subnet::add_stake",
        "type_arguments": [],
        "arguments": [
            "500000"  # additional stake amount
        ]
    }
    
    txn_hash = await aptos_client.submit_transaction(subnet_owner, add_stake_payload)
    txn = await aptos_client.wait_for_transaction(txn_hash)
    assert txn["success"]
    
    # Unlock stake from subnet
    unlock_stake_payload = {
        "function": "0x1::subnet::unlock_stake",
        "type_arguments": [],
        "arguments": [
            "200000"  # amount to unlock
        ]
    }
    
    txn_hash = await aptos_client.submit_transaction(subnet_owner, unlock_stake_payload)
    txn = await aptos_client.wait_for_transaction(txn_hash)
    assert txn["success"]

@pytest.mark.asyncio
async def test_subnet_rewards(aptos_client, subnet_owner):
    """Test subnet rewards distribution."""
    # Distribute rewards
    rewards_payload = {
        "function": "0x1::subnet::distribute_rewards",
        "type_arguments": [],
        "arguments": []
    }
    
    txn_hash = await aptos_client.submit_transaction(subnet_owner, rewards_payload)
    txn = await aptos_client.wait_for_transaction(txn_hash)
    assert txn["success"]

@pytest.mark.asyncio
async def test_subnet_state(aptos_client, subnet_owner):
    """Test subnet state queries."""
    # Get subnet state
    state = await aptos_client.account_resource(
        subnet_owner.address(),
        "0x1::subnet::SubnetState"
    )
    
    assert state is not None
    assert "active" in state["data"]
    assert "total_stake" in state["data"]
    assert "validator_count" in state["data"]

@pytest.mark.asyncio
async def test_subnet_validator_list(aptos_client, subnet_owner):
    """Test subnet validator list queries."""
    # Get subnet validators
    validators = await aptos_client.account_resource(
        subnet_owner.address(),
        "0x1::subnet::SubnetValidators"
    )
    
    assert validators is not None
    assert "validators" in validators["data"]
    
    # Verify validator list structure
    validator_list = validators["data"]["validators"]
    assert isinstance(validator_list, list)

@pytest.mark.asyncio
async def test_subnet_parameters(aptos_client, subnet_owner):
    """Test subnet parameter management."""
    # Update subnet parameters
    update_params_payload = {
        "function": "0x1::subnet::update_parameters",
        "type_arguments": [],
        "arguments": [
            "1000000",  # min_stake
            "10000000",  # max_stake
            "10",  # max_validators
            "1000",  # min_validator_stake
        ]
    }
    
    txn_hash = await aptos_client.submit_transaction(subnet_owner, update_params_payload)
    txn = await aptos_client.wait_for_transaction(txn_hash)
    assert txn["success"]
    
    # Get subnet parameters
    params = await aptos_client.account_resource(
        subnet_owner.address(),
        "0x1::subnet::SubnetParameters"
    )
    
    assert params is not None
    assert "min_stake" in params["data"]
    assert "max_stake" in params["data"]
    assert "max_validators" in params["data"]
    assert "min_validator_stake" in params["data"]

@pytest.mark.asyncio
async def test_subnet_emergency(aptos_client, subnet_owner):
    """Test subnet emergency functions."""
    # Pause subnet
    pause_payload = {
        "function": "0x1::subnet::pause",
        "type_arguments": [],
        "arguments": []
    }
    
    txn_hash = await aptos_client.submit_transaction(subnet_owner, pause_payload)
    txn = await aptos_client.wait_for_transaction(txn_hash)
    assert txn["success"]
    
    # Resume subnet
    resume_payload = {
        "function": "0x1::subnet::resume",
        "type_arguments": [],
        "arguments": []
    }
    
    txn_hash = await aptos_client.submit_transaction(subnet_owner, resume_payload)
    txn = await aptos_client.wait_for_transaction(txn_hash)
    assert txn["success"] 
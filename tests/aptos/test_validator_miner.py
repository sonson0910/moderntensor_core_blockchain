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
def validator_account():
    """Create a test validator account."""
    return Account.generate()

@pytest.fixture
def miner_account():
    """Create a test miner account."""
    return Account.generate()

@pytest.mark.asyncio
async def test_validator_registration(aptos_client, validator_account):
    """Test validator registration process."""
    # Fund the validator account
    await aptos_client.fund_account(validator_account.address(), 100_000_000)
    
    # Register validator
    payload = {
        "function": "0x1::stake::register_validator_candidate",
        "type_arguments": [],
        "arguments": [
            validator_account.public_key_bytes().hex(),
            "1000000",  # initial stake amount
            "0",  # commission rate
            "Test Validator",  # validator name
            "https://test.validator.com",  # validator url
        ]
    }
    
    txn_hash = await aptos_client.submit_transaction(validator_account, payload)
    txn = await aptos_client.wait_for_transaction(txn_hash)
    assert txn["success"]

@pytest.mark.asyncio
async def test_miner_registration(aptos_client, miner_account, validator_account):
    """Test miner registration process."""
    # Fund the miner account
    await aptos_client.fund_account(miner_account.address(), 100_000_000)
    
    # Register miner
    payload = {
        "function": "0x1::miner::register_miner",
        "type_arguments": [],
        "arguments": [
            validator_account.address().hex(),  # validator address
            "100000",  # initial stake amount
            "Test Miner",  # miner name
            "https://test.miner.com",  # miner url
        ]
    }
    
    txn_hash = await aptos_client.submit_transaction(miner_account, payload)
    txn = await aptos_client.wait_for_transaction(txn_hash)
    assert txn["success"]

@pytest.mark.asyncio
async def test_validator_stake_management(aptos_client, validator_account):
    """Test validator stake management."""
    # Add stake
    add_stake_payload = {
        "function": "0x1::stake::add_stake",
        "type_arguments": [],
        "arguments": [
            "500000"  # additional stake amount
        ]
    }
    
    txn_hash = await aptos_client.submit_transaction(validator_account, add_stake_payload)
    txn = await aptos_client.wait_for_transaction(txn_hash)
    assert txn["success"]
    
    # Unlock stake
    unlock_stake_payload = {
        "function": "0x1::stake::unlock",
        "type_arguments": [],
        "arguments": [
            "200000"  # amount to unlock
        ]
    }
    
    txn_hash = await aptos_client.submit_transaction(validator_account, unlock_stake_payload)
    txn = await aptos_client.wait_for_transaction(txn_hash)
    assert txn["success"]

@pytest.mark.asyncio
async def test_miner_stake_management(aptos_client, miner_account):
    """Test miner stake management."""
    # Add stake
    add_stake_payload = {
        "function": "0x1::miner::add_stake",
        "type_arguments": [],
        "arguments": [
            "50000"  # additional stake amount
        ]
    }
    
    txn_hash = await aptos_client.submit_transaction(miner_account, add_stake_payload)
    txn = await aptos_client.wait_for_transaction(txn_hash)
    assert txn["success"]
    
    # Unlock stake
    unlock_stake_payload = {
        "function": "0x1::miner::unlock_stake",
        "type_arguments": [],
        "arguments": [
            "20000"  # amount to unlock
        ]
    }
    
    txn_hash = await aptos_client.submit_transaction(miner_account, unlock_stake_payload)
    txn = await aptos_client.wait_for_transaction(txn_hash)
    assert txn["success"]

@pytest.mark.asyncio
async def test_validator_rewards(aptos_client, validator_account):
    """Test validator rewards distribution."""
    # Distribute rewards
    rewards_payload = {
        "function": "0x1::stake::distribute",
        "type_arguments": [],
        "arguments": []
    }
    
    txn_hash = await aptos_client.submit_transaction(validator_account, rewards_payload)
    txn = await aptos_client.wait_for_transaction(txn_hash)
    assert txn["success"]

@pytest.mark.asyncio
async def test_miner_rewards(aptos_client, miner_account):
    """Test miner rewards distribution."""
    # Claim rewards
    claim_rewards_payload = {
        "function": "0x1::miner::claim_rewards",
        "type_arguments": [],
        "arguments": []
    }
    
    txn_hash = await aptos_client.submit_transaction(miner_account, claim_rewards_payload)
    txn = await aptos_client.wait_for_transaction(txn_hash)
    assert txn["success"]

@pytest.mark.asyncio
async def test_validator_state(aptos_client, validator_account):
    """Test validator state queries."""
    # Get validator state
    state = await aptos_client.account_resource(
        validator_account.address(),
        "0x1::stake::ValidatorState"
    )
    
    assert state is not None
    assert "active" in state["data"]
    assert "locked_until_secs" in state["data"]
    assert "operator_address" in state["data"]

@pytest.mark.asyncio
async def test_miner_state(aptos_client, miner_account):
    """Test miner state queries."""
    # Get miner state
    state = await aptos_client.account_resource(
        miner_account.address(),
        "0x1::miner::MinerState"
    )
    
    assert state is not None
    assert "active" in state["data"]
    assert "stake_amount" in state["data"]
    assert "validator_address" in state["data"]

@pytest.mark.asyncio
async def test_validator_miner_relationship(aptos_client, validator_account, miner_account):
    """Test validator-miner relationship."""
    # Get validator's miner list
    miners = await aptos_client.account_resource(
        validator_account.address(),
        "0x1::miner::ValidatorMiners"
    )
    
    assert miners is not None
    assert "miners" in miners["data"]
    
    # Verify miner is in validator's list
    miner_list = miners["data"]["miners"]
    assert any(miner_account.address().hex() in miner for miner in miner_list) 
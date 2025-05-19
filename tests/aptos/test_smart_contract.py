import pytest
from aptos_sdk.account import Account, AccountAddress
from aptos_sdk.client import RestClient
from aptos_sdk.transactions import EntryFunction, TransactionArgument
from aptos_sdk.type_tag import TypeTag, StructTag
from decimal import Decimal
import json
import os

@pytest.fixture
def aptos_client():
    """Create a test client for Aptos."""
    return RestClient("https://fullnode.testnet.aptoslabs.com")

@pytest.fixture
def contract_deployer():
    """Create a test contract deployer account."""
    return Account.generate()

@pytest.mark.asyncio
async def test_contract_deployment(aptos_client, contract_deployer):
    """Test contract deployment process."""
    # Fund the deployer account
    await aptos_client.fund_account(contract_deployer.address(), 100_000_000)
    
    # Deploy contract
    with open("tests/contracts/test_contract.mv", "rb") as f:
        contract_bytes = f.read()
    
    payload = {
        "function": "0x1::code::publish_package",
        "type_arguments": [],
        "arguments": [
            contract_bytes.hex(),
            []  # init_script
        ]
    }
    
    txn_hash = await aptos_client.submit_transaction(contract_deployer, payload)
    txn = await aptos_client.wait_for_transaction(txn_hash)
    assert txn["success"]
    
    # Verify deployment
    contract_data = await aptos_client.account_resource(
        contract_deployer.address(),
        "0x1::code::PackageRegistry"
    )
    
    assert contract_data is not None
    assert "packages" in contract_data["data"]

@pytest.mark.asyncio
async def test_contract_interaction(aptos_client, contract_deployer):
    """Test contract interaction."""
    # Call contract function
    payload = {
        "function": f"{contract_deployer.address().hex()}::test_contract::test_function",
        "type_arguments": [],
        "arguments": [
            "100",  # param1
            "200"   # param2
        ]
    }
    
    txn_hash = await aptos_client.submit_transaction(contract_deployer, payload)
    txn = await aptos_client.wait_for_transaction(txn_hash)
    assert txn["success"]
    
    # Verify function call
    result = await aptos_client.account_resource(
        contract_deployer.address(),
        f"{contract_deployer.address().hex()}::test_contract::TestState"
    )
    
    assert result is not None
    assert "value" in result["data"]

@pytest.mark.asyncio
async def test_contract_events(aptos_client, contract_deployer):
    """Test contract event handling."""
    # Trigger event
    payload = {
        "function": f"{contract_deployer.address().hex()}::test_contract::emit_event",
        "type_arguments": [],
        "arguments": [
            "Test Event"  # event data
        ]
    }
    
    txn_hash = await aptos_client.submit_transaction(contract_deployer, payload)
    txn = await aptos_client.wait_for_transaction(txn_hash)
    assert txn["success"]
    
    # Get events
    events = await aptos_client.get_events_by_handle(
        contract_deployer.address(),
        f"{contract_deployer.address().hex()}::test_contract::TestEvents",
        "test_event"
    )
    
    assert len(events) > 0
    assert events[0]["data"] == "Test Event"

@pytest.mark.asyncio
async def test_contract_upgrade(aptos_client, contract_deployer):
    """Test contract upgrade functionality."""
    # Deploy new version
    with open("tests/contracts/test_contract_v2.mv", "rb") as f:
        contract_bytes = f.read()
    
    payload = {
        "function": "0x1::code::upgrade_package",
        "type_arguments": [],
        "arguments": [
            contract_bytes.hex(),
            []  # init_script
        ]
    }
    
    txn_hash = await aptos_client.submit_transaction(contract_deployer, payload)
    txn = await aptos_client.wait_for_transaction(txn_hash)
    assert txn["success"]
    
    # Verify upgrade
    contract_data = await aptos_client.account_resource(
        contract_deployer.address(),
        "0x1::code::PackageRegistry"
    )
    
    assert contract_data is not None
    assert "packages" in contract_data["data"]

@pytest.mark.asyncio
async def test_contract_state(aptos_client, contract_deployer):
    """Test contract state management."""
    # Update state
    payload = {
        "function": f"{contract_deployer.address().hex()}::test_contract::update_state",
        "type_arguments": [],
        "arguments": [
            "New State Value"  # new value
        ]
    }
    
    txn_hash = await aptos_client.submit_transaction(contract_deployer, payload)
    txn = await aptos_client.wait_for_transaction(txn_hash)
    assert txn["success"]
    
    # Verify state update
    state = await aptos_client.account_resource(
        contract_deployer.address(),
        f"{contract_deployer.address().hex()}::test_contract::TestState"
    )
    
    assert state is not None
    assert state["data"]["value"] == "New State Value"

@pytest.mark.asyncio
async def test_contract_permissions(aptos_client, contract_deployer):
    """Test contract permissions management."""
    # Set permissions
    payload = {
        "function": f"{contract_deployer.address().hex()}::test_contract::set_permissions",
        "type_arguments": [],
        "arguments": [
            "0x1",  # admin address
            "true",  # can_upgrade
            "true",  # can_pause
            "false"  # can_destroy
        ]
    }
    
    txn_hash = await aptos_client.submit_transaction(contract_deployer, payload)
    txn = await aptos_client.wait_for_transaction(txn_hash)
    assert txn["success"]
    
    # Verify permissions
    permissions = await aptos_client.account_resource(
        contract_deployer.address(),
        f"{contract_deployer.address().hex()}::test_contract::Permissions"
    )
    
    assert permissions is not None
    assert "admin" in permissions["data"]
    assert "can_upgrade" in permissions["data"]
    assert "can_pause" in permissions["data"]
    assert "can_destroy" in permissions["data"]

@pytest.mark.asyncio
async def test_contract_pause(aptos_client, contract_deployer):
    """Test contract pause functionality."""
    # Pause contract
    pause_payload = {
        "function": f"{contract_deployer.address().hex()}::test_contract::pause",
        "type_arguments": [],
        "arguments": []
    }
    
    txn_hash = await aptos_client.submit_transaction(contract_deployer, pause_payload)
    txn = await aptos_client.wait_for_transaction(txn_hash)
    assert txn["success"]
    
    # Verify pause
    state = await aptos_client.account_resource(
        contract_deployer.address(),
        f"{contract_deployer.address().hex()}::test_contract::TestState"
    )
    
    assert state is not None
    assert state["data"]["paused"] == True
    
    # Resume contract
    resume_payload = {
        "function": f"{contract_deployer.address().hex()}::test_contract::resume",
        "type_arguments": [],
        "arguments": []
    }
    
    txn_hash = await aptos_client.submit_transaction(contract_deployer, resume_payload)
    txn = await aptos_client.wait_for_transaction(txn_hash)
    assert txn["success"]
    
    # Verify resume
    state = await aptos_client.account_resource(
        contract_deployer.address(),
        f"{contract_deployer.address().hex()}::test_contract::TestState"
    )
    
    assert state is not None
    assert state["data"]["paused"] == False 
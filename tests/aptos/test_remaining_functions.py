import pytest
from aptos_sdk.account import Account, AccountAddress
from aptos_sdk.client import RestClient
from aptos_sdk.transactions import EntryFunction, TransactionArgument
from aptos_sdk.type_tag import TypeTag, StructTag
import json
import time
import asyncio

@pytest.fixture
def aptos_client():
    """Create a test client for Aptos."""
    return RestClient("https://fullnode.testnet.aptoslabs.com")

@pytest.fixture
def test_account():
    """Create a test account."""
    return Account.generate()

@pytest.mark.asyncio
async def test_account_management(aptos_client, test_account):
    """Test account management functions."""
    # Fund account
    await aptos_client.fund_account(test_account.address(), 100_000_000)
    
    # Get account info
    account_info = await aptos_client.account(test_account.address())
    assert account_info is not None
    assert "sequence_number" in account_info
    assert "authentication_key" in account_info
    
    # Get account resources
    resources = await aptos_client.account_resources(test_account.address())
    assert resources is not None
    assert isinstance(resources, list)
    
    # Get account modules
    modules = await aptos_client.account_modules(test_account.address())
    assert modules is not None
    assert isinstance(modules, list)

@pytest.mark.asyncio
async def test_transaction_management(aptos_client, test_account):
    """Test transaction management functions."""
    # Create test transaction
    payload = {
        "function": "0x1::coin::transfer",
        "type_arguments": ["0x1::aptos_coin::AptosCoin"],
        "arguments": [
            "0x1",
            "1000"
        ]
    }
    
    # Submit transaction
    txn_hash = await aptos_client.submit_transaction(test_account, payload)
    assert txn_hash is not None
    
    # Wait for transaction
    txn = await aptos_client.wait_for_transaction(txn_hash)
    assert txn["success"]
    
    # Get transaction
    txn_info = await aptos_client.transaction(txn_hash)
    assert txn_info is not None
    assert txn_info["hash"] == txn_hash
    
    # Get transaction by version
    txn_by_version = await aptos_client.transaction_by_version(txn_info["version"])
    assert txn_by_version is not None
    assert txn_by_version["hash"] == txn_hash

@pytest.mark.asyncio
async def test_block_management(aptos_client):
    """Test block management functions."""
    # Get latest block
    latest_block = await aptos_client.get_latest_block()
    assert latest_block is not None
    assert "block_height" in latest_block
    assert "block_hash" in latest_block
    
    # Get block by height
    block = await aptos_client.get_block_by_height(latest_block["block_height"])
    assert block is not None
    assert block["block_height"] == latest_block["block_height"]
    
    # Get block by version
    block_by_version = await aptos_client.get_block_by_version(latest_block["first_version"])
    assert block_by_version is not None
    assert block_by_version["block_height"] == latest_block["block_height"]

@pytest.mark.asyncio
async def test_event_management(aptos_client):
    """Test event management functions."""
    # Get events by creation number
    events = await aptos_client.get_events_by_creation_number(
        "0x1",
        "0",
        {"start": 0, "limit": 10}
    )
    assert events is not None
    assert isinstance(events, list)
    
    # Get events by event handle
    events_by_handle = await aptos_client.get_events_by_event_handle(
        "0x1",
        "0x1::coin::CoinStore<0x1::aptos_coin::AptosCoin>",
        "deposit_events",
        {"start": 0, "limit": 10}
    )
    assert events_by_handle is not None
    assert isinstance(events_by_handle, list)

@pytest.mark.asyncio
async def test_state_management(aptos_client):
    """Test state management functions."""
    # Get state
    state = await aptos_client.get_state()
    assert state is not None
    assert "chain_id" in state
    assert "ledger_version" in state
    
    # Get state proof
    state_proof = await aptos_client.get_state_proof("0x1")
    assert state_proof is not None
    assert "ledger_info" in state_proof
    assert "state_proof" in state_proof

@pytest.mark.asyncio
async def test_table_management(aptos_client):
    """Test table management functions."""
    # Get table item
    table_item = await aptos_client.get_table_item(
        "0x1",
        "0x1::coin::CoinStore<0x1::aptos_coin::AptosCoin>",
        "coin",
        "0x1"
    )
    assert table_item is not None
    assert "value" in table_item
    
    # Get table items
    table_items = await aptos_client.get_table_items(
        "0x1",
        "0x1::coin::CoinStore<0x1::aptos_coin::AptosCoin>",
        "coin",
        {"start": 0, "limit": 10}
    )
    assert table_items is not None
    assert isinstance(table_items, list)

@pytest.mark.asyncio
async def test_ledger_management(aptos_client):
    """Test ledger management functions."""
    # Get ledger info
    ledger_info = await aptos_client.get_ledger_info()
    assert ledger_info is not None
    assert "chain_id" in ledger_info
    assert "ledger_version" in ledger_info
    
    # Get ledger timestamp
    timestamp = await aptos_client.get_ledger_timestamp()
    assert timestamp is not None
    assert isinstance(timestamp, int)

@pytest.mark.asyncio
async def test_chain_management(aptos_client):
    """Test chain management functions."""
    # Get chain id
    chain_id = await aptos_client.get_chain_id()
    assert chain_id is not None
    assert isinstance(chain_id, int)
    
    # Get chain status
    chain_status = await aptos_client.get_chain_status()
    assert chain_status is not None
    assert "chain_id" in chain_status
    assert "ledger_version" in chain_status

@pytest.mark.asyncio
async def test_indexer_management(aptos_client):
    """Test indexer management functions."""
    # Get indexer status
    indexer_status = await aptos_client.get_indexer_status()
    assert indexer_status is not None
    assert "status" in indexer_status
    
    # Get indexer version
    indexer_version = await aptos_client.get_indexer_version()
    assert indexer_version is not None
    assert "version" in indexer_version

@pytest.mark.asyncio
async def test_metadata_management(aptos_client):
    """Test metadata management functions."""
    # Get metadata
    metadata = await aptos_client.get_metadata()
    assert metadata is not None
    assert "version" in metadata
    assert "chain_id" in metadata
    
    # Get module metadata
    module_metadata = await aptos_client.get_module_metadata("0x1::coin")
    assert module_metadata is not None
    assert "name" in module_metadata
    assert "friends" in module_metadata

@pytest.mark.asyncio
async def test_error_handling(aptos_client, test_account):
    """Test error handling functions."""
    # Test invalid transaction
    invalid_payload = {
        "function": "0x1::invalid::function",
        "type_arguments": [],
        "arguments": []
    }
    
    try:
        await aptos_client.submit_transaction(test_account, invalid_payload)
        assert False, "Should have raised an error"
    except Exception as e:
        assert "invalid" in str(e).lower()
    
    # Test invalid account
    try:
        await aptos_client.account("0xinvalid")
        assert False, "Should have raised an error"
    except Exception as e:
        assert "invalid" in str(e).lower()

@pytest.mark.asyncio
async def test_rate_limiting(aptos_client):
    """Test rate limiting functionality."""
    # Make multiple requests
    for _ in range(10):
        await aptos_client.get_ledger_info()
    
    # Verify rate limit headers
    headers = await aptos_client.get_rate_limit_headers()
    assert headers is not None
    assert "x-ratelimit-limit" in headers
    assert "x-ratelimit-remaining" in headers
    assert "x-ratelimit-reset" in headers 
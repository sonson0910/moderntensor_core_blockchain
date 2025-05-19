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
def validator_account():
    """Create a test validator account."""
    return Account.generate()

@pytest.mark.asyncio
async def test_p2p_connection(aptos_client):
    """Test P2P connection and peer discovery."""
    # Get peer list
    peers = await aptos_client.get_peers()
    assert peers is not None
    assert isinstance(peers, list)
    assert len(peers) > 0
    
    # Get peer info
    peer_info = await aptos_client.get_peer_info(peers[0])
    assert peer_info is not None
    assert "address" in peer_info
    assert "version" in peer_info
    assert "role" in peer_info

@pytest.mark.asyncio
async def test_p2p_message_broadcast(aptos_client):
    """Test P2P message broadcasting."""
    # Create test message
    message = {
        "type": "test_message",
        "data": "Hello P2P Network",
        "timestamp": int(time.time())
    }
    
    # Broadcast message
    payload = {
        "function": "0x1::p2p::broadcast_message",
        "type_arguments": [],
        "arguments": [
            json.dumps(message)
        ]
    }
    
    txn_hash = await aptos_client.submit_transaction(validator_account, payload)
    txn = await aptos_client.wait_for_transaction(txn_hash)
    assert txn["success"]
    
    # Verify message propagation
    messages = await aptos_client.get_p2p_messages()
    assert messages is not None
    assert isinstance(messages, list)
    assert len(messages) > 0
    assert messages[0]["data"] == message["data"]

@pytest.mark.asyncio
async def test_consensus_state(aptos_client):
    """Test consensus state management."""
    # Get consensus state
    consensus_state = await aptos_client.get_consensus_state()
    assert consensus_state is not None
    assert "current_round" in consensus_state
    assert "current_leader" in consensus_state
    assert "validators" in consensus_state
    
    # Get validator set
    validator_set = await aptos_client.get_validator_set()
    assert validator_set is not None
    assert "active_validators" in validator_set
    assert "total_voting_power" in validator_set

@pytest.mark.asyncio
async def test_consensus_participation(aptos_client, validator_account):
    """Test validator participation in consensus."""
    # Fund validator account
    await aptos_client.fund_account(validator_account.address(), 100_000_000)
    
    # Register as validator
    payload = {
        "function": "0x1::validator::register_validator",
        "type_arguments": [],
        "arguments": [
            validator_account.public_key_bytes().hex(),
            "1000000",  # stake amount
            "0x1",  # consensus key
            "0x1",  # validator network address
            "0x1",  # fullnode network address
        ]
    }
    
    txn_hash = await aptos_client.submit_transaction(validator_account, payload)
    txn = await aptos_client.wait_for_transaction(txn_hash)
    assert txn["success"]
    
    # Get validator participation
    participation = await aptos_client.get_validator_participation(validator_account.address())
    assert participation is not None
    assert "proposals" in participation
    assert "votes" in participation
    assert "missed_rounds" in participation

@pytest.mark.asyncio
async def test_block_proposal(aptos_client, validator_account):
    """Test block proposal and validation."""
    # Create test block
    block_data = {
        "transactions": [],
        "timestamp": int(time.time()),
        "previous_block_hash": "0x1"
    }
    
    # Propose block
    payload = {
        "function": "0x1::consensus::propose_block",
        "type_arguments": [],
        "arguments": [
            json.dumps(block_data)
        ]
    }
    
    txn_hash = await aptos_client.submit_transaction(validator_account, payload)
    txn = await aptos_client.wait_for_transaction(txn_hash)
    assert txn["success"]
    
    # Verify block proposal
    proposals = await aptos_client.get_block_proposals()
    assert proposals is not None
    assert isinstance(proposals, list)
    assert len(proposals) > 0

@pytest.mark.asyncio
async def test_consensus_voting(aptos_client, validator_account):
    """Test consensus voting mechanism."""
    # Get current round
    consensus_state = await aptos_client.get_consensus_state()
    current_round = consensus_state["current_round"]
    
    # Submit vote
    vote_data = {
        "round": current_round,
        "block_hash": "0x1",
        "vote_type": "yes"
    }
    
    payload = {
        "function": "0x1::consensus::submit_vote",
        "type_arguments": [],
        "arguments": [
            json.dumps(vote_data)
        ]
    }
    
    txn_hash = await aptos_client.submit_transaction(validator_account, payload)
    txn = await aptos_client.wait_for_transaction(txn_hash)
    assert txn["success"]
    
    # Verify vote
    votes = await aptos_client.get_round_votes(current_round)
    assert votes is not None
    assert isinstance(votes, list)
    assert len(votes) > 0

@pytest.mark.asyncio
async def test_network_broadcast(aptos_client):
    """Test network-wide broadcast functionality."""
    # Create broadcast message
    broadcast_data = {
        "type": "network_update",
        "data": {
            "version": "1.0.0",
            "changes": ["feature1", "feature2"]
        },
        "timestamp": int(time.time())
    }
    
    # Broadcast to network
    payload = {
        "function": "0x1::network::broadcast",
        "type_arguments": [],
        "arguments": [
            json.dumps(broadcast_data)
        ]
    }
    
    txn_hash = await aptos_client.submit_transaction(validator_account, payload)
    txn = await aptos_client.wait_for_transaction(txn_hash)
    assert txn["success"]
    
    # Verify broadcast
    broadcasts = await aptos_client.get_network_broadcasts()
    assert broadcasts is not None
    assert isinstance(broadcasts, list)
    assert len(broadcasts) > 0
    assert broadcasts[0]["data"] == broadcast_data["data"]

@pytest.mark.asyncio
async def test_consensus_sync(aptos_client):
    """Test consensus synchronization."""
    # Get sync status
    sync_status = await aptos_client.get_sync_status()
    assert sync_status is not None
    assert "current_version" in sync_status
    assert "target_version" in sync_status
    assert "sync_progress" in sync_status
    
    # Start sync
    payload = {
        "function": "0x1::consensus::start_sync",
        "type_arguments": [],
        "arguments": []
    }
    
    txn_hash = await aptos_client.submit_transaction(validator_account, payload)
    txn = await aptos_client.wait_for_transaction(txn_hash)
    assert txn["success"]
    
    # Wait for sync
    await asyncio.sleep(5)
    
    # Verify sync completion
    sync_status = await aptos_client.get_sync_status()
    assert sync_status["sync_progress"] == 100 
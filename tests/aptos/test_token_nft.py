import pytest
from aptos_sdk.account import Account, AccountAddress
from aptos_sdk.client import RestClient
from aptos_sdk.transactions import EntryFunction, TransactionArgument
from aptos_sdk.type_tag import TypeTag, StructTag
from decimal import Decimal
import json

@pytest.fixture
def aptos_client():
    """Create a test client for Aptos."""
    return RestClient("https://fullnode.testnet.aptoslabs.com")

@pytest.fixture
def token_creator():
    """Create a test token creator account."""
    return Account.generate()

@pytest.fixture
def nft_creator():
    """Create a test NFT creator account."""
    return Account.generate()

@pytest.mark.asyncio
async def test_token_creation(aptos_client, token_creator):
    """Test token creation process."""
    # Fund the creator account
    await aptos_client.fund_account(token_creator.address(), 100_000_000)
    
    # Create token
    payload = {
        "function": "0x1::token::create_token",
        "type_arguments": [],
        "arguments": [
            "Test Token",  # name
            "TST",  # symbol
            "8",  # decimals
            "1000000",  # supply
            "https://test.token.com",  # url
            "0x1",  # royalty numerator
            "100",  # royalty denominator
        ]
    }
    
    txn_hash = await aptos_client.submit_transaction(token_creator, payload)
    txn = await aptos_client.wait_for_transaction(txn_hash)
    assert txn["success"]
    
    # Verify token creation
    token_data = await aptos_client.account_resource(
        token_creator.address(),
        "0x1::token::TokenStore"
    )
    
    assert token_data is not None
    assert "tokens" in token_data["data"]

@pytest.mark.asyncio
async def test_token_transfer(aptos_client, token_creator):
    """Test token transfer functionality."""
    # Create recipient account
    recipient = Account.generate()
    await aptos_client.fund_account(recipient.address(), 100_000_000)
    
    # Transfer tokens
    payload = {
        "function": "0x1::token::transfer",
        "type_arguments": [],
        "arguments": [
            recipient.address().hex(),
            "1000"  # amount
        ]
    }
    
    txn_hash = await aptos_client.submit_transaction(token_creator, payload)
    txn = await aptos_client.wait_for_transaction(txn_hash)
    assert txn["success"]
    
    # Verify transfer
    recipient_tokens = await aptos_client.account_resource(
        recipient.address(),
        "0x1::token::TokenStore"
    )
    
    assert recipient_tokens is not None
    assert "tokens" in recipient_tokens["data"]

@pytest.mark.asyncio
async def test_nft_creation(aptos_client, nft_creator):
    """Test NFT creation process."""
    # Fund the creator account
    await aptos_client.fund_account(nft_creator.address(), 100_000_000)
    
    # Create NFT collection
    collection_payload = {
        "function": "0x1::token::create_collection",
        "type_arguments": [],
        "arguments": [
            "Test Collection",  # name
            "Test Description",  # description
            "https://test.collection.com",  # url
            "1000",  # max supply
            "0x1",  # royalty numerator
            "100",  # royalty denominator
        ]
    }
    
    txn_hash = await aptos_client.submit_transaction(nft_creator, collection_payload)
    txn = await aptos_client.wait_for_transaction(txn_hash)
    assert txn["success"]
    
    # Create NFT
    nft_payload = {
        "function": "0x1::token::create_token",
        "type_arguments": [],
        "arguments": [
            "Test NFT",  # name
            "Test NFT Description",  # description
            "https://test.nft.com",  # url
            "1",  # supply
            "0x1",  # royalty numerator
            "100",  # royalty denominator
            "Test Collection",  # collection name
        ]
    }
    
    txn_hash = await aptos_client.submit_transaction(nft_creator, nft_payload)
    txn = await aptos_client.wait_for_transaction(txn_hash)
    assert txn["success"]
    
    # Verify NFT creation
    nft_data = await aptos_client.account_resource(
        nft_creator.address(),
        "0x1::token::TokenStore"
    )
    
    assert nft_data is not None
    assert "tokens" in nft_data["data"]

@pytest.mark.asyncio
async def test_nft_transfer(aptos_client, nft_creator):
    """Test NFT transfer functionality."""
    # Create recipient account
    recipient = Account.generate()
    await aptos_client.fund_account(recipient.address(), 100_000_000)
    
    # Transfer NFT
    payload = {
        "function": "0x1::token::transfer",
        "type_arguments": [],
        "arguments": [
            recipient.address().hex(),
            "1"  # token id
        ]
    }
    
    txn_hash = await aptos_client.submit_transaction(nft_creator, payload)
    txn = await aptos_client.wait_for_transaction(txn_hash)
    assert txn["success"]
    
    # Verify transfer
    recipient_nfts = await aptos_client.account_resource(
        recipient.address(),
        "0x1::token::TokenStore"
    )
    
    assert recipient_nfts is not None
    assert "tokens" in recipient_nfts["data"]

@pytest.mark.asyncio
async def test_token_burn(aptos_client, token_creator):
    """Test token burn functionality."""
    # Burn tokens
    payload = {
        "function": "0x1::token::burn",
        "type_arguments": [],
        "arguments": [
            "1000"  # amount
        ]
    }
    
    txn_hash = await aptos_client.submit_transaction(token_creator, payload)
    txn = await aptos_client.wait_for_transaction(txn_hash)
    assert txn["success"]
    
    # Verify burn
    token_data = await aptos_client.account_resource(
        token_creator.address(),
        "0x1::token::TokenStore"
    )
    
    assert token_data is not None
    assert "tokens" in token_data["data"]

@pytest.mark.asyncio
async def test_nft_burn(aptos_client, nft_creator):
    """Test NFT burn functionality."""
    # Burn NFT
    payload = {
        "function": "0x1::token::burn",
        "type_arguments": [],
        "arguments": [
            "1"  # token id
        ]
    }
    
    txn_hash = await aptos_client.submit_transaction(nft_creator, payload)
    txn = await aptos_client.wait_for_transaction(txn_hash)
    assert txn["success"]
    
    # Verify burn
    nft_data = await aptos_client.account_resource(
        nft_creator.address(),
        "0x1::token::TokenStore"
    )
    
    assert nft_data is not None
    assert "tokens" in nft_data["data"]

@pytest.mark.asyncio
async def test_token_metadata(aptos_client, token_creator):
    """Test token metadata management."""
    # Update token metadata
    payload = {
        "function": "0x1::token::update_token_metadata",
        "type_arguments": [],
        "arguments": [
            "New Token Name",  # name
            "New Token Description",  # description
            "https://new.token.com",  # url
        ]
    }
    
    txn_hash = await aptos_client.submit_transaction(token_creator, payload)
    txn = await aptos_client.wait_for_transaction(txn_hash)
    assert txn["success"]
    
    # Verify metadata update
    token_data = await aptos_client.account_resource(
        token_creator.address(),
        "0x1::token::TokenStore"
    )
    
    assert token_data is not None
    assert "tokens" in token_data["data"]

@pytest.mark.asyncio
async def test_nft_metadata(aptos_client, nft_creator):
    """Test NFT metadata management."""
    # Update NFT metadata
    payload = {
        "function": "0x1::token::update_token_metadata",
        "type_arguments": [],
        "arguments": [
            "New NFT Name",  # name
            "New NFT Description",  # description
            "https://new.nft.com",  # url
        ]
    }
    
    txn_hash = await aptos_client.submit_transaction(nft_creator, payload)
    txn = await aptos_client.wait_for_transaction(txn_hash)
    assert txn["success"]
    
    # Verify metadata update
    nft_data = await aptos_client.account_resource(
        nft_creator.address(),
        "0x1::token::TokenStore"
    )
    
    assert nft_data is not None
    assert "tokens" in nft_data["data"] 
import pytest
from aptos_sdk.account import Account, AccountAddress
from aptos_sdk.client import RestClient
from aptos_sdk.transactions import EntryFunction, TransactionArgument
from aptos_sdk.type_tag import TypeTag, StructTag
import os
import json
import base64

@pytest.fixture
def aptos_client():
    """Create a test client for Aptos."""
    return RestClient("https://fullnode.testnet.aptoslabs.com")

@pytest.fixture
def test_account():
    """Create a test account."""
    return Account.generate()

@pytest.mark.asyncio
async def test_key_generation():
    """Test key generation and properties."""
    # Generate new account
    account = Account.generate()
    
    # Test key properties
    assert len(account.private_key_bytes) == 32
    assert len(account.public_key_bytes()) == 32
    assert isinstance(account.address(), AccountAddress)
    
    # Test key derivation
    derived_account = Account.load_key(account.private_key_bytes)
    assert derived_account.address() == account.address()
    assert derived_account.public_key_bytes() == account.public_key_bytes()

@pytest.mark.asyncio
async def test_key_import_export():
    """Test key import and export functionality."""
    # Generate account
    account = Account.generate()
    
    # Export private key
    private_key_hex = account.private_key_bytes.hex()
    private_key_b64 = base64.b64encode(account.private_key_bytes).decode()
    
    # Import from hex
    imported_account_hex = Account.load_key(bytes.fromhex(private_key_hex))
    assert imported_account_hex.address() == account.address()
    
    # Import from base64
    imported_account_b64 = Account.load_key(base64.b64decode(private_key_b64))
    assert imported_account_b64.address() == account.address()

@pytest.mark.asyncio
async def test_key_storage():
    """Test key storage and retrieval."""
    # Create test directory
    test_dir = "test_keys"
    os.makedirs(test_dir, exist_ok=True)
    
    try:
        # Generate and save account
        account = Account.generate()
        key_file = os.path.join(test_dir, "test_key.json")
        
        # Save key
        key_data = {
            "private_key": account.private_key_bytes.hex(),
            "public_key": account.public_key_bytes().hex(),
            "address": account.address().hex()
        }
        with open(key_file, "w") as f:
            json.dump(key_data, f)
        
        # Load key
        with open(key_file, "r") as f:
            loaded_data = json.load(f)
        
        loaded_account = Account.load_key(bytes.fromhex(loaded_data["private_key"]))
        assert loaded_account.address().hex() == account.address().hex()
        assert loaded_account.public_key_bytes().hex() == account.public_key_bytes().hex()
    
    finally:
        # Cleanup
        if os.path.exists(key_file):
            os.remove(key_file)
        if os.path.exists(test_dir):
            os.rmdir(test_dir)

@pytest.mark.asyncio
async def test_key_rotation(aptos_client, test_account):
    """Test key rotation functionality."""
    # Fund the account
    await aptos_client.fund_account(test_account.address(), 100_000_000)
    
    # Generate new key pair
    new_account = Account.generate()
    
    # Rotate key
    payload = {
        "function": "0x1::account::rotate_authentication_key",
        "type_arguments": [],
        "arguments": [
            new_account.public_key_bytes().hex()
        ]
    }
    
    txn_hash = await aptos_client.submit_transaction(test_account, payload)
    txn = await aptos_client.wait_for_transaction(txn_hash)
    assert txn["success"]
    
    # Verify new key works
    new_balance = await aptos_client.account_balance(new_account.address())
    assert isinstance(new_balance, int)

@pytest.mark.asyncio
async def test_multisig_account():
    """Test multisig account creation and management."""
    # Generate multiple accounts for multisig
    accounts = [Account.generate() for _ in range(3)]
    public_keys = [acc.public_key_bytes().hex() for acc in accounts]
    
    # Create multisig account
    multisig_account = Account.generate()
    
    # Add signers
    for i, account in enumerate(accounts):
        payload = {
            "function": "0x1::multisig_account::add_signer",
            "type_arguments": [],
            "arguments": [
                multisig_account.address().hex(),
                public_keys[i]
            ]
        }
        
        txn_hash = await aptos_client.submit_transaction(account, payload)
        txn = await aptos_client.wait_for_transaction(txn_hash)
        assert txn["success"]
    
    # Verify signers
    signers = await aptos_client.account_resource(
        multisig_account.address(),
        "0x1::multisig_account::Signers"
    )
    
    assert signers is not None
    assert "signers" in signers["data"]
    assert len(signers["data"]["signers"]) == 3

@pytest.mark.asyncio
async def test_key_recovery():
    """Test key recovery functionality."""
    # Generate account
    account = Account.generate()
    
    # Create recovery key
    recovery_account = Account.generate()
    
    # Set up recovery
    payload = {
        "function": "0x1::recovery::setup_recovery",
        "type_arguments": [],
        "arguments": [
            recovery_account.address().hex()
        ]
    }
    
    txn_hash = await aptos_client.submit_transaction(account, payload)
    txn = await aptos_client.wait_for_transaction(txn_hash)
    assert txn["success"]
    
    # Verify recovery setup
    recovery_state = await aptos_client.account_resource(
        account.address(),
        "0x1::recovery::RecoveryState"
    )
    
    assert recovery_state is not None
    assert "recovery_address" in recovery_state["data"]
    assert recovery_state["data"]["recovery_address"] == recovery_account.address().hex()

@pytest.mark.asyncio
async def test_key_permissions():
    """Test key permissions and capabilities."""
    # Generate account
    account = Account.generate()
    
    # Set up key permissions
    payload = {
        "function": "0x1::account::set_key_permissions",
        "type_arguments": [],
        "arguments": [
            "0x1::account::KeyPermissions",  # permission type
            "true",  # can_sign
            "true",  # can_rotate
            "false"  # can_recover
        ]
    }
    
    txn_hash = await aptos_client.submit_transaction(account, payload)
    txn = await aptos_client.wait_for_transaction(txn_hash)
    assert txn["success"]
    
    # Verify permissions
    permissions = await aptos_client.account_resource(
        account.address(),
        "0x1::account::KeyPermissions"
    )
    
    assert permissions is not None
    assert "can_sign" in permissions["data"]
    assert "can_rotate" in permissions["data"]
    assert "can_recover" in permissions["data"] 
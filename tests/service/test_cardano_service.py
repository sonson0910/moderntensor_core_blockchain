# tests/service/test_cardano_service.py

import os
import pytest
import logging
from pycardano import Network
from sdk.service.context import get_chain_context
from sdk.service.query_service import get_address_info
from sdk.service.tx_service import send_ada, send_token

logging.basicConfig(level=logging.INFO)

@pytest.fixture(scope="session")
def chain_context_fixture():
    """
    Creates a chain context, specifically a BlockFrostChainContext in TESTNET mode, 
    for use throughout the test session.
    
    Steps:
      1) Read the BLOCKFROST_PROJECT_ID from environment (or use a default if not set).
      2) Call get_chain_context() with the method set to "blockfrost", the provided project_id, 
         and the TESTNET network.
      3) Return the resulting chain context, which can be injected into test functions.

    Returns:
        BlockFrostChainContext: A chain context configured for Cardano TESTNET via Blockfrost.
    """
    project_id = os.getenv("BLOCKFROST_PROJECT_ID", "preprod06dzhzKlynuTInzvxHDH5cXbdHo524DE")
    return get_chain_context(method="blockfrost", project_id=project_id, network=Network.TESTNET)

@pytest.mark.integration
def test_get_chain_context_blockfrost(chain_context_fixture):
    """
    Integration test to verify that the chain_context_fixture is indeed 
    a BlockFrostChainContext instance when using the "blockfrost" method.
    """
    from pycardano import BlockFrostChainContext
    assert isinstance(chain_context_fixture, BlockFrostChainContext), \
        "chain_context_fixture should be an instance of BlockFrostChainContext."

@pytest.mark.integration
def test_get_address_info(chain_context_fixture, hotkey_skey_fixture):
    """
    Test retrieval of address information (UTxOs, lovelace, token balances) 
    using get_address_info.

    Steps:
      1) Decode the hotkey_skey_fixture, which provides a (payment_xsk, stake_xsk).
      2) Construct an Address object from these extended signing keys (TESTNET).
      3) Call get_address_info(...) with this address and the chain context.
      4) Verify the returned dictionary contains the expected fields 
         (lovelace, tokens, address, utxo_count).
    """
    (payment_xsk, stake_xsk) = hotkey_skey_fixture

    from pycardano import Address
    pay_xvk = payment_xsk.to_verification_key()
    stake_xvk = stake_xsk.to_verification_key()
    from_address = Address(pay_xvk.hash(), stake_xvk.hash(), network=Network.TESTNET)

    info = get_address_info(str(from_address), chain_context_fixture)
    assert "lovelace" in info, "Response dict should contain 'lovelace' key."
    assert "tokens" in info, "Response dict should contain 'tokens' key."
    logging.info(f"Address info: {info}")

    # Check whether the returned address is correct and that UTXO count is non-negative
    assert info["address"] == str(from_address), "Address in info should match from_address."
    assert info["utxo_count"] >= 0, "UTXO count should be a non-negative integer."

@pytest.mark.integration
def test_send_ada(chain_context_fixture, hotkey_skey_fixture):
    """
    Integration test to send a small amount of ADA (1_000_000 lovelace => 1 ADA) 
    from the hotkey's address to a test receiver address.

    Steps:
      1) Obtain (payment_xsk, stake_xsk) from hotkey_skey_fixture.
      2) Retrieve or default to a TEST_RECEIVER_ADDRESS environment variable 
         for the destination address.
      3) Call send_ada(...) using the chain_context_fixture, which should 
         build and submit a transaction.
      4) Confirm the returned transaction ID (tx_id) is non-empty.

    Note:
      This test requires that the hotkey address has enough funds on TESTNET 
      to cover fees and the sent amount. Otherwise, it may fail.
    """
    (payment_xsk, stake_xsk) = hotkey_skey_fixture

    # Load the receiver address from environment or fall back to a default
    to_address_str = os.getenv(
        "TEST_RECEIVER_ADDRESS",
        "addr_test1qpkxr3kpzex93m646qr7w82d56md2kchtsv9jy39dykn4cmcxuuneyeqhdc4wy7de9mk54fndmckahxwqtwy3qg8pums5vlxhz"
    )

    tx_id = send_ada(
        chain_context=chain_context_fixture,
        payment_xsk=payment_xsk,
        stake_xsk=stake_xsk,
        to_address_str=to_address_str,
        lovelace_amount=1_000_000,  # 1 ADA in lovelace
        network=Network.TESTNET,
    )
    logging.info(f"send_ada => {tx_id}")
    assert len(tx_id) > 0, "Transaction ID should be a non-empty string upon success."

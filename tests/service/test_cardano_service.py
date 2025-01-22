# tests/service/test_cardano_service.py

import os
import pytest
from pycardano import Network

from sdk.config.settings import settings, logger  # Use the global logger & settings
from sdk.service.context import get_chain_context
from sdk.service.query_service import get_address_info
from sdk.service.tx_service import send_ada


@pytest.fixture(scope="session")
def chain_context_fixture():
    """
    Creates a chain context, specifically a BlockFrostChainContext in TESTNET mode, 
    for use throughout the test session.

    Steps:
      1) Reads the BLOCKFROST_PROJECT_ID from environment or settings (if implemented).
      2) Calls get_chain_context() with method="blockfrost".
      3) Returns the resulting chain context, which can be injected into test functions.

    Returns:
        BlockFrostChainContext: A chain context configured for Cardano TESTNET via Blockfrost.
    """
    # If you want to pass in a specific project_id, you can read from settings:
    # project_id = settings.BLOCKFROST_PROJECT_ID
    # return get_chain_context(method="blockfrost", project_id=project_id, network=Network.TESTNET)
    return get_chain_context(method="blockfrost")


@pytest.mark.integration
def test_get_chain_context_blockfrost(chain_context_fixture):
    """
    Integration test to verify that chain_context_fixture is indeed 
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
      1) Decode (payment_xsk, stake_xsk) from hotkey_skey_fixture.
      2) Construct an Address object (TESTNET).
      3) Call get_address_info(...) with this address and chain_context_fixture.
      4) Verify the returned dictionary contains 'lovelace', 'tokens', 'address', 'utxo_count'.
    """
    (payment_xsk, stake_xsk) = hotkey_skey_fixture
    from pycardano import Address

    pay_xvk = payment_xsk.to_verification_key()
    stake_xvk = stake_xsk.to_verification_key()
    from_address = Address(payment_part=pay_xvk.hash(), staking_part=stake_xvk.hash(), network=Network.TESTNET)

    info = get_address_info(str(from_address), chain_context_fixture)
    assert "lovelace" in info, "Response dict should contain 'lovelace' key."
    assert "tokens" in info, "Response dict should contain 'tokens' key."
    logger.info(f"Address info: {info}")

    # Check address match and non-negative UTxO count
    assert info["address"] == str(from_address), "Address in info should match from_address."
    assert info["utxo_count"] >= 0, "UTXO count should be a non-negative integer."


@pytest.mark.integration
def test_send_ada(chain_context_fixture, hotkey_skey_fixture):
    """
    Integration test to send 1 ADA from the hotkey's address to a test receiver address.

    Steps:
      1) Obtain (payment_xsk, stake_xsk).
      2) Determine test receiver address from environment or default.
      3) Call send_ada(...) with the chain_context_fixture.
      4) Verify the transaction ID (tx_id) is non-empty.

    Note:
      The hotkey address must have enough funds on TESTNET for this to succeed.
    """
    (payment_xsk, stake_xsk) = hotkey_skey_fixture

    # Load the receiver address from env or default
    to_address_str = os.getenv(
        "TEST_RECEIVER_ADDRESS",
        "addr_test1qpkxr3kpzex93m646qr7w82d56md2kchtsv9jy39dykn4cmcxuuneyeqhdc4wy7de9mk54fndmckahxwqtwy3qg8pums5vlxhz"
    )

    tx_id = send_ada(
        chain_context=chain_context_fixture,
        payment_xsk=payment_xsk,
        stake_xsk=stake_xsk,
        to_address_str=to_address_str,
        lovelace_amount=1_000_000,  # 1 ADA
        network=Network.TESTNET,
    )
    logger.info(f"send_ada => {tx_id}")
    assert len(tx_id) > 0, "Transaction ID should be a non-empty string upon success."

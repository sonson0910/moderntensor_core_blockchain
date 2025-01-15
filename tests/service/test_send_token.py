# tests/service/test_send_token.py

import os
import pytest
import logging
from pycardano import Network
from sdk.service.tx_service import send_token
from sdk.service.context import get_chain_context

@pytest.fixture(scope="session")
def chain_context_fixture():
    """
    Creates a BlockFrost-based chain context for Cardano TESTNET.

    Steps:
      1) Reads the BLOCKFROST_PROJECT_ID from the environment or defaults 
         to "preprod06dzhzKlynuTInzvxHDH5cXbdHo524DE".
      2) Calls get_chain_context(...) with method="blockfrost" to initialize 
         the BlockFrostChainContext on TESTNET.
      3) Returns this chain context fixture for use in tests.
    """
    project_id = os.getenv("BLOCKFROST_PROJECT_ID", "preprod06dzhzKlynuTInzvxHDH5cXbdHo524DE")
    return get_chain_context(method="blockfrost", project_id=project_id, network=Network.TESTNET)

logging.basicConfig(level=logging.INFO)

@pytest.mark.integration
def test_send_michielcoin(chain_context_fixture, hotkey_skey_fixture):
    """
    Integration test to send 50 "MichielCOIN" (MIT) tokens using send_token(...) 
    from a hotkey-based address to a receiver address.

    Prerequisites:
      - "MichielCOIN" token is already minted under a known policy_id.
      - The environment variables provide:
          TEST_RECEIVER_ADDRESS: The destination address.
          TEST_POLICY_ID_HEX: The policy ID for "MichielCOIN".
      - The hotkey fixture has enough UTxOs (ADA + token) for the transfer.

    Steps:
      1) Read the receiver address from the environment. If none is set, skip the test.
      2) Read the policy_id_hex from the environment. If none is set, skip the test.
      3) Prepare base_dir, coldkey_name, hotkey_name, and password from ENV or defaults.
      4) Call send_token(...), specifying how many tokens to send, to which address, 
         and the network context.
      5) Verify the returned tx_id is non-empty, indicating a successful submission.

    Note:
      - This test requires that the hotkey's address actually holds at least 50 "MichielCOIN" 
        plus enough ADA to cover fees (transaction fee is set to 200_000 lovelace here).
      - If the address does not have enough tokens or ADA, the transaction will fail, 
        and the test will likely fail or raise an exception.
    """

    # 1) Read the receiver address from environment (or use a default). If not set, skip.
    to_address_str = os.getenv(
        "TEST_RECEIVER_ADDRESS",
        "addr_test1qpkxr3kpzex93m646qr7w82d56md2kchtsv9jy39dykn4cmcxuuneyeqhdc4wy7de9mk54fndmckahxwqtwy3qg8pums5vlxhz"
    )
    if not to_address_str:
        pytest.skip("TEST_RECEIVER_ADDRESS not set => skipping test_send_michielcoin")

    # 2) Read the policy ID from environment (or use default). If not set, skip.
    policy_id_hex = os.getenv(
        "TEST_POLICY_ID_HEX",
        "b9107b627e28700da1c5c2077c40b1c7d1fe2e9b23ff20e0e6b8fec1"
    )
    if not policy_id_hex:
        pytest.skip("TEST_POLICY_ID_HEX not set => skipping test_send_michielcoin")

    # 3) Gather base directory and coldkey config from environment or use default
    base_dir = os.getenv("HOTKEY_BASE_DIR", "moderntensor")
    coldkey_name = os.getenv("COLDKEY_NAME", "kickoff")
    hotkey_name = os.getenv("HOTKEY_NAME", "hk1")
    password = os.getenv("HOTKEY_PASSWORD", "sonlearn2003")

    # Number of tokens to send and the asset's name
    token_amount = 50
    asset_name   = "MIT"

    # 4) Call send_token(...) with the chain context, specifying all required parameters
    tx_id = send_token(
        chain_context=chain_context_fixture,
        base_dir=base_dir,
        coldkey_name=coldkey_name,
        hotkey_name=hotkey_name,
        password=password,
        to_address_str=to_address_str,
        policy_id_hex=policy_id_hex,
        asset_name=asset_name,
        token_amount=token_amount,
        fee=200_000,           # 0.2 ADA fee
        network=Network.TESTNET
    )

    logging.info(f"[test_send_michielcoin] => TX ID: {tx_id}")

    # 5) Validate the transaction ID is not empty
    assert len(tx_id) > 0, "Transaction ID is empty => token transfer failed"

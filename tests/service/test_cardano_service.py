# tests/service/test_cardano_service.py

import os
import pytest
import logging
from pycardano import Network
from sdk.service.context import get_chain_context
from sdk.service.query_service import get_address_info
from sdk.service.tx_service import send_ada # send_token

logging.basicConfig(level=logging.INFO)

@pytest.fixture(scope="session")
def chain_context_fixture():
    """
    Tạo chain_context (BlockFrost testnet)
    """
    project_id = os.getenv("BLOCKFROST_PROJECT_ID", "preprod06dzhzKlynuTInzvxHDH5cXbdHo524DE")
    return get_chain_context(method="blockfrost", project_id=project_id, network=Network.TESTNET)

# XÓA: @pytest.fixture(scope="session") def hotkey_skey_fixture(): ... 
# => Chúng ta đã định nghĩa fixture hotkey_skey_fixture trong conftest.py

@pytest.mark.integration
def test_get_chain_context_blockfrost(chain_context_fixture):
    from pycardano import BlockFrostChainContext
    assert isinstance(chain_context_fixture, BlockFrostChainContext)

@pytest.mark.integration
def test_get_address_info(chain_context_fixture, hotkey_skey_fixture):
    (payment_xsk, stake_xsk) = hotkey_skey_fixture

    from pycardano import Address
    pay_xvk = payment_xsk.to_verification_key()
    stake_xvk = stake_xsk.to_verification_key()
    from_address = Address(pay_xvk.hash(), stake_xvk.hash(), network=Network.TESTNET)

    info = get_address_info(str(from_address), chain_context_fixture)
    assert "lovelace" in info
    assert "tokens" in info
    logging.info(f"Address info: {info}")
    assert info["address"] == str(from_address)
    assert info["utxo_count"] >= 0

@pytest.mark.integration
def test_send_ada(chain_context_fixture, hotkey_skey_fixture):
    # hotkey_skey_fixture => (payment_xsk, stake_xsk)
    (payment_xsk, stake_xsk) = hotkey_skey_fixture

    # Tạo address
    to_address_str = os.getenv("TEST_RECEIVER_ADDRESS", "addr_test1qpkxr3kpzex93m646qr7w82d56md2kchtsv9jy39dykn4cmcxuuneyeqhdc4wy7de9mk54fndmckahxwqtwy3qg8pums5vlxhz")

    tx_id = send_ada(
        chain_context=chain_context_fixture,
        payment_xsk=payment_xsk,
        stake_xsk=stake_xsk,
        to_address_str=to_address_str,
        lovelace_amount=1_000_000,
        network=Network.TESTNET,
    )
    logging.info(f"send_ada => {tx_id}")
    assert len(tx_id) > 0

# @pytest.mark.integration
# def test_send_token(chain_context_fixture, hotkey_skey_fixture):
#     from pycardano import Address
#     xvk = hotkey_skey_fixture.to_verification_key()
#     from_address = Address(xvk.hash(), network=Network.TESTNET)
#     to_address_str = os.getenv("TEST_RECEIVER_ADDRESS", str(from_address))

#     policy_id = os.getenv("TEST_TOKEN_POLICY", "abc123...")
#     asset_name = os.getenv("TEST_TOKEN_NAME", "MYTOKEN")
#     token_amount = 1
#     lovelace_amount = 2_000_000

#     tx_id = send_token(
#         chain_context=chain_context_fixture,
#         from_signing_key=hotkey_skey_fixture,
#         to_address_str=to_address_str,
#         policy_id=policy_id,
#         asset_name=asset_name,
#         token_amount=token_amount,
#         lovelace_amount=lovelace_amount,
#         network=Network.TESTNET,
#     )
#     logging.info(f"send_token => tx_id: {tx_id}")
#     assert len(tx_id) > 0

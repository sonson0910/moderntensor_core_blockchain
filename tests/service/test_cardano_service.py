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
    Create chain_context (BlockFrost testnet)
    """
    project_id = os.getenv("BLOCKFROST_PROJECT_ID", "preprod06dzhzKlynuTInzvxHDH5cXbdHo524DE")
    return get_chain_context(method="blockfrost", project_id=project_id, network=Network.TESTNET)

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
# def test_send_michielcoin(chain_context_fixture, hotkey_skey_fixture):
#     """
#     Demo test: Gọi send_token_lowlevel_hotkey => gửi 50 "MichielCOIN".
    
#     Giả sử token "MichielCOIN" đã minted => 
#     'policy_id_hex' => sẵn => 
#     => Gửi sang to_address (ENV: TEST_RECEIVER_ADDRESS).
#     """

#     # 1) Lấy to_address_str từ ENV => nếu chưa set => skip
#     to_address_str = os.getenv("TEST_RECEIVER_ADDRESS", "")
#     if not to_address_str:
#         pytest.skip("Chưa set TEST_RECEIVER_ADDRESS => skip test_send_michielcoin")

#     # 2) policy_id_hex => 
#     #    - Hoặc lấy từ fixture minted_policy_id
#     #    - Hoặc cứng => "abc123..." (VD 56 hex)
#     #    - Ở đây DEMO => ENV: 'TEST_POLICY_ID_HEX' hoặc skip
#     policy_id_hex = "b9107b627e28700da1c5c2077c40b1c7d1fe2e9b23ff20e0e6b8fec1"

#     # 3) Gọi hàm send_token_lowlevel_hotkey
#     # chain_context_fixture => fixture conftest
#     # base_dir, coldkey_name, hotkey_name, password => 
#     #    => Lấy từ ENV => HOẶC code cứng => DEMO bên dưới
    
#     base_dir = os.getenv("HOTKEY_BASE_DIR", "moderntensor")
#     coldkey_name = os.getenv("COLDKEY_NAME", "kickoff")
#     hotkey_name = os.getenv("HOTKEY_NAME", "hk1")
#     password = os.getenv("HOTKEY_PASSWORD", "sonlearn2003")

#     token_amount = 50
#     asset_name   = "MIT"

#     tx_id = send_token(
#         chain_context=chain_context_fixture,
#         base_dir=base_dir,
#         coldkey_name=coldkey_name,
#         hotkey_name=hotkey_name,
#         password=password,
#         to_address_str=to_address_str,
#         policy_id_hex=policy_id_hex,
#         asset_name=asset_name,
#         token_amount=token_amount,
#         fee=200_000,
#         network=Network.TESTNET
#     )

#     logging.info(f"[test_send_michielcoin] => TX ID: {tx_id}")
#     assert len(tx_id) > 0, "Gửi token fail => tx_id rỗng"
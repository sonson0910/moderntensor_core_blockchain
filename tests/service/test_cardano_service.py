# tests/test_cardano_tx.py

import os
import pytest
import logging
from pycardano import PaymentSigningKey, Network

# Giả sử bạn có sẵn các hàm này
from sdk.node.cardano_service.context import get_chain_context
from sdk.node.cardano_service.query_service import get_address_info
from sdk.node.cardano_service.tx_service import send_ada, send_token

logging.basicConfig(level=logging.INFO)

@pytest.fixture(scope="session")
def chain_context_fixture():
    """
    Tạo chain_context bằng Blockfrost (testnet).
    Yêu cầu bạn đặt BLOCKFROST_PROJECT_ID trong biến môi trường,
    hoặc truyền cứng 1 API key vào đây (cẩn thận bảo mật).
    """
    project_id = os.getenv("BLOCKFROST_PROJECT_ID", "YOUR_BLOCKFROST_API_KEY")
    context = get_chain_context(
        method="blockfrost",
        project_id=project_id,
        network=Network.TESTNET
    )
    return context

@pytest.fixture(scope="session")
def hotkey_skey_fixture():
    """
    Fixture nạp private key (PaymentSigningKey) từ file .skey.
    Tài khoản này phải có 1 ít ADA để test.
    """
    skey_path = os.getenv("HOTKEY_SKEY_PATH", "tests/keys/my_hotkey.skey")
    skey = PaymentSigningKey.load(skey_path)
    return skey

@pytest.mark.integration
def test_get_address_info(chain_context_fixture, hotkey_skey_fixture):
    """
    Test hàm get_address_info: Lấy UTxO, balance,... của 1 địa chỉ.
    """
    from_address = hotkey_skey_fixture.to_public_key().to_address(Network.TESTNET)
    info = get_address_info(str(from_address), chain_context_fixture)
    assert "lovelace" in info
    assert "tokens" in info
    logging.info(f"Address info: {info}")
    # Kiểm tra cơ bản
    assert info["address"] == str(from_address)
    assert info["utxo_count"] >= 0

@pytest.mark.integration
def test_send_ada(chain_context_fixture, hotkey_skey_fixture):
    """
    Test gửi 1 ADA đến 1 địa chỉ test.
    Cần đảm bảo hotkey này có ít nhất vài ADA để test.
    """
    from_address = hotkey_skey_fixture.to_public_key().to_address(Network.TESTNET)
    to_address_str = os.getenv("TEST_RECEIVER_ADDRESS", str(from_address))
    # Nếu không có địa chỉ người nhận trong env, mặc định gửi cho chính mình

    tx_id = send_ada(
        chain_context=chain_context_fixture,
        from_signing_key=hotkey_skey_fixture,
        to_address_str=to_address_str,
        lovelace_amount=1_000_000,  # 1 ADA
        network=Network.TESTNET
    )
    logging.info(f"send_ada => tx_id: {tx_id}")
    assert len(tx_id) > 0

@pytest.mark.integration
def test_send_token(chain_context_fixture, hotkey_skey_fixture):
    """
    Test gửi 1 token bất kỳ (policy_id + asset_name),
    đòi hỏi hotkey này đang sở hữu token đó trong UTxO.
    """
    from_address = hotkey_skey_fixture.to_public_key().to_address(Network.TESTNET)
    to_address_str = os.getenv("TEST_RECEIVER_ADDRESS", str(from_address))

    # Ví dụ token "MOD" (giả định) với policy_id "abcdef1234..." -> thay thật
    policy_id = os.getenv("TEST_TOKEN_POLICY", "abc123...") 
    asset_name = os.getenv("TEST_TOKEN_NAME", "MYTOKEN") 
    token_amount = 1
    lovelace_amount = 2_000_000  # cần ~2 ADA để kèm token

    tx_id = send_token(
        chain_context=chain_context_fixture,
        from_signing_key=hotkey_skey_fixture,
        to_address_str=to_address_str,
        policy_id=policy_id,
        asset_name=asset_name,
        token_amount=token_amount,
        lovelace_amount=lovelace_amount,
        network=Network.TESTNET
    )
    logging.info(f"send_token => tx_id: {tx_id}")
    assert len(tx_id) > 0

from dataclasses import dataclass
import pytest
from pycardano import (
    UTxO,
    TransactionInput,
    TransactionOutput,
    Address,
    Value,
    PlutusV3Script,
    Redeemer,
    PaymentSigningKey,
    BlockFrostChainContext,
    Network,
    VerificationKeyHash,
    TransactionId,
    PlutusData
)
from remove_fake_utxo import remove_fake_utxos

# Giả lập lớp HelloWorldDatum từ unlock.py
@dataclass
class HelloWorldDatum(PlutusData):
    CONSTR_ID = 0
    owner: bytes

# Fixture chain context
@pytest.fixture
def chain_context():
    """Tạo ngữ cảnh chuỗi blockchain cho testnet."""
    # Thay bằng API key thực tế khi chạy
    api_key = "your_blockfrost_api_key"
    return BlockFrostChainContext(api_key, Network.TESTNET)

# Fixture giả lập danh sách UTxO giả mạo
@pytest.fixture
def fake_utxos():
    """Tạo danh sách UTxO giả mạo để kiểm thử."""
    contract_address = Address.from_primitive("your_contract_address")  # Thay bằng địa chỉ hợp đồng thực tế
    # UTxO giả mạo 1
    datum1 = HelloWorldDatum(owner=b'fake_owner_1')
    utxo1 = UTxO(
        input=TransactionInput.from_primitive(["fake_tx_hash_1", 0]),
        output=TransactionOutput(
            address=contract_address,
            amount=Value(2_000_000),  # 2 tADA
            datum=datum1,
        ),
    )
    # UTxO giả mạo 2
    datum2 = HelloWorldDatum(owner=b'fake_owner_2')
    utxo2 = UTxO(
        input=TransactionInput.from_primitive(["fake_tx_hash_2", 1]),
        output=TransactionOutput(
            address=contract_address,
            amount=Value(3_000_000),  # 3 tADA
            datum=datum2,
        ),
    )
    return [utxo1, utxo2]

# Fixture script hợp đồng
@pytest.fixture
def script():
    """Tạo script hợp đồng Plutus giả lập."""
    return PlutusV3Script(b'fake_script_bytes')

# Fixture redeemer
@pytest.fixture
def redeemer():
    """Tạo redeemer đơn giản."""
    return Redeemer(0)

# Fixture signing key và owner
@pytest.fixture
def signing_key_and_owner():
    """Tạo signing key và owner giả lập."""
    signing_key = PaymentSigningKey.from_json('{"type": "PaymentSigningKeyShelley_ed25519", "description": "Payment Signing Key", "cborHex": "5820..."}')  # Thay bằng khóa thực tế
    owner = VerificationKeyHash(bytes.fromhex("fake_owner_hash"))  # Thay bằng hash thực tế
    return signing_key, owner

# Hàm kiểm thử
def test_remove_fake_utxos(chain_context, fake_utxos, script, redeemer, signing_key_and_owner):
    """Kiểm thử service xóa UTxO giả mạo."""
    signing_key, owner = signing_key_and_owner

    # Gọi service để xóa UTxO giả mạo
    tx_id = remove_fake_utxos(
        fake_utxos=fake_utxos,
        script=script,
        redeemer=redeemer,
        signing_key=signing_key,
        owner=owner,
        context=chain_context,
    )

    # Kiểm tra kết quả
    assert tx_id is not None, "Transaction ID không được rỗng"
    assert isinstance(tx_id, TransactionId), "Transaction ID không hợp lệ"
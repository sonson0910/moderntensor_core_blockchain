from dataclasses import dataclass
import pytest
from pycardano import (
    Address,
    PlutusV3Script,
    Redeemer,
    Network,
    TransactionId,
    PlutusData
)
from sdk.metagraph.remove_fake_utxo import remove_fake_utxos
from sdk.service.context import get_chain_context
from sdk.smartcontract.validator import read_validator
from sdk.service.utxos import get_utxo_from_str
from sdk.metagraph.metagraph_datum import MinerDatum  # Lớp MinerDatum từ file metagraph_datum.py


# Giả lập lớp HelloWorldDatum từ unlock.py
@dataclass
class HelloWorldDatum(PlutusData):
    CONSTR_ID = 0
    owner: bytes

# Fixture cung cấp chain context
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

# Fixture giả lập danh sách UTxO giả mạo
@pytest.fixture
def fake_utxos():
    """Tạo một UTxO giả lập với datum ban đầu."""
    validator=read_validator()
    script_hash = validator["script_hash"]  # Thay bằng hash của hợp đồng Plutus
    contract_address = Address(
        payment_part = script_hash,
        network=Network.TESTNET,
    )
    utxo=get_utxo_from_str(contract_address=contract_address, datumclass=MinerDatum, context=chain_context_fixture)
    return [utxo]

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


# Hàm kiểm thử
def test_remove_fake_utxos(chain_context_fixture, fake_utxos, script, redeemer, hotkey_skey_fixture):
    """Kiểm thử service xóa UTxO giả mạo."""
    (payment_xsk, stake_xsk) = hotkey_skey_fixture
    network = Network.TESTNET
    validator=read_validator()
    script = validator["script_bytes"]  # Thay bằng hash của hợp đồng Plutus

    # Gọi service để xóa UTxO giả mạo
    tx_id = remove_fake_utxos(
        payment_xsk=payment_xsk,
        stake_xsk=stake_xsk,
        fake_utxos=fake_utxos,
        script=script,
        redeemer=redeemer,
        context=chain_context_fixture,
        network=network
    )

    # Kiểm tra kết quả
    assert tx_id is not None, "Transaction ID không được rỗng"
    assert isinstance(tx_id, TransactionId), "Transaction ID không hợp lệ"
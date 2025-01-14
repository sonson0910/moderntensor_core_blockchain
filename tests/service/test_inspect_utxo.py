import os
import pytest
import logging
from pycardano import Address, Network, MultiAsset, Asset
from sdk.service.context import get_chain_context


import os
import pytest
import logging
from pycardano import Address, Network

import logging

# Thêm config ghi ra file
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler("inspect_utxo.log", mode="w"),
        logging.StreamHandler()  # Vẫn log ra console
    ]
)
logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO)

@pytest.fixture(scope="session")
def chain_context_fixture():
    """
    Create chain_context (BlockFrost testnet)
    """
    project_id = os.getenv("BLOCKFROST_PROJECT_ID", "preprod06dzhzKlynuTInzvxHDH5cXbdHo524DE")
    return get_chain_context(method="blockfrost", project_id=project_id, network=Network.TESTNET)

@pytest.mark.integration
def test_inspect_utxo(chain_context_fixture, hotkey_skey_fixture):
    """
    Test này chỉ để in ra (inspect) UTxOs tại địa chỉ from_address =>
    Kiểm tra policy_id, asset_name, quantity thực sự có trong UTxOs.
    """

    (payment_xsk, stake_xsk) = hotkey_skey_fixture
    from_network = chain_context_fixture.network  # TESTNET
    pay_xvk = payment_xsk.to_verification_key()
    stake_xvk = stake_xsk.to_verification_key() if stake_xsk else None

    from_address = Address(
        payment_part=pay_xvk.hash(),
        staking_part=stake_xvk.hash() if stake_xsk else None,
        network=from_network
    )
    print(f"from_address = {from_address}")

    # Lấy UTxOs
    utxos = chain_context_fixture.utxos(from_address)
    if not utxos:
        print("No UTxOs found => Possibly 0 token + 0 ADA here.")
        return

    # In ra chi tiết từng UTxO
    for idx, utxo in enumerate(utxos, start=1):
        print(f"\n--- UTxO #{idx} ---")
        print(f"Input (tx_in) : {utxo.input}")
        print(f"ADA coin      : {utxo.output.amount.coin}")
        ma = utxo.output.amount.multi_asset
        if ma:
            for policy_id, assets_map in ma.items():
                for aname, qty in assets_map.items():
                    # policy_id = ScriptHash => policy_id.payload => bytes => .hex()
                    # aname     = AssetName => aname.payload => bytes => decode
                    policy_id_hex = policy_id.payload.hex()
                    asset_name_str = aname.payload.decode("utf-8", errors="replace")

                    print(
                        f"  policy_id={policy_id_hex} "
                        f"asset_name={asset_name_str} "
                        f"quantity={qty}"
                    )
        else:
            print("No multi-asset tokens in this UTxO")

    assert True  # Test "inspect" => pass

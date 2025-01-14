# tests/service/test_mint_michielcoin.py

import os
import pytest
import logging
from os.path import exists

from pycardano import (
    PaymentKeyPair,
    PaymentSigningKey,
    PaymentVerificationKey,
    ScriptPubkey,
    ScriptAll,
    TransactionBuilder,
    TransactionOutput,
    Value,
    AssetName,
    Asset,
    MultiAsset,
    min_lovelace,
    Address,
    Network
)

from sdk.service.context import get_chain_context


@pytest.fixture(scope="session")
def chain_context_fixture():
    """
    Create chain_context (BlockFrost testnet)
    """
    project_id = os.getenv("BLOCKFROST_PROJECT_ID", "preprod06dzhzKlynuTInzvxHDH5cXbdHo524DE")
    return get_chain_context(method="blockfrost", project_id=project_id, network=Network.TESTNET)

@pytest.mark.integration
def test_mint_mit_token(chain_context_fixture, hotkey_skey_fixture):
    """
    Test: Dùng "logic cũ" để mint 100 token "MichielCOIN" 
    => (1) if policy.skey/policy.vkey not exist => generate => store in coldkey dir
    => (2) build transaction => mint => (payment_skey, policy_skey).
    => (3) Submit => check success
    """

    # 0) Lấy Payment key (hotkey) từ fixture => (payment_skey, staking_skey)
    (payment_skey, staking_skey) = hotkey_skey_fixture
    logging.info("[test_mint_michielcoin] Start test to mint 'MichielCOIN' with hotkey as payment key")

    # 1) Tạo main_address, receive_address
    from_network = chain_context_fixture.network
    main_address = Address(
        payment_part=payment_skey.to_verification_key().hash(),
        staking_part=staking_skey.to_verification_key().hash(),
        network=from_network,
    )

    # Theo logic cũ => child #1 => code gốc => ta tạm reuse main_address => tuỳ.
    receive_address = main_address

    logging.info(f"main_address   = {main_address}")
    logging.info(f"receive_address= {receive_address}")

    # 2) Kiểm tra UTxO => nếu không có => skip
    utxos = chain_context_fixture.utxos(main_address)
    if not utxos:
        pytest.skip("main_address does not have any UTxOs => skip mint test")

    # 3) builder
    builder = TransactionBuilder(chain_context_fixture)

    # 4) Xác định coldkey_dir => Lưu policy key
    base_dir = os.getenv("HOTKEY_BASE_DIR", "moderntensor")
    coldkey_name = os.getenv("COLDKEY_NAME", "kickoff")
    coldkey_dir = os.path.join(base_dir, coldkey_name)
    os.makedirs(coldkey_dir, exist_ok=True)

    policy_skey_path = os.path.join(coldkey_dir, "policy.skey")
    policy_vkey_path = os.path.join(coldkey_dir, "policy.vkey")

    # 5) Generate policy key pair if not exist => store in coldkey_dir
    if not exists(policy_skey_path) and not exists(policy_vkey_path):
        key_pair = PaymentKeyPair.generate()
        key_pair.signing_key.save(policy_skey_path)
        key_pair.verification_key.save(policy_vkey_path)
        logging.info(f"[test_mint_michielcoin] Generated policy key => {policy_skey_path}, {policy_vkey_path}")

    # 6) load policy signing / verification => create script
    policy_signing_key = PaymentSigningKey.load(policy_skey_path)
    policy_verification_key = PaymentVerificationKey.load(policy_vkey_path)
    pub_key_policy = ScriptPubkey(policy_verification_key.hash())
    policy = ScriptAll([pub_key_policy])

    policy_id = policy.hash()
    policy_id_hex = policy_id.payload.hex()
    logging.info(f"[test_mint_michielcoin] policy_id = {policy_id_hex}")

    # 7) Tạo multiasset => 100 "MichielCOIN"
    asset_name = "MIT"
    asset_name_bytes = asset_name.encode("utf-8")
    token_asset_name = AssetName(asset_name_bytes)

    new_asset = Asset()
    new_asset[token_asset_name] = 1000000

    multiasset = MultiAsset()
    multiasset[policy_id] = new_asset

    builder.native_scripts = [policy]
    builder.mint = multiasset

    # 8) Tính min_lovelace => add output => receive_address
    min_val = min_lovelace(
        chain_context_fixture,
        output=TransactionOutput(receive_address, Value(0, multiasset))
    )
    builder.add_output(
        TransactionOutput(receive_address, Value(min_val, multiasset))
    )

    # 9) add input => main_address => build
    builder.add_input_address(main_address)

    # 10) build_and_sign => [payment_skey, policy_signing_key]
    signed_tx = builder.build_and_sign(
        signing_keys=[payment_skey, policy_signing_key],
        change_address=main_address
    )

    # 11) submit
    result = chain_context_fixture.submit_tx(signed_tx.to_cbor())

    logging.info(f"Number of inputs : {len(signed_tx.transaction_body.inputs)}")
    logging.info(f"Number of outputs: {len(signed_tx.transaction_body.outputs)}")
    logging.info(f"Fee             : {signed_tx.transaction_body.fee/1_000_000} ADA")
    logging.info(f"Transaction submitted => {result}")

    # 12) check
    assert len(result) > 0, "Tx ID rỗng => mint fail"

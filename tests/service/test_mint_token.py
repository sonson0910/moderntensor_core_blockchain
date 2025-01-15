# tests/service/test_mint_michielcoin.py

import os
import time
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
    Creates a chain_context using BlockFrost for Cardano TESTNET. 
    This fixture is shared (session-scoped) across all tests that require 
    blockchain access.

    Steps:
      1) Reads the BLOCKFROST_PROJECT_ID from the environment or uses a default.
      2) Calls get_chain_context with method="blockfrost" and TESTNET to 
         initialize a BlockFrostChainContext.
      3) Returns the context for UTxO queries, submitting transactions, etc.
    """
    project_id = os.getenv("BLOCKFROST_PROJECT_ID", "preprod06dzhzKlynuTInzvxHDH5cXbdHo524DE")
    return get_chain_context(method="blockfrost", project_id=project_id, network=Network.TESTNET)


@pytest.mark.integration
def test_mint_mit_token(chain_context_fixture, hotkey_skey_fixture):
    """
    Integration test: Mints 1,000,000 units of "MichielCOIN" (symbol "MIT") 
    using a policy script. The test follows a "legacy" logic approach.

    Steps:
      1) Retrieve payment and staking extended signing keys from the hotkey_skey_fixture.
      2) Construct main_address (the minter's address) and reuse it as the receiving address.
      3) Check that the address has at least one UTxO (enough funds) to cover minting fees.
      4) Generate or load the policy keys (policy.skey / policy.vkey). If they don't exist, create them.
      5) Build the policy script (ScriptAll containing a ScriptPubkey).
      6) Define a MultiAsset structure representing 1,000,000 "MichielCOIN" tokens.
      7) Add an output to the transaction carrying these tokens plus the required minimum lovelace.
      8) Use the payment address as input and sign the transaction with both payment_skey 
         and policy_signing_key.
      9) Submit the transaction to Blockfrost, verifying a non-empty result (tx ID).

    Notes:
      - This test will skip if the minter's address has no UTxOs.
      - The minted tokens are effectively credited to the same address (receive_address).
      - The policy.skey and policy.vkey are stored in the coldkey_dir for future reuse.
    """

    time.sleep(30)
    # 0) Get Payment/Stake extended signing keys from fixture
    (payment_skey, staking_skey) = hotkey_skey_fixture
    logging.info("[test_mint_michielcoin] Begin minting 'MichielCOIN' with hotkey as payment key.")

    # 1) Construct main_address and reuse it as the receiving address
    from_network = chain_context_fixture.network  # Typically TESTNET
    main_address = Address(
        payment_part=payment_skey.to_verification_key().hash(),
        staking_part=staking_skey.to_verification_key().hash(),
        network=from_network,
    )
    receive_address = main_address  # Reuse for simplicity
    logging.info(f"main_address   = {main_address}")
    logging.info(f"receive_address= {receive_address}")

    # 2) Check UTxOs; if no UTxOs, skip test
    utxos = chain_context_fixture.utxos(main_address)
    if not utxos:
        pytest.skip("main_address does not have any UTxOs => skip mint test")

    # 3) Create a transaction builder
    builder = TransactionBuilder(chain_context_fixture)

    # 4) Determine where to store the policy key files (policy.skey, policy.vkey)
    base_dir = os.getenv("HOTKEY_BASE_DIR", "moderntensor")
    coldkey_name = os.getenv("COLDKEY_NAME", "kickoff")
    coldkey_dir = os.path.join(base_dir, coldkey_name)
    os.makedirs(coldkey_dir, exist_ok=True)

    policy_skey_path = os.path.join(coldkey_dir, "policy.skey")
    policy_vkey_path = os.path.join(coldkey_dir, "policy.vkey")

    # 5) Generate a policy key pair if it doesn't already exist, and save to disk
    if not exists(policy_skey_path) and not exists(policy_vkey_path):
        key_pair = PaymentKeyPair.generate()
        key_pair.signing_key.save(policy_skey_path)
        key_pair.verification_key.save(policy_vkey_path)
        logging.info(f"[test_mint_michielcoin] Generated policy keys at {policy_skey_path} and {policy_vkey_path}")

    # 6) Load policy signing/verification keys and create the script
    policy_signing_key = PaymentSigningKey.load(policy_skey_path)
    policy_verification_key = PaymentVerificationKey.load(policy_vkey_path)
    pub_key_policy = ScriptPubkey(policy_verification_key.hash())
    policy = ScriptAll([pub_key_policy])  # Can extend with multiple scripts if needed

    policy_id = policy.hash()
    policy_id_hex = policy_id.payload.hex()
    logging.info(f"[test_mint_michielcoin] policy_id = {policy_id_hex}")

    # 7) Define a MultiAsset representing 1,000,000 "MichielCOIN" (symbol "MIT")
    asset_name = "MIT"
    asset_name_bytes = asset_name.encode("utf-8")
    token_asset_name = AssetName(asset_name_bytes)

    new_asset = Asset()
    new_asset[token_asset_name] = 1_000_000  # The quantity to mint

    multiasset = MultiAsset()
    multiasset[policy_id] = new_asset

    # Add the script to the builder and specify what to mint
    builder.native_scripts = [policy]
    builder.mint = multiasset

    # 8) Calculate the minimum ADA required for a UTxO containing this multi-asset
    #    Then add an output that contains (min_val, multiasset) for the receiving address
    min_val = min_lovelace(
        chain_context_fixture,
        output=TransactionOutput(receive_address, Value(0, multiasset))
    )
    builder.add_output(
        TransactionOutput(receive_address, Value(min_val, multiasset))
    )

    # 9) Add inputs from main_address to fund the transaction
    builder.add_input_address(main_address)

    # 10) Build and sign using both the payment signing key and the policy signing key
    signed_tx = builder.build_and_sign(
        signing_keys=[payment_skey, policy_signing_key],
        change_address=main_address
    )

    # 11) Submit the transaction to the network
    result = chain_context_fixture.submit_tx(signed_tx.to_cbor())

    logging.info(f"Number of inputs : {len(signed_tx.transaction_body.inputs)}")
    logging.info(f"Number of outputs: {len(signed_tx.transaction_body.outputs)}")
    logging.info(f"Fee             : {signed_tx.transaction_body.fee/1_000_000} ADA")
    logging.info(f"Transaction submitted => {result}")

    # 12) Validate that the result (tx ID) is non-empty, indicating success
    assert len(result) > 0, "Empty TX ID => mint transaction failed."

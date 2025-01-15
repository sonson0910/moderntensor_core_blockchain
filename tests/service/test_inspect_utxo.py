import os
import pytest
import logging
from pycardano import Address, Network
from sdk.service.context import get_chain_context

# Configure logging to write both to a file ("inspect_utxo.log") and console (StreamHandler)
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler("inspect_utxo.log", mode="w"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@pytest.fixture(scope="session")
def chain_context_fixture():
    """
    Creates a BlockFrost-based chain context for Cardano TESTNET
    to be shared across tests in this session.

    Steps:
      1) Reads BLOCKFROST_PROJECT_ID from the environment or uses a default.
      2) Calls get_chain_context(...) with method="blockfrost" 
         to initialize a BlockFrostChainContext.
      3) Returns this context so that tests can query UTxOs or submit transactions.

    Returns:
        A chain context object (BlockFrostChainContext) for Cardano TESTNET.
    """
    project_id = os.getenv("BLOCKFROST_PROJECT_ID", "preprod06dzhzKlynuTInzvxHDH5cXbdHo524DE")
    return get_chain_context(method="blockfrost", project_id=project_id, network=Network.TESTNET)

@pytest.mark.integration
def test_inspect_utxo(chain_context_fixture, hotkey_skey_fixture):
    """
    Integration test to inspect (log/print) all UTxOs at the address derived from 
    the provided hotkey_skey_fixture. This is primarily for observation/troubleshooting.

    Steps:
      1) Decode the hotkey_skey_fixture to retrieve payment and stake signing keys.
      2) Construct an Address object (TESTNET) from these signing keys.
      3) Query the chain context for the UTxOs at this address.
      4) Print detailed information about each UTxO (ADA and any multi-asset tokens).

    Args:
        chain_context_fixture: A BlockFrostChainContext fixture providing blockchain access.
        hotkey_skey_fixture: A fixture that returns a tuple (payment_xsk, stake_xsk) 
                            for deriving addresses.

    Notes:
      - The test simply prints UTxO details and marks itself as passed (assert True).
      - This test is useful for debugging or verifying token balances on TESTNET.
    """

    # Retrieve the payment and stake signing keys from fixture
    (payment_xsk, stake_xsk) = hotkey_skey_fixture
    from_network = chain_context_fixture.network  # Should be TESTNET

    # Convert the signing keys to verification keys
    pay_xvk = payment_xsk.to_verification_key()
    stake_xvk = stake_xsk.to_verification_key() if stake_xsk else None

    # Construct the address (TESTNET) from payment and optional stake verification keys
    from_address = Address(
        payment_part=pay_xvk.hash(),
        staking_part=stake_xvk.hash() if stake_xvk else None,
        network=from_network
    )

    print(f"Inspecting UTxOs for address: {from_address}")

    # Fetch all UTxOs for this address
    utxos = chain_context_fixture.utxos(from_address)
    if not utxos:
        print("No UTxOs found => Possibly zero tokens and zero ADA.")
        # Still pass the test, as no UTxOs is valid
        return

    # Loop through each UTxO and print details
    for idx, utxo in enumerate(utxos, start=1):
        print(f"\n--- UTxO #{idx} ---")
        print(f"Input (tx_in) : {utxo.input}")
        print(f"ADA coin      : {utxo.output.amount.coin}")

        # Check for multi-asset tokens in this UTxO
        ma = utxo.output.amount.multi_asset
        if ma:
            for policy_id, assets_map in ma.items():
                for aname, qty in assets_map.items():
                    # Convert policy_id and asset_name to readable formats
                    policy_id_hex = policy_id.payload.hex()
                    asset_name_str = aname.payload.decode("utf-8", errors="replace")

                    print(
                        f"  policy_id={policy_id_hex} "
                        f"asset_name={asset_name_str} "
                        f"quantity={qty}"
                    )
        else:
            print("No multi-asset tokens in this UTxO")

    # The test passes as long as no exceptions occur
    assert True

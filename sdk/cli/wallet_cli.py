# file: sdk/cli/wallet_cli.py

import click
from rich.tree import Tree
from rich.console import Console
from pycardano import (
    Network,
    PlutusV3Script,
    ScriptHash,
    Address,
    PaymentSigningKey,
    StakeSigningKey,
    plutus_script_hash,
    hash,
)
import cbor2
import os  # Import os for path operations
from sdk.keymanager.wallet_manager import WalletManager
from typing import Optional  # Import Optional
from sdk.service.register_key import register_key
from sdk.service.context import get_chain_context  # Needed for context
from sdk.config.settings import settings  # Load settings for defaults

# Import Datum definition
from sdk.metagraph.metagraph_datum import MinerDatum, STATUS_ACTIVE

# Import helper to get current slot
# from sdk.utils.cardano_utils import get_current_slot # Assume this exists
import traceback  # Import traceback for detailed error logging
import hashlib  # Import the standard hashlib library


@click.group()
def wallet_cli():
    """
    CLI command group for Wallet Management (Coldkey & Hotkey).
    """
    pass


# ------------------------------------------------------------------------------
# 1) CREATE COLDKEY
# ------------------------------------------------------------------------------
@wallet_cli.command("create-coldkey")
@click.option("--name", required=True, help="Coldkey name.")
@click.option(
    "--password",
    prompt=True,
    hide_input=True,
    confirmation_prompt=True,
    help="mnemonic encryption password.",
)
@click.option(
    "--base-dir", default="moderntensor", help="The base directory stores coldkeys."
)
@click.option(
    "--network",
    default="testnet",
    type=click.Choice(["testnet", "mainnet"]),
    help="Select Cardano network.",
)
def create_coldkey_cmd(name, password, base_dir, network):
    """
    Generate coldkey (mnemonic), encrypt and save to folder.
    """
    net = Network.TESTNET if network == "testnet" else Network.MAINNET
    wm = WalletManager(network=net, base_dir=base_dir)
    wm.create_coldkey(name, password)
    click.echo(f"[OK] Coldkey '{name}' has been created in directory '{base_dir}'.")


# ------------------------------------------------------------------------------
# 2) LOAD COLDKEY
# ------------------------------------------------------------------------------
@wallet_cli.command("load-coldkey")
@click.option("--name", required=True, help="Coldkey name.")
@click.option("--password", prompt=True, hide_input=True, help="Password.")
@click.option("--base-dir", default="moderntensor", help="Base directory.")
@click.option(
    "--network",
    default="testnet",
    type=click.Choice(["testnet", "mainnet"]),
    help="Network.",
)
def load_coldkey_cmd(name, password, base_dir, network):
    """
    Load coldkey into memory.
    """
    net = Network.TESTNET if network == "testnet" else Network.MAINNET
    wm = WalletManager(network=net, base_dir=base_dir)
    wm.load_coldkey(name, password)
    click.echo(f"[OK] Coldkey '{name}' has been loaded from '{base_dir}'.")


# ------------------------------------------------------------------------------
# 3) GENERATE HOTKEY
# ------------------------------------------------------------------------------
@wallet_cli.command("generate-hotkey")
@click.option("--coldkey", required=True, help="Coldkey name.")
@click.option("--hotkey-name", required=True, help="Hotkey name.")
@click.option("--base-dir", default="moderntensor", help="Base directory.")
@click.option(
    "--network",
    default="testnet",
    type=click.Choice(["testnet", "mainnet"]),
    help="Network.",
)
def generate_hotkey_cmd(coldkey, hotkey_name, base_dir, network):
    """
    Create hotkey (public key) and save it to hotkeys.json
    """
    net = Network.TESTNET if network == "testnet" else Network.MAINNET
    wm = WalletManager(network=net, base_dir=base_dir)

    password = click.prompt("Enter the coldkey password", hide_input=True)
    wm.load_coldkey(coldkey, password)
    encrypted_data = wm.generate_hotkey(coldkey, hotkey_name)
    click.echo(f"[OK] Hotkey '{hotkey_name}' created => {encrypted_data}")


# ------------------------------------------------------------------------------
# 4) IMPORT HOTKEY
# ------------------------------------------------------------------------------
@wallet_cli.command("import-hotkey")
@click.option("--coldkey", required=True, help="Coldkey name.")
@click.option("--encrypted-hotkey", required=True, help="Encrypted hotkey string.")
@click.option("--hotkey-name", required=True, help="Hotkey name.")
@click.option(
    "--overwrite",
    is_flag=True,
    default=False,
    help="Overwrite the old hotkey if the name is the same.",
)
@click.option("--base-dir", default="moderntensor", help="Base directory.")
@click.option(
    "--network",
    default="testnet",
    type=click.Choice(["testnet", "mainnet"]),
    help="Network.",
)
def import_hotkey_cmd(
    coldkey, encrypted_hotkey, hotkey_name, overwrite, base_dir, network
):
    """
    Import an encrypted hotkey from a string.
    """
    net = Network.TESTNET if network == "testnet" else Network.MAINNET
    wm = WalletManager(network=net, base_dir=base_dir)

    password = click.prompt("Enter the coldkey password", hide_input=True)
    wm.load_coldkey(coldkey, password)

    wm.import_hotkey(coldkey, encrypted_hotkey, hotkey_name, overwrite=overwrite)
    click.echo(f"[OK] Hotkey '{hotkey_name}' has been imported.")


# ------------------------------------------------------------------------------
# 5) LIST KEY
# ------------------------------------------------------------------------------


@wallet_cli.command(name="list")
def list_coldkeys():
    """
    List all Coldkeys and their Hotkeys in tree structure (using Rich).
    """
    manager = WalletManager()
    wallets = manager.load_all_wallets()

    console = Console()

    if not wallets:
        console.print("[bold red]No coldkeys found.[/bold red]")
        return

    root_tree = Tree("[bold cyan]Wallets[/bold cyan]")

    for w in wallets:
        # Tạo node con cho Coldkey
        coldkey_node = root_tree.add(
            f"[bold yellow]Coldkey[/bold yellow] [magenta]{w['name']}[/magenta]"
        )

        # hotkeys
        if w.get("hotkeys"):
            for hk in w["hotkeys"]:
                hk_addr = hk["address"] or "unknown"
                coldkey_node.add(f"Hotkey [green]{hk['name']}[/green] (addr={hk_addr})")

    console.print(root_tree)


# ------------------------------------------------------------------------------
# 6) REGISTER HOTKEY (via Smart Contract Update)
# ------------------------------------------------------------------------------
@wallet_cli.command("register-hotkey")
@click.option("--coldkey", required=True, help="Coldkey name controlling the hotkey.")
@click.option("--hotkey", required=True, help="Hotkey name to register (used as UID).")
@click.option(
    "--password",
    prompt=True,
    hide_input=True,
    help="Password for the coldkey.",
)
@click.option(
    "--subnet-uid", required=True, type=int, help="UID of the subnet to register on."
)
@click.option(
    "--initial-stake",
    required=True,
    type=int,
    help="Initial stake amount (in Lovelace).",
)
@click.option(
    "--api-endpoint",
    required=True,  # Now required for MinerDatum
    help="Full API endpoint URL for this hotkey (e.g., http://<ip>:<port>).",
)
@click.option(
    "--script-path",
    required=True,
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    help="Path to the Plutus V3 script file (.plutus).",
)
@click.option(
    "--base-dir",
    default=lambda: settings.HOTKEY_BASE_DIR,
    help="Base directory for keys.",
)
@click.option(
    "--network",
    default=lambda: (
        str(settings.CARDANO_NETWORK).lower() if settings.CARDANO_NETWORK else "testnet"
    ),  # Get from settings safely
    type=click.Choice(["testnet", "mainnet"]),
    help="Select Cardano network.",
)
@click.option(
    "--contract-address",
    default=lambda: settings.TEST_CONTRACT_ADDRESS,
    help="Contract script address.",
)
@click.option(
    "--yes",
    is_flag=True,
    help="Skip confirmation prompt before submitting transaction.",
)
def register_hotkey_cmd(
    coldkey,
    hotkey,
    password,
    subnet_uid,
    initial_stake,
    api_endpoint,
    script_path,
    base_dir,
    network,
    contract_address,
    yes,
):
    """
    Register a hotkey as a Miner by updating the smart contract datum.
    Finds the UTxO with the lowest incentive and updates its datum.
    """
    click.echo(f"Attempting to register hotkey '{hotkey}' as a Miner...")

    try:
        net = Network.TESTNET if network == "testnet" else Network.MAINNET
        wm = WalletManager(network=net, base_dir=base_dir)

        # --- Load Keys ---
        click.echo(f"Loading coldkey '{coldkey}'...")
        coldkey_data = wm.load_coldkey(coldkey, password)
        if (
            not coldkey_data
            or not coldkey_data.get("payment_skey")
            or not coldkey_data.get("payment_address")
        ):
            click.echo(
                f"[Error] Failed to load coldkey '{coldkey}' or its signing key/address."
            )
            return
        cold_payment_skey: PaymentSigningKey = coldkey_data["payment_skey"]
        cold_address: Address = coldkey_data["payment_address"]
        # Stake key might be needed depending on the contract
        cold_stake_skey: Optional[StakeSigningKey] = coldkey_data.get("stake_skey")
        click.echo(f"Coldkey '{coldkey}' loaded (Address: {cold_address}).")

        click.echo(f"Verifying hotkey '{hotkey}'...")
        hotkey_info = wm.get_hotkey_info(coldkey, hotkey)
        if not hotkey_info or not hotkey_info.get("address"):
            click.echo(
                f"[Error] Failed to find hotkey '{hotkey}' info. Generate it first?"
            )
            return
        hot_address_str = hotkey_info["address"]
        click.echo(f"Hotkey '{hotkey}' found (Address: {hot_address_str}).")

        # --- Load Script and Prepare Datum ---
        click.echo(f"Loading Plutus script from: {script_path}")
        try:
            with open(script_path, "r") as f:
                script_hex = f.read()
            script = PlutusV3Script(bytes.fromhex(script_hex))
            script_hash = plutus_script_hash(script)
            click.echo(f"Script loaded. Script Hash: {script_hash.to_primitive()}")
        except FileNotFoundError:
            click.echo(f"[Error] Script file not found: {script_path}")
            return
        except ValueError as e:  # Catch hex decoding errors
            click.echo(f"[Error] Invalid script file content (not valid hex?): {e}")
            return
        except Exception as e:
            click.echo(f"[Error] Failed to load or parse Plutus script: {e}")
            return

        click.echo("Preparing new Miner Datum...")
        # Get current slot (Need a utility function for this)
        # current_slot = get_current_slot(context) # Assuming context is needed here
        current_slot = 0  # Placeholder - GET ACTUAL SLOT!
        if current_slot == 0:
            click.echo(
                "[Warning] Could not get current slot, using 0 for registration/update slot."
            )

        # Convert addresses/UIDs/endpoint to bytes for Datum
        try:
            hotkey_uid_bytes = hotkey.encode("utf-8")
            api_endpoint_bytes = api_endpoint.encode("utf-8")
            # Use hash.blake2b_224 for wallet address hash
            wallet_addr_hash_bytes = hashlib.blake2b(
                bytes(cold_address), digest_size=28
            ).digest()
            # Performance history hash - initialize as empty? Needs clarification.
            perf_history_hash_bytes = b""
        except Exception as e:
            click.echo(f"[Error] Failed to encode data for Datum: {e}")
            return

        # Create the new datum instance
        # Note: Defaulting performance/trust/rewards to 0. Needs review.
        new_datum = MinerDatum(
            uid=hotkey_uid_bytes,
            subnet_uid=subnet_uid,
            stake=initial_stake,  # Lovelace
            scaled_last_performance=0,
            scaled_trust_score=0,
            accumulated_rewards=0,
            last_update_slot=current_slot,  # Use current slot
            performance_history_hash=perf_history_hash_bytes,  # Placeholder
            wallet_addr_hash=wallet_addr_hash_bytes,  # Placeholder hash
            status=STATUS_ACTIVE,  # Register as active
            registration_slot=current_slot,  # Use current slot
            api_endpoint=api_endpoint_bytes,
        )
        click.echo("New Miner Datum prepared:")
        click.echo(f"  UID: {hotkey}")
        click.echo(f"  Subnet UID: {subnet_uid}")
        click.echo(f"  Stake: {initial_stake}")
        click.echo(f"  API Endpoint: {api_endpoint}")
        # Print other relevant datum fields if needed

        # --- Blockchain Interaction ---
        click.echo("Initializing Cardano context...")
        context = get_chain_context(method="blockfrost")  # Assumes blockfrost
        if not context:
            click.echo("[Error] Could not initialize Cardano chain context.")
            return

        # Use contract address from parameter or settings and convert to ScriptHash
        try:
            contract_sh = (
                ScriptHash.from_primitive(contract_address)
                if contract_address
                else None
            )
        except ValueError:
            click.echo(
                f"[Error] Invalid contract address format: {contract_address}. Must be a valid ScriptHash hex string."
            )
            return

        if not contract_sh:
            # Try getting default from settings if not provided via CLI
            try:
                default_addr_str = settings.TEST_CONTRACT_ADDRESS
                contract_sh = (
                    ScriptHash.from_primitive(default_addr_str)
                    if default_addr_str
                    else None
                )
            except Exception as e:
                click.echo(
                    f"[Error] Could not load default contract address from settings: {e}"
                )
                contract_sh = None  # Ensure it's None if loading fails

        if not contract_sh:
            click.echo(
                "[Error] Contract address (ScriptHash) is required, either via --contract-address or settings."
            )
            return
        click.echo(f"Using Contract Script Hash: {contract_sh.to_primitive()}")

        # Confirm before proceeding
        if not yes:
            click.confirm(
                f"\nRegister hotkey '{hotkey}' as Miner on subnet {subnet_uid} "
                f"by updating UTxO at {contract_sh}?",
                abort=True,
            )

        click.echo("Submitting registration transaction via register_key service...")
        try:
            tx_id = register_key(
                payment_xsk=cold_payment_skey.to_extended_signing_key(),  # Convert if needed
                stake_xsk=(
                    cold_stake_skey.to_extended_signing_key()
                    if cold_stake_skey
                    else None
                ),
                script_hash=script_hash,  # This is already ScriptHash type
                new_datum=new_datum,
                script=script,
                context=context,
                network=net,
                contract_address=contract_sh,  # Pass the ScriptHash object
                # redeemer=None # Use default Redeemer(0)
            )

            if tx_id:
                click.echo(f"[OK] Miner registration transaction submitted.")
                click.echo(f"Transaction ID: {tx_id}")
                click.echo("Please wait for blockchain confirmation.")
            else:
                # The function should raise an error if submission fails
                click.echo(
                    "[Error] Failed to submit registration transaction (No TxID returned)."
                )

        except FileNotFoundError as e:
            click.echo(
                f"[Error] Key file not found: {e}. Have you created the coldkey/hotkey?"
            )
        except ValueError as e:
            # Catch errors from register_key (e.g., no UTxO found)
            click.echo(f"[Error] Registration failed: {e}")
        except Exception as e:
            # Catch potential errors during tx building/signing/submission
            click.echo(f"[Error] An unexpected error occurred during registration: {e}")
            traceback.print_exc()  # Print full traceback for debugging

    except FileNotFoundError as e:
        # Catch errors from initial file/key loading if they occurred outside the inner try
        click.echo(f"[Error] Initial file/key loading error: {e}")
    except ValueError as e:
        # Catch other value errors (e.g., parsing arguments, address conversion)
        click.echo(f"[Error] Invalid value encountered during setup: {e}")
    except Exception as e:
        # Catch any other unexpected error not caught by the inner block
        click.echo(
            f"[Error] An overall unexpected error occurred in register_hotkey_cmd: {e}"
        )
        traceback.print_exc()  # Print details for debugging the outer failure

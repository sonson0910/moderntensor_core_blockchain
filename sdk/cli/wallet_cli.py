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

# Import function to read validator details
from sdk.smartcontract.validator import read_validator

# Import Datum definition
from sdk.metagraph.metagraph_datum import MinerDatum, STATUS_ACTIVE

# Import helper to get current slot
# from sdk.utils.cardano_utils import get_current_slot # Assume this exists
# Import hash_data for empty history hash
from sdk.metagraph.hash.hash_datum import hash_data
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
    console = Console()
    console.print(
        f":heavy_check_mark: [bold green]Coldkey '{name}' created in directory '{base_dir}'.[/bold green]"
    )


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
    console = Console()
    console.print(
        f":key: [bold blue]Coldkey '{name}' loaded from '{base_dir}'.[/bold blue]"
    )


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
    console = Console()
    console.print(
        f":sparkles: [bold green]Hotkey '{hotkey_name}' created.[/bold green]"
    )


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
    console = Console()
    console.print(
        f":inbox_tray: [bold green]Hotkey '{hotkey_name}' imported.[/bold green]"
    )


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
            f":closed_lock_with_key: [bold yellow]Coldkey[/bold yellow] [magenta]{w['name']}[/magenta]"
        )

        # hotkeys
        if w.get("hotkeys"):
            for hk in w["hotkeys"]:
                hk_addr = hk["address"] or "unknown"
                # Use a different key icon for hotkey
                coldkey_node.add(
                    f":key: Hotkey [green]{hk['name']}[/green] (addr=[dim]{hk_addr}[/dim])"
                )

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
    base_dir,
    network,
    yes,
):
    """
    Register a hotkey as a Miner by updating the smart contract datum.
    Finds the UTxO with the lowest incentive and updates its datum.
    """
    console = Console()
    console.print(
        f":rocket: Attempting to register hotkey [cyan]'{hotkey}'[/cyan] as a Miner..."
    )

    try:
        net = Network.TESTNET if network == "testnet" else Network.MAINNET
        wm = WalletManager(network=net, base_dir=base_dir)

        # --- Load Keys ---
        console.print(f"⏳ Loading coldkey [magenta]'{coldkey}'[/magenta]...")
        coldkey_data = wm.load_coldkey(coldkey, password)
        if (
            not coldkey_data
            or not coldkey_data.get("payment_skey")
            or not coldkey_data.get("payment_address")
        ):
            console.print(
                f"[bold red]Error:[/bold red] Failed to load coldkey '{coldkey}' or its signing key/address."
            )
            return
        cold_payment_skey: PaymentSigningKey = coldkey_data["payment_skey"]
        cold_address: Address = coldkey_data["payment_address"]
        cold_stake_skey: Optional[StakeSigningKey] = coldkey_data.get("stake_skey")
        console.print(
            f":key: Coldkey '{coldkey}' loaded (Address: [dim]{cold_address}[/dim])."
        )

        console.print(f"⏳ Verifying hotkey [cyan]'{hotkey}'[/cyan]...")
        hotkey_info = wm.get_hotkey_info(coldkey, hotkey)
        if not hotkey_info or not hotkey_info.get("address"):
            console.print(
                f"[bold red]Error:[/bold red] Failed to find hotkey '{hotkey}' info. Generate it first?"
            )
            return
        hot_address_str = hotkey_info["address"]
        console.print(
            f":key: Hotkey '{hotkey}' found (Address: [dim]{hot_address_str}[/dim])."
        )

        # --- Blockchain Interaction (Initialize Context FIRST) ---
        console.print("⏳ Initializing Cardano context...")
        context = get_chain_context(method="blockfrost")  # Assumes blockfrost
        if not context:
            console.print(
                "[bold red]Error:[/bold red] Could not initialize Cardano chain context."
            )
            return
        console.print(
            f":globe_with_meridians: Cardano context initialized (Network: {net})."
        )

        # --- Load Script --- (Moved after context init)
        console.print("⏳ Loading validator script details...")
        try:
            validator_details = read_validator()
            if (
                not validator_details
                or "script" not in validator_details
                or "script_hash" not in validator_details
            ):
                console.print(
                    "[bold red]Error:[/bold red] Failed to load valid script details (script or hash missing) using read_validator."
                )
                return
            script: PlutusV3Script = validator_details["script"]
            script_hash: ScriptHash = validator_details["script_hash"]
            contract_address_obj = Address(payment_part=script_hash, network=net)
            console.print(
                f":scroll: Script details loaded. Script Hash: [yellow]{script_hash.to_primitive()}[/yellow]"
            )
            console.print(
                f":link: Derived Contract Address: [blue]{contract_address_obj}[/blue]"
            )
        except Exception as e:
            console.print(
                f"[bold red]Error:[/bold red] Failed to load validator script details: {e}"
            )
            console.print_exception(show_locals=True)
            return

        # --- Prepare Datum --- (Moved after context init)
        console.print("⏳ Preparing new Miner Datum...")
        current_slot: Optional[int] = None
        try:
            current_slot = context.last_block_slot
            if current_slot is None:
                console.print(
                    "[yellow]Warning:[/yellow] context.last_block_slot returned None."
                )
                current_slot = 0
            console.print(f":clock1: Using current slot: {current_slot}")
        except Exception as slot_err:
            console.print(
                f"[yellow]Warning:[/yellow] Could not get current slot from context: {slot_err}. Using 0."
            )
            current_slot = 0

        # Convert addresses/UIDs/endpoint to bytes for Datum
        try:
            hotkey_uid_bytes = hotkey.encode("utf-8")
            api_endpoint_bytes = api_endpoint.encode("utf-8")
            wallet_addr_hash_bytes = hashlib.blake2b(
                bytes(cold_address), digest_size=28
            ).digest()
            perf_history_hash_bytes = hash_data([])
        except Exception as e:
            console.print(
                f"[bold red]Error:[/bold red] Failed to encode data for Datum: {e}"
            )
            return

        # Create the new datum instance
        new_datum = MinerDatum(
            uid=hotkey_uid_bytes,
            subnet_uid=subnet_uid,
            stake=initial_stake,
            scaled_last_performance=0,
            scaled_trust_score=0,
            accumulated_rewards=0,
            last_update_slot=current_slot,
            performance_history_hash=perf_history_hash_bytes,
            wallet_addr_hash=wallet_addr_hash_bytes,
            status=STATUS_ACTIVE,
            registration_slot=current_slot,
            api_endpoint=api_endpoint_bytes,
        )
        console.print(":clipboard: New Miner Datum prepared:")
        click.echo(f"  UID: {hotkey}")
        click.echo(f"  Subnet UID: {subnet_uid}")
        click.echo(f"  Stake: {initial_stake}")
        click.echo(f"  API Endpoint: {api_endpoint}")

        # Confirm before proceeding
        if not yes:
            click.confirm(
                f"\n❓ Register hotkey [cyan]'{hotkey}'[/cyan] as Miner on subnet [yellow]{subnet_uid}[/yellow] "
                f"by updating UTxO at contract address [blue]{contract_address_obj}[/blue]?",
                abort=True,
            )

        console.print(
            ":arrow_up: Submitting registration transaction via [bold]register_key[/bold] service..."
        )
        try:
            tx_id = register_key(
                payment_xsk=cold_payment_skey.to_extended_signing_key(),
                stake_xsk=(
                    cold_stake_skey.to_extended_signing_key()
                    if cold_stake_skey
                    else None
                ),
                script_hash=script_hash,
                new_datum=new_datum,
                script=script,
                context=context,
                network=net,
                contract_address=contract_address_obj,
            )

            if tx_id:
                console.print(
                    f":heavy_check_mark: [bold green]Miner registration transaction submitted.[/bold green]"
                )
                console.print(f"Transaction ID: [bold blue]{tx_id}[/bold blue]")
                console.print(
                    ":hourglass_flowing_sand: Please wait for blockchain confirmation."
                )
            else:
                console.print(
                    "[bold red]Error:[/bold red] Failed to submit registration transaction (No TxID returned)."
                )

        except FileNotFoundError as e:
            console.print(
                f"[bold red]Error:[/bold red] Key file not found: {e}. Have you created the coldkey/hotkey?"
            )
        except ValueError as e:
            console.print(f"[bold red]Error:[/bold red] Registration failed: {e}")
        except Exception as e:
            console.print(
                f"[bold red]Error:[/bold red] An unexpected error occurred during registration: {e}"
            )
            console.print_exception(show_locals=True)

    except FileNotFoundError as e:
        console.print(
            f"[bold red]Error:[/bold red] Initial file/key loading error: {e}"
        )
    except ValueError as e:
        console.print(
            f"[bold red]Error:[/bold red] Invalid value encountered during setup: {e}"
        )
    except Exception as e:
        console.print(
            f"[bold red]Error:[/bold red] An overall unexpected error occurred in register_hotkey_cmd: {e}"
        )
        console.print_exception(show_locals=True)

# sdk/cli/metagraph_cli.py
import click
import asyncio
import json
import os
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from moderntensor_aptos.mt_core.account import Account
from moderntensor_aptos.mt_core.async_client import ModernTensorCoreClient
from moderntensor_aptos.mt_core.config.settings import settings, logger
from moderntensor_aptos.mt_core.core_client.contract_client import (
    register_miner,
    register_validator,
    get_all_miners,
    get_all_validators,
)


# ------------------------------------------------------------------------------
# METAGRAPH COMMAND GROUP
# ------------------------------------------------------------------------------
@click.group()
def metagraph_cli():
    """
    🔄 Commands for working with the ModernTensor metagraph on Core blockchain. 🔄
    """
    pass


# Helper function to load account from disk
def _load_account(account_name: str, password: str, base_dir: str) -> Optional[Account]:
    console = Console()
    try:
        account_path = os.path.join(base_dir, f"{account_name}.json")
        if not os.path.exists(account_path):
            console.print(
                f"[bold red]Error:[/bold red] Account file {account_path} not found"
            )
            return None

        # In a real implementation, you would decrypt the account file with the password
        # For now, we'll just load the account from disk
        with open(account_path, "r") as f:
            account_data = json.load(f)
            # This is simplified - in a real implementation, you'd need to decrypt private keys
            private_key_hex = account_data["private_key"]
            account = Account.from_key(private_key_hex)
            console.print(f"✅ Account loaded: [blue]{account.address}[/blue]")
            return account
    except Exception as e:
        console.print(f"[bold red]Error loading account:[/bold red] {e}")
        logger.exception(f"Error loading account {account_name}")
        return None


# Helper function to get Core Client
def _get_client(network: str) -> ModernTensorCoreClient:
    if network == "mainnet":
        return ModernTensorCoreClient("https://rpc.coredao.org")
    elif network == "testnet":
        return ModernTensorCoreClient("https://rpc.test.btcs.network")
    elif network == "devnet":
        return ModernTensorCoreClient("https://rpc.dev.btcs.network")
    else:
        # Default to testnet
        return ModernTensorCoreClient("https://rpc.test.btcs.network")


# ------------------------------------------------------------------------------
# REGISTER MINER COMMAND
# ------------------------------------------------------------------------------
@metagraph_cli.command("register-miner")
@click.option("--account", required=True, help="Account name to register as miner.")
@click.option("--password", prompt=True, hide_input=True, help="Account password.")
@click.option("--subnet-uid", required=True, type=int, help="Subnet ID to join.")
@click.option("--api-endpoint", required=True, help="API endpoint URL for the miner.")
@click.option(
    "--stake-amount",
    required=True,
    type=int,
    help="Amount to stake in octas (1 APT = 10^8 octas).",
)
@click.option(
    "--contract-address",
    default=lambda: settings.APTOS_CONTRACT_ADDRESS,
    help="ModernTensor contract address.",
)
@click.option(
    "--network",
    default=lambda: settings.APTOS_NETWORK,
    type=click.Choice(["mainnet", "testnet", "devnet", "local"]),
    help="Select Aptos network.",
)
@click.option(
    "--base-dir",
    default=lambda: settings.ACCOUNT_BASE_DIR,
    help="Base directory where account files reside.",
)
@click.option("--yes", is_flag=True, help="Skip confirmation prompt.")
def register_miner_cmd(
    account,
    password,
    subnet_uid,
    api_endpoint,
    stake_amount,
    contract_address,
    network,
    base_dir,
    yes,
):
    """
    📝 Register a new miner in the metagraph.
    """
    console = Console()
    account_obj = _load_account(account, password, base_dir)
    if not account_obj:
        return

    client = _get_client(network)

    # Display information about the registration
    console.print(
        f"❓ Registering account [blue]{account_obj.address}[/blue] as a miner"
    )
    console.print(f"  Subnet: [cyan]{subnet_uid}[/cyan]")
    console.print(f"  API Endpoint: [green]{api_endpoint}[/green]")
    console.print(
        f"  Stake Amount: [yellow]{stake_amount:,}[/yellow] octas ({stake_amount / 100_000_000:.8f} APT)"
    )

    if not yes:
        click.confirm("This will submit a transaction. Proceed?", abort=True)

    console.print("⏳ Submitting miner registration transaction...")
    try:
        # Create ModernTensorClient and register miner
        moderntensor_client = ModernTensorCoreClient(
            account_obj, client, contract_address
        )

        # Generate a random UID - in a real implementation, this would be derived from the account
        import secrets

        uid = secrets.token_bytes(32)

        # Register the miner
        tx_hash = asyncio.run(
            moderntensor_client.register_miner(
                uid=uid,
                subnet_uid=subnet_uid,
                stake_amount=stake_amount,
                api_endpoint=api_endpoint,
            )
        )

        if tx_hash:
            console.print(
                f":heavy_check_mark: [bold green]Miner registration transaction submitted![/bold green]"
            )
            console.print(f"  Transaction hash: [bold blue]{tx_hash}[/bold blue]")
            console.print(f"  Miner UID: [magenta]{uid.hex()}[/magenta]")
        else:
            console.print(
                ":cross_mark: [bold red]Registration failed. Check logs for details.[/bold red]"
            )
    except Exception as e:
        console.print(
            f":cross_mark: [bold red]Error during miner registration:[/bold red] {e}"
        )
        logger.exception("Miner registration command failed")


# ------------------------------------------------------------------------------
# REGISTER VALIDATOR COMMAND
# ------------------------------------------------------------------------------
@metagraph_cli.command("register-validator")
@click.option("--account", required=True, help="Account name to register as validator.")
@click.option("--password", prompt=True, hide_input=True, help="Account password.")
@click.option("--subnet-uid", required=True, type=int, help="Subnet ID to join.")
@click.option(
    "--api-endpoint", required=True, help="API endpoint URL for the validator."
)
@click.option(
    "--stake-amount",
    required=True,
    type=int,
    help="Amount to stake in octas (1 APT = 10^8 octas).",
)
@click.option(
    "--contract-address",
    default=lambda: settings.APTOS_CONTRACT_ADDRESS,
    help="ModernTensor contract address.",
)
@click.option(
    "--network",
    default=lambda: settings.APTOS_NETWORK,
    type=click.Choice(["mainnet", "testnet", "devnet", "local"]),
    help="Select Aptos network.",
)
@click.option(
    "--base-dir",
    default=lambda: settings.ACCOUNT_BASE_DIR,
    help="Base directory where account files reside.",
)
@click.option("--yes", is_flag=True, help="Skip confirmation prompt.")
def register_validator_cmd(
    account,
    password,
    subnet_uid,
    api_endpoint,
    stake_amount,
    contract_address,
    network,
    base_dir,
    yes,
):
    """
    📝 Register a new validator in the metagraph.
    """
    console = Console()
    account_obj = _load_account(account, password, base_dir)
    if not account_obj:
        return

    client = _get_client(network)

    # Display information about the registration
    console.print(
        f"❓ Registering account [blue]{account_obj.address}[/blue] as a validator"
    )
    console.print(f"  Subnet: [cyan]{subnet_uid}[/cyan]")
    console.print(f"  API Endpoint: [green]{api_endpoint}[/green]")
    console.print(
        f"  Stake Amount: [yellow]{stake_amount:,}[/yellow] octas ({stake_amount / 100_000_000:.8f} APT)"
    )

    if not yes:
        click.confirm("This will submit a transaction. Proceed?", abort=True)

    console.print("⏳ Submitting validator registration transaction...")
    try:
        # Create ModernTensorClient and register validator
        moderntensor_client = ModernTensorCoreClient(
            account_obj, client, contract_address
        )

        # Generate a random UID - in a real implementation, this would be derived from the account
        import secrets

        uid = secrets.token_bytes(32)

        # Register the validator
        tx_hash = asyncio.run(
            moderntensor_client.register_validator(
                uid=uid,
                subnet_uid=subnet_uid,
                stake_amount=stake_amount,
                api_endpoint=api_endpoint,
            )
        )

        if tx_hash:
            console.print(
                f":heavy_check_mark: [bold green]Validator registration transaction submitted![/bold green]"
            )
            console.print(f"  Transaction hash: [bold blue]{tx_hash}[/bold blue]")
            console.print(f"  Validator UID: [magenta]{uid.hex()}[/magenta]")
        else:
            console.print(
                ":cross_mark: [bold red]Registration failed. Check logs for details.[/bold red]"
            )
    except Exception as e:
        console.print(
            f":cross_mark: [bold red]Error during validator registration:[/bold red] {e}"
        )
        logger.exception("Validator registration command failed")


# ------------------------------------------------------------------------------
# LIST MINERS COMMAND
# ------------------------------------------------------------------------------
@metagraph_cli.command("list-miners")
@click.option("--subnet-uid", type=int, help="Filter miners by subnet ID (optional).")
@click.option(
    "--contract-address",
    default=lambda: settings.APTOS_CONTRACT_ADDRESS,
    help="ModernTensor contract address.",
)
@click.option(
    "--network",
    default=lambda: settings.APTOS_NETWORK,
    type=click.Choice(["mainnet", "testnet", "devnet", "local"]),
    help="Select Aptos network.",
)
def list_miners_cmd(subnet_uid, contract_address, network):
    """
    📋 List all miners in the metagraph.
    """
    console = Console()
    client = _get_client(network)

    # Display query information
    if subnet_uid is not None:
        console.print(f"⏳ Fetching miners for subnet [cyan]{subnet_uid}[/cyan]...")
    else:
        console.print("⏳ Fetching all miners...")

    try:
        # Get all miners
        miners = asyncio.run(
            get_all_miners(
                client=client, contract_address=contract_address, subnet_uid=subnet_uid
            )
        )

        if not miners:
            console.print("[bold yellow]No miners found.[/bold yellow]")
            return

        # Display miners in a table
        table = Table(
            title=f"Miners"
            + (f" in Subnet {subnet_uid}" if subnet_uid is not None else ""),
            border_style="blue",
        )
        table.add_column("UID", style="magenta")
        table.add_column("Address", style="blue")
        table.add_column("API Endpoint", style="green")
        table.add_column("Stake", style="yellow")
        table.add_column("Trust Score", style="cyan")
        table.add_column("Status", style="bright_white")

        for miner in miners:
            status_str = (
                "Active"
                if miner.status == 1
                else "Inactive" if miner.status == 0 else "Jailed"
            )
            status_style = (
                "green"
                if miner.status == 1
                else "yellow" if miner.status == 0 else "red"
            )

            table.add_row(
                miner.uid[:8] + "...",  # Truncate UID for display
                miner.address,
                miner.api_endpoint or "N/A",
                f"{miner.stake:.8f} APT",
                f"{miner.trust_score:.6f}",
                f"[{status_style}]{status_str}[/{status_style}]",
            )

        console.print(table)
        console.print(f"Total miners: [bold cyan]{len(miners)}[/bold cyan]")

    except Exception as e:
        console.print(f"[bold red]Error listing miners:[/bold red] {e}")
        logger.exception("List miners command failed")


# ------------------------------------------------------------------------------
# LIST VALIDATORS COMMAND
# ------------------------------------------------------------------------------
@metagraph_cli.command("list-validators")
@click.option(
    "--subnet-uid", type=int, help="Filter validators by subnet ID (optional)."
)
@click.option(
    "--contract-address",
    default=lambda: settings.APTOS_CONTRACT_ADDRESS,
    help="ModernTensor contract address.",
)
@click.option(
    "--network",
    default=lambda: settings.APTOS_NETWORK,
    type=click.Choice(["mainnet", "testnet", "devnet", "local"]),
    help="Select Aptos network.",
)
def list_validators_cmd(subnet_uid, contract_address, network):
    """
    📋 List all validators in the metagraph.
    """
    console = Console()
    client = _get_client(network)

    # Display query information
    if subnet_uid is not None:
        console.print(f"⏳ Fetching validators for subnet [cyan]{subnet_uid}[/cyan]...")
    else:
        console.print("⏳ Fetching all validators...")

    try:
        # Get all validators
        validators = asyncio.run(
            get_all_validators(
                client=client, contract_address=contract_address, subnet_uid=subnet_uid
            )
        )

        if not validators:
            console.print("[bold yellow]No validators found.[/bold yellow]")
            return

        # Display validators in a table
        table = Table(
            title=f"Validators"
            + (f" in Subnet {subnet_uid}" if subnet_uid is not None else ""),
            border_style="blue",
        )
        table.add_column("UID", style="magenta")
        table.add_column("Address", style="blue")
        table.add_column("API Endpoint", style="green")
        table.add_column("Stake", style="yellow")
        table.add_column("Trust Score", style="cyan")
        table.add_column("Performance", style="bright_yellow")
        table.add_column("Status", style="bright_white")

        for validator in validators:
            status_str = (
                "Active"
                if validator.status == 1
                else "Inactive" if validator.status == 0 else "Jailed"
            )
            status_style = (
                "green"
                if validator.status == 1
                else "yellow" if validator.status == 0 else "red"
            )

            table.add_row(
                validator.uid[:8] + "...",  # Truncate UID for display
                validator.address,
                validator.api_endpoint or "N/A",
                f"{validator.stake:.8f} APT",
                f"{validator.trust_score:.6f}",
                f"{validator.last_performance:.6f}",
                f"[{status_style}]{status_str}[/{status_style}]",
            )

        console.print(table)
        console.print(f"Total validators: [bold cyan]{len(validators)}[/bold cyan]")

    except Exception as e:
        console.print(f"[bold red]Error listing validators:[/bold red] {e}")
        logger.exception("List validators command failed")

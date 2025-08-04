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
from moderntensor_aptos.mt_core.async_client import CoreAsyncClient
from moderntensor_aptos.mt_core.config.settings import settings, logger
from moderntensor_aptos.mt_core.core_client.contract_client import (
    ModernTensorCoreClient,
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
def _get_client(network: str) -> CoreAsyncClient:
    if network == "mainnet":
        return CoreAsyncClient("https://rpc.coredao.org")
    elif network == "testnet":
        return CoreAsyncClient("https://rpc.test.btcs.network")
    elif network == "devnet":
        return CoreAsyncClient("https://rpc.test.btcs.network")  # Use testnet for dev
    else:
        # Default to testnet
        return CoreAsyncClient("https://rpc.test.btcs.network")


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
    default=lambda: settings.CORE_CONTRACT_ADDRESS,
    help="ModernTensor contract address.",
)
@click.option(
    "--network",
    default=lambda: settings.CORE_NETWORK,
    type=click.Choice(["mainnet", "testnet", "devnet", "local"]),
    help="Select Core network.",
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
        from web3 import Web3

        w3 = Web3(Web3.HTTPProvider(client.rpc_url))
        moderntensor_client = ModernTensorCoreClient(
            w3=w3, contract_address=contract_address, account=account_obj
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
    default=lambda: settings.CORE_CONTRACT_ADDRESS,
    help="ModernTensor contract address.",
)
@click.option(
    "--network",
    default=lambda: settings.CORE_NETWORK,
    type=click.Choice(["mainnet", "testnet", "devnet", "local"]),
    help="Select Core network.",
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
        from web3 import Web3

        w3 = Web3(Web3.HTTPProvider(client.rpc_url))
        moderntensor_client = ModernTensorCoreClient(
            w3=w3, contract_address=contract_address, account=account_obj
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
    default=lambda: settings.CORE_CONTRACT_ADDRESS,
    help="ModernTensor contract address.",
)
@click.option(
    "--network",
    default=lambda: settings.CORE_NETWORK,
    type=click.Choice(["mainnet", "testnet", "devnet", "local"]),
    help="Select Core network.",
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
        # Get all miners using ModernTensorCoreClient
        from web3 import Web3

        w3 = Web3(Web3.HTTPProvider(client.rpc_url))
        moderntensor_client = ModernTensorCoreClient(
            w3=w3, contract_address=contract_address
        )
        console.print(f"🔍 Connecting to contract: {contract_address}")
        console.print(f"🔍 Using RPC: {client.rpc_url}")

        miners = moderntensor_client.get_all_miners()
        console.print(f"🔍 Found {len(miners) if miners else 0} miners")

        if miners:
            console.print(f"🔍 Miner addresses: {miners}")

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
        table.add_column("Stake (CORE + BTC)", style="yellow")
        table.add_column("Trust Score", style="cyan")
        table.add_column("Owner", style="white")
        table.add_column("Status", style="bright_white")

        for miner_address in miners:
            try:
                # Get detailed miner info
                miner_info = moderntensor_client.get_miner_info(miner_address)
                console.print(f"🔍 Miner info: {miner_info}")

                # Basic display for now
                table.add_row(
                    miner_address[:8] + "...",  # Truncate address for display
                    miner_address,
                    "N/A",  # API endpoint
                    "N/A",  # Stake
                    "N/A",  # Trust score
                    "N/A",  # Owner
                    "[green]Active[/green]",
                )
            except Exception as e:
                console.print(f"⚠️ Error getting miner info for {miner_address}: {e}")
                # Still add to table with basic info
                table.add_row(
                    miner_address[:8] + "...",
                    miner_address,
                    "N/A",
                    "N/A",
                    "N/A",
                    "N/A",
                    "[yellow]Unknown[/yellow]",
                )

        console.print(table)

        # Enhanced network statistics with Bitcoin staking
        total_miners = len(miners)
        total_core_stake = 0  # TODO: Calculate from miner info
        total_bitcoin_stake = 0  # TODO: Calculate from miner info
        miners_with_btc = 0  # TODO: Calculate from miner info

        console.print(f"\n📊 [bold blue]Miners Summary[/bold blue]")
        console.print(f"Total miners: [bold cyan]{total_miners}[/bold cyan]")
        console.print(f"Total CORE stake: [yellow]{total_core_stake:.4f} CORE[/yellow]")
        console.print(
            f"Total Bitcoin stake: [orange1]{total_bitcoin_stake/100000000:.8f} BTC[/orange1]"
        )
        console.print(
            f"Miners with Bitcoin: [green]{miners_with_btc}/{total_miners}[/green] ({miners_with_btc/total_miners*100:.1f}%)"
            if total_miners > 0
            else "Miners with Bitcoin: 0/0"
        )

    except Exception as e:
        console.print(f"[bold red]Error listing miners:[/bold red] {e}")
        console.print(f"[bold red]Error type:[/bold red] {type(e).__name__}")
        import traceback

        console.print(f"[bold red]Traceback:[/bold red] {traceback.format_exc()}")
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
    default=lambda: settings.CORE_CONTRACT_ADDRESS,
    help="ModernTensor contract address.",
)
@click.option(
    "--network",
    default=lambda: settings.CORE_NETWORK,
    type=click.Choice(["mainnet", "testnet", "devnet", "local"]),
    help="Select Core network.",
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
        # Get all validators using ModernTensorCoreClient
        from web3 import Web3

        w3 = Web3(Web3.HTTPProvider(client.rpc_url))
        moderntensor_client = ModernTensorCoreClient(
            w3=w3, contract_address=contract_address
        )
        validators = moderntensor_client.get_all_validators()

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
        table.add_column("Stake (CORE + BTC)", style="yellow")
        table.add_column("Trust Score", style="cyan")
        table.add_column("Performance", style="bright_yellow")
        table.add_column("Owner", style="white")
        table.add_column("Status", style="bright_white")

        for validator_address in validators:
            try:
                # Get detailed validator info
                validator_info = moderntensor_client.get_validator_info(
                    validator_address
                )
                console.print(f"🔍 Validator info: {validator_info}")

                # Basic display for now
                table.add_row(
                    validator_address[:8] + "...",  # Truncate address for display
                    validator_address,
                    "N/A",  # API endpoint
                    "N/A",  # Stake
                    "N/A",  # Trust score
                    "N/A",  # Performance
                    "N/A",  # Owner
                    "[green]Active[/green]",
                )
            except Exception as e:
                console.print(
                    f"⚠️ Error getting validator info for {validator_address}: {e}"
                )
                # Still add to table with basic info
                table.add_row(
                    validator_address[:8] + "...",
                    validator_address,
                    "N/A",
                    "N/A",
                    "N/A",
                    "N/A",
                    "N/A",
                    "[yellow]Unknown[/yellow]",
                )

        console.print(table)

        # Enhanced network statistics with Bitcoin staking
        total_validators = len(validators)
        total_core_stake = 0  # TODO: Calculate from validator info
        total_bitcoin_stake = 0  # TODO: Calculate from validator info
        validators_with_btc = 0  # TODO: Calculate from validator info

        console.print(f"\n📊 [bold blue]Validators Summary[/bold blue]")
        console.print(f"Total validators: [bold cyan]{total_validators}[/bold cyan]")
        console.print(f"Total CORE stake: [yellow]{total_core_stake:.4f} CORE[/yellow]")
        console.print(
            f"Total Bitcoin stake: [orange1]{total_bitcoin_stake/100000000:.8f} BTC[/orange1]"
        )
        console.print(
            f"Validators with Bitcoin: [green]{validators_with_btc}/{total_validators}[/green] ({validators_with_btc/total_validators*100:.1f}%)"
            if total_validators > 0
            else "Validators with Bitcoin: 0/0"
        )

    except Exception as e:
        console.print(f"[bold red]Error listing validators:[/bold red] {e}")
        logger.exception("List validators command failed")


if __name__ == "__main__":
    metagraph_cli()

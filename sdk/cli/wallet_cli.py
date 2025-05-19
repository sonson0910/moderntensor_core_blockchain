# file: sdk/cli/wallet_cli.py
"""
Command-line interface for Aptos wallet management.

This module provides CLI commands to create, manage, and use Aptos wallets.
It allows users to generate new accounts, view addresses, and perform wallet-related tasks.
"""

import os
import click
import json
from rich.console import Console
from rich.table import Table
import asyncio
from typing import Dict, Any

from aptos_sdk.account import Account, AccountAddress
from aptos_sdk.bcs import Serializer
from aptos_sdk.transactions import EntryFunction, TransactionArgument
from aptos_sdk.client import RestClient

from sdk.keymanager.wallet_manager import WalletManager
from sdk.keymanager.decryption_utils import decode_hotkey_skey
from sdk.config.settings import settings, logger

# Network selection parameters
NETWORK_CHOICES = ["mainnet", "testnet", "devnet", "local"]
DEFAULT_NETWORK = settings.APTOS_NETWORK

# from sdk.utils.cardano_utils import get_current_slot # Replace with Aptos utility if needed


@click.group()
def aptosctl():
    """
    🗳️ Aptos Control Tool - A command line interface for managing Aptos accounts and operations. 🗳️
    """
    pass


@aptosctl.group()
def wallet():
    """
    🏦 Wallet management commands.
    """
    pass


@wallet.command("create")
@click.option(
    "--name", required=True, help="Name for the new wallet (coldkey)."
)
@click.option(
    "--password",
    prompt=True,
    hide_input=True,
    confirmation_prompt=True,
    help="Password to encrypt wallet mnemonic.",
)
@click.option(
    "--network",
    type=click.Choice(NETWORK_CHOICES),
    default=lambda: settings.APTOS_NETWORK,
    help="Select Aptos network.",
)
@click.option(
    "--show-mnemonic",
    is_flag=True,
    default=False,
    help="Display the generated mnemonic phrase (sensitive information).",
)
@click.option(
    "--base-dir",
    default=lambda: settings.HOTKEY_BASE_DIR,
    show_default=True,
    help="Base directory to store coldkey.",
)
def create_cmd(name, password, network, show_mnemonic, base_dir):
    """
    🏦 Create a new wallet (coldkey).

    This command creates a new coldkey (seed phrase wallet) with the given name
    and encrypted with the provided password.
    """
    console = Console()
    console.print("⏳ Creating wallet, please wait...")

    try:
        wm = WalletManager(network=network, base_dir=base_dir)
        mnemonic = wm.create_coldkey(name, password)
        
        if mnemonic:
            console.print(
                f":white_check_mark: [bold green]Success![/bold green] Wallet created with name: [cyan]{name}[/cyan]"
            )
            console.print("📁 Wallet files stored in the following location:")
            console.print(f"  [dim]{os.path.join(base_dir, name)}[/dim]")
            
            if show_mnemonic:
                console.print("\n[bold yellow]⚠️ BACKUP THIS MNEMONIC PHRASE! ⚠️[/bold yellow]")
                console.print(
                    "[yellow]Store it safely offline. Anyone with this mnemonic can access your funds.[/yellow]"
                )
                console.print(f"\n[bold]{mnemonic}[/bold]\n")
        else:
            console.print(
                f"[bold red]Error:[/bold red] Wallet creation failed. Please try again."
            )
    except FileExistsError:
        console.print(
            f"[bold red]Error:[/bold red] A wallet with name '{name}' already exists."
        )
        console.print(
            "Use a different name or delete the existing wallet directory first."
        )
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        logger.exception(e)


@wallet.command("add-hotkey")
@click.option(
    "--coldkey",
    required=True,
    help="Name of the parent coldkey (wallet).",
)
@click.option(
    "--hotkey",
    required=True,
    help="Name for the new hotkey.",
)
@click.option(
    "--password",
    prompt=True,
    hide_input=True,
    help="Password for the coldkey.",
)
@click.option(
    "--network",
    type=click.Choice(NETWORK_CHOICES),
    default=lambda: settings.APTOS_NETWORK,
    help="Select the Aptos network (testnet/mainnet).",
)
@click.option(
    "--base-dir",
    default=lambda: settings.HOTKEY_BASE_DIR,
    show_default=True,
    help="Base directory where wallet files are stored.",
)
def add_hotkey_cmd(coldkey, hotkey, password, network, base_dir):
    """
    🔑 Add a new hotkey to an existing coldkey.

    This command generates a new hotkey under the specified coldkey.
    The hotkey can be used for staking and other operations.
    """
    console = Console()
    console.print("⏳ Generating new hotkey...")

    try:
        wm = WalletManager(network=network, base_dir=base_dir)
        wm.add_hotkey(coldkey, hotkey, password)
        
        console.print(
            f":white_check_mark: [bold green]Success![/bold green] Hotkey '{hotkey}' added to coldkey '{coldkey}'"
        )
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        logger.exception(e)


@wallet.command("info")
@click.option(
    "--name", required=True, help="Name of the wallet to display information for."
)
@click.option(
    "--base-dir",
    default=lambda: settings.HOTKEY_BASE_DIR,
    show_default=True,
    help="Base directory where wallet files are stored.",
)
def info_cmd(name, base_dir):
    """
    ℹ️ Display information about a wallet.

    This command shows the address and other details for the specified wallet.
    """
    console = Console()
    
    try:
        wm = WalletManager(base_dir=base_dir)
        info = wm.get_wallet_info(name)
        
        table = Table(title=f"Wallet Information: {name}")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")
        
        for key, value in info.items():
            table.add_row(key, str(value))
        
        console.print(table)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        logger.exception(e)


@aptosctl.group()
def validator():
    """
    ⚡ Validator management commands.
    """
    pass


@validator.command("register")
@click.option(
    "--name", required=True, help="Name for the new validator."
)
@click.option(
    "--coldkey", required=True, help="Name of the coldkey to use."
)
@click.option(
    "--password",
    prompt=True,
    hide_input=True,
    help="Password for the coldkey.",
)
@click.option(
    "--network",
    type=click.Choice(NETWORK_CHOICES),
    default=lambda: settings.APTOS_NETWORK,
    help="Select Aptos network.",
)
@click.option(
    "--base-dir",
    default=lambda: settings.HOTKEY_BASE_DIR,
    show_default=True,
    help="Base directory where wallet files are stored.",
)
def register_validator_cmd(name, coldkey, password, network, base_dir):
    """
    ⚡ Register a new validator.

    This command registers a new validator using the specified coldkey.
    """
    console = Console()
    console.print("⏳ Registering validator...")

    try:
        wm = WalletManager(network=network, base_dir=base_dir)
        wm.register_validator(name, coldkey, password)
        
        console.print(
            f":white_check_mark: [bold green]Success![/bold green] Validator '{name}' registered successfully"
        )
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        logger.exception(e)


@aptosctl.group()
def subnet():
    """
    🌐 Subnet management commands.
    """
    pass


@subnet.command("create")
@click.option(
    "--name", required=True, help="Name for the new subnet."
)
@click.option(
    "--validator", required=True, help="Name of the validator to use."
)
@click.option(
    "--password",
    prompt=True,
    hide_input=True,
    help="Password for the validator's coldkey.",
)
@click.option(
    "--network",
    type=click.Choice(NETWORK_CHOICES),
    default=lambda: settings.APTOS_NETWORK,
    help="Select Aptos network.",
)
@click.option(
    "--base-dir",
    default=lambda: settings.HOTKEY_BASE_DIR,
    show_default=True,
    help="Base directory where wallet files are stored.",
)
def create_subnet_cmd(name, validator, password, network, base_dir):
    """
    🌐 Create a new subnet.

    This command creates a new subnet using the specified validator.
    """
    console = Console()
    console.print("⏳ Creating subnet...")

    try:
        wm = WalletManager(network=network, base_dir=base_dir)
        wm.create_subnet(name, validator, password)
        
        console.print(
            f":white_check_mark: [bold green]Success![/bold green] Subnet '{name}' created successfully"
        )
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        logger.exception(e)


if __name__ == '__main__':
    aptosctl()

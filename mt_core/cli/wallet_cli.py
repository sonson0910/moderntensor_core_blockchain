# file: sdk/cli/wallet_cli.py
"""
Command-line interface for Core blockchain wallet management.

This module provides CLI commands to create, manage, and use Core blockchain wallets.
It allows users to generate new accounts, view addresses, and perform wallet-related tasks.
"""

import os
import click
import json
from rich.console import Console
from rich.table import Table
import asyncio
from typing import Dict, Any

from moderntensor_aptos.mt_core.account import Account
from moderntensor_aptos.mt_core.core_client.contract_client import (
    ModernTensorCoreClient,
)
from moderntensor_aptos.mt_core.keymanager.wallet_manager import WalletManager
from moderntensor_aptos.mt_core.keymanager.decryption_utils import decode_hotkey_account
from moderntensor_aptos.mt_core.config.settings import settings, logger

# Network selection parameters
NETWORK_CHOICES = ["mainnet", "testnet", "devnet", "local"]
DEFAULT_NETWORK = getattr(settings, "CORE_NETWORK", "testnet")


@click.group()
def wallet_cli():
    """
    🔥 CYBERPUNK WALLET MATRIX - Neural quantum wallet management system ⚡
    """
    pass


@wallet_cli.command("create")
@click.option("--name", required=True, help="Name for the new wallet (coldkey).")
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
    default=DEFAULT_NETWORK,
    help="Select Core blockchain network.",
)
@click.option(
    "--show-mnemonic",
    is_flag=True,
    default=False,
    help="Display the generated mnemonic phrase (sensitive information).",
)
@click.option(
    "--base-dir",
    default=lambda: getattr(settings, "HOTKEY_BASE_DIR", "./wallets"),
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
                console.print(
                    "\n[bold yellow]⚠️ BACKUP THIS MNEMONIC PHRASE! ⚠️[/bold yellow]"
                )
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


@wallet_cli.command("add-hotkey")
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
    default=DEFAULT_NETWORK,
    help="Select the Core blockchain network.",
)
@click.option(
    "--base-dir",
    default=lambda: getattr(settings, "HOTKEY_BASE_DIR", "./wallets"),
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


@wallet_cli.command("info")
@click.option(
    "--name", required=True, help="Name of the wallet to display information for."
)
@click.option(
    "--base-dir",
    default=lambda: getattr(settings, "HOTKEY_BASE_DIR", "./wallets"),
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


# Alias for backward compatibility
wallet = wallet_cli

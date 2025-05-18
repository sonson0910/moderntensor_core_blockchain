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

# Replace pycardano imports with Aptos SDK
from aptos_sdk.account import Account, AccountAddress
from aptos_sdk.bcs import Serializer
from aptos_sdk.transactions import EntryFunction, TransactionArgument

from sdk.keymanager.wallet_manager import WalletManager
from sdk.keymanager.decryption_utils import decode_hotkey_skey
from sdk.config.settings import settings, logger

# Network selection parameters
NETWORK_CHOICES = ["mainnet", "testnet", "devnet", "local"]
DEFAULT_NETWORK = settings.APTOS_NETWORK

# from sdk.utils.cardano_utils import get_current_slot # Replace with Aptos utility if needed


@click.group()
def wallet_cli():
    """
    🗳️ Commands for Aptos account creation and management. 🗳️
    """
    pass


@wallet_cli.command("create")
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


@wallet_cli.command("restore")
@click.option(
    "--name", required=True, help="Name for the restored wallet."
)
@click.option(
    "--mnemonic",
    prompt="Enter your mnemonic phrase (24 words separated by spaces)",
    help="The mnemonic phrase to restore.",
)
@click.option(
    "--password",
    prompt=True,
    hide_input=True,
    confirmation_prompt=True,
    help="New password to encrypt the restored wallet.",
)
@click.option(
    "--network",
    type=click.Choice(NETWORK_CHOICES),
    default=lambda: settings.APTOS_NETWORK,
    help="Select Aptos network.",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Overwrite existing wallet if name exists.",
)
@click.option(
    "--base-dir",
    default=lambda: settings.HOTKEY_BASE_DIR,
    show_default=True,
    help="Base directory to store coldkey.",
)
def restore_cmd(name, mnemonic, password, network, force, base_dir):
    """
    🔄 Restore a wallet from a mnemonic phrase.

    This command restores a wallet using the provided 24-word mnemonic phrase.
    """
    console = Console()
    console.print("⏳ Validating mnemonic and restoring wallet...")
    
    try:
        wm = WalletManager(network=network, base_dir=base_dir)
        wm.restore_coldkey_from_mnemonic(name, mnemonic, password, force)
        
        console.print(
            f":white_check_mark: [bold green]Success![/bold green] Wallet restored with name: [cyan]{name}[/cyan]"
        )
        console.print("📁 Wallet files stored in the following location:")
        console.print(f"  [dim]{os.path.join(base_dir, name)}[/dim]")
    except FileExistsError:
        console.print(
            f"[bold red]Error:[/bold red] A wallet with name '{name}' already exists.\n"
            "Use --force to overwrite."
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
    default=lambda: settings.APTOS_NETWORK,
    help="Select the Aptos network (testnet/mainnet).",
)
@click.option(
    "--base-dir",
    default=lambda: settings.HOTKEY_BASE_DIR,
    help="Base directory where wallet files are stored.",
)
def add_hotkey_cmd(coldkey, hotkey, password, network, base_dir):
    """
    🔑 Create a new hotkey under an existing coldkey (wallet).
    
    Hotkeys are used for daily operations while coldkeys remain secure.
    """
    console = Console()
    console.print("⏳ Generating hotkey, please wait...")
    
    try:
        wm = WalletManager(network=network, base_dir=base_dir)
        encrypted_hotkey = wm.generate_hotkey(coldkey, hotkey)
        
        if encrypted_hotkey:
            console.print(
                f":white_check_mark: [bold green]Success![/bold green] Hotkey [cyan]{hotkey}[/cyan] created under coldkey [cyan]{coldkey}[/cyan]"
            )
            # Console additional info about the hotkey
            hotkey_info = wm.get_hotkey_info(coldkey, hotkey)
            if hotkey_info and "address" in hotkey_info:
                console.print(f"📍 Address: [yellow]{hotkey_info['address']}[/yellow]")
        else:
            console.print(
                f"[bold red]Error:[/bold red] Failed to generate hotkey. Please check coldkey name and password."
            )
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        logger.exception(e)


@wallet_cli.command("list")
@click.option(
    "--base-dir",
    default=lambda: settings.HOTKEY_BASE_DIR,
    help="Base directory where wallet files are stored.",
)
def list_wallets_cmd(base_dir):
    """
    📋 List all wallets (coldkeys) and their hotkeys.
    
    Shows all available wallets and their associated hotkeys in a table.
    """
    console = Console()
    console.print("⏳ Scanning for wallets...")
    
    try:
        wm = WalletManager(base_dir=base_dir)
        wallets = wm.load_all_wallets()
        
        if not wallets:
            console.print(f"[yellow]No wallets found in {base_dir}[/yellow]")
            return
        
        console.print(f"📂 Found [bold cyan]{len(wallets)}[/bold cyan] wallets:")
        
        # Create a table for displaying wallets and hotkeys
        table = Table(title="Wallets and Hotkeys", box=None)
        table.add_column("Wallet (coldkey)", style="cyan")
        table.add_column("Hotkey", style="green")
        table.add_column("Address", style="yellow")
        
        for wallet in wallets:
            coldkey_name = wallet["name"]
            hotkeys = wallet["hotkeys"]
            
            if not hotkeys:
                table.add_row(coldkey_name, "[dim italic]No hotkeys[/dim italic]", "")
            else:
                for i, hotkey in enumerate(hotkeys):
                    hotkey_name = hotkey["name"]
                    address = hotkey.get("address", "N/A")
                    
                    # For first hotkey, include coldkey name
                    if i == 0:
                        table.add_row(coldkey_name, hotkey_name, address)
                    else:
                        table.add_row("", hotkey_name, address)
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        logger.exception(e)


@wallet_cli.command("export-hotkey")
@click.option(
    "--coldkey",
    required=True,
    help="Name of the parent coldkey (wallet).",
)
@click.option(
    "--hotkey",
    required=True,
    help="Name of the hotkey to export.",
)
@click.option(
    "--password",
    prompt=True,
    hide_input=True,
    help="Password for the coldkey.",
)
@click.option(
    "--file",
    help="Output file to save the exported hotkey (omit for console output).",
)
@click.option(
    "--base-dir",
    default=lambda: settings.HOTKEY_BASE_DIR,
    help="Base directory where wallet files are stored.",
)
@click.option(
    "--network",
    type=click.Choice(NETWORK_CHOICES),
    default=lambda: settings.APTOS_NETWORK,
    help="Select Aptos network.",
)
def export_hotkey_cmd(coldkey, hotkey, password, file, base_dir, network):
    """
    📤 Export a hotkey for backup or transfer.
    
    Exports a hotkey's encrypted data string, which can be imported on another device.
    """
    console = Console()
    console.print("⏳ Retrieving hotkey data...")
    
    try:
        wm = WalletManager(network=network, base_dir=base_dir)
        key_info = wm.get_hotkey_info(coldkey, hotkey)
        
        if not key_info:
            console.print(
                f"[bold red]Error:[/bold red] Hotkey '{hotkey}' not found under coldkey '{coldkey}'."
            )
            return
        
        if "encrypted_data" not in key_info:
            console.print(
                f"[bold red]Error:[/bold red] Encrypted data not found for hotkey '{hotkey}'."
            )
            return
        
        encrypted_data = key_info["encrypted_data"]
        
        if file:
            # Save to file
            with open(file, "w") as f:
                f.write(encrypted_data)
            console.print(f":white_check_mark: [green]Hotkey exported to file:[/green] {file}")
        else:
            # Display in console
            console.print("[bold yellow]⚠️ COPY THIS ENCRYPTED HOTKEY STRING: ⚠️[/bold yellow]")
            console.print(f"\n{encrypted_data}\n")
            console.print("[dim]Note: This string contains encrypted key data. Store it securely.[/dim]")
    
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        logger.exception(e)


@wallet_cli.command("faucet")
@click.option(
    "--address", required=True, help="Address to fund with test tokens."
)
@click.option(
    "--amount", default=1000, type=int, help="Amount of test tokens to request (1 APT = 10^8 octas)."
)
@click.option(
    "--network",
    type=click.Choice(["testnet", "devnet"]),
    default="testnet",
    help="Select testnet or devnet (not available for mainnet).",
)
@click.option("--yes", is_flag=True, help="Skip confirmation prompt.")
def faucet_cmd(address, amount, network, yes):
    """
    💧 Request test tokens from the Aptos faucet (testnet/devnet only).
    
    This command requests test tokens from the Aptos faucet for testing purposes.
    Only works on testnet and devnet.
    """
    console = Console()
    
    if network == "testnet":
        faucet_url = "https://faucet.testnet.aptoslabs.com"
    else:  # devnet
        faucet_url = "https://faucet.devnet.aptoslabs.com"
    
    amount_in_octas = amount * 100_000_000  # Convert APT to octas
    
    # Format address if needed
    if not address.startswith("0x"):
        address = f"0x{address}"
    
    if not yes:
        console.print(f"🪄 Requesting {amount} APT from the {network} faucet")
        console.print(f"  Address: [blue]{address}[/blue]")
        console.print(f"  Faucet: [green]{faucet_url}[/green]")
        console.print("\n⚠️  [yellow]Note: This is for testing only. Tokens have no real value.[/yellow]")
        if not click.confirm("Do you want to proceed?"):
            console.print("Operation cancelled.")
            return
    
    async def send_faucet_request():
        import aiohttp
        
        console.print("⏳ Sending request to faucet...")
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "address": address, 
                    "amount": amount_in_octas
                }
                
                async with session.post(f"{faucet_url}/fund", json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        txn_hash = result.get("txn_hash", "Unknown")
                        console.print("✅ [bold green]Success![/bold green] Funds should arrive shortly.")
                        console.print(f"  Transaction: [blue]{txn_hash}[/blue]")
                        console.print(f"  Explorer: https://explorer.aptoslabs.com/txn/{txn_hash}?network={network}")
                    else:
                        error_text = await response.text()
                        console.print(f"❌ [bold red]Error:[/bold red] {response.status} - {error_text}")
                        
        except Exception as e:
            console.print(f"❌ [bold red]Error:[/bold red] {e}")
    
    asyncio.run(send_faucet_request())

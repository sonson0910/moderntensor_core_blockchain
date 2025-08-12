#!/usr/bin/env python3
"""
Demo script for ModernTensor Aptos HD Wallet System
Demonstrates the complete workflow of HD wallet management
"""

import os
import sys
import tempfile
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Add the project root to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from mt_core.keymanager.hd_wallet_manager import CoreHDWalletManager

console = Console()


def demo_hd_wallet_system():
    """
    Comprehensive demo of HD wallet system features
    """

    console.print(
        Panel.fit(
            "[bold cyan]🚀 ModernTensor Aptos HD Wallet System Demo[/bold cyan]\n\n"
            "[yellow]This demo shows how to use the ModernTensor-style HD wallet system for Core[/yellow]",
            title="HD Wallet Demo",
            border_style="cyan",
        )
    )

    # Use temporary directory for demo
    with tempfile.TemporaryDirectory() as tmpdir:
        console.print(f"\n[dim]Using temporary directory: {tmpdir}[/dim]")

        # Initialize wallet manager
        wm = CoreHDWalletManager(base_dir=tmpdir)

        # === Step 1: Create HD Wallet ===
        console.print("\n[bold blue]📦 Step 1: Creating HD Wallet[/bold blue]")

        wallet_name = "organization_wallet"
        password = "secure_password_123"
        mnemonic = wm.create_wallet(wallet_name, password, 24)

        console.print(f"[green]✅ Created wallet: {wallet_name}[/green]")
        console.print(f"[dim]Mnemonic words: {len(mnemonic.split())}[/dim]")

        # === Step 2: Load Wallet ===
        console.print("\n[bold blue]🔓 Step 2: Loading Wallet[/bold blue]")

        success = wm.load_wallet(wallet_name, password)
        console.print(f"[green]✅ Wallet loaded: {success}[/green]")

        # === Step 3: Create Coldkeys (Master Keys) ===
        console.print(
            "\n[bold blue]❄️ Step 3: Creating Coldkeys (Master Keys)[/bold blue]"
        )

        # Create multiple coldkeys for different purposes
        coldkeys = [
            ("treasury", "Treasury management key"),
            ("validator", "Validator operations key"),
            ("development", "Development team key"),
        ]

        coldkey_info = {}
        for name, description in coldkeys:
            info = wm.create_coldkey(wallet_name, name)
            coldkey_info[name] = info
            console.print(f"[green]✅ Created coldkey: {name}[/green]")
            console.print(f"[dim]  Address: {info['address']}[/dim]")
            console.print(f"[dim]  Path: {info['derivation_path']}[/dim]")

        # === Step 4: Create Hotkeys (Derived Keys) ===
        console.print(
            "\n[bold blue]🔥 Step 4: Creating Hotkeys (Derived Keys)[/bold blue]"
        )

        # Create hotkeys for validator coldkey
        hotkeys = [
            ("validator_1", "Main validator hotkey"),
            ("validator_2", "Backup validator hotkey"),
            ("validator_3", "Test validator hotkey"),
        ]

        hotkey_info = {}
        for name, description in hotkeys:
            info = wm.create_hotkey(wallet_name, "validator", name)
            hotkey_info[name] = info
            console.print(f"[green]✅ Created hotkey: {name}[/green]")
            console.print(f"[dim]  Address: {info['address']}[/dim]")
            console.print(f"[dim]  Path: {info['derivation_path']}[/dim]")

        # === Step 5: Get Account Objects ===
        console.print("\n[bold blue]🔑 Step 5: Getting Account Objects[/bold blue]")

        # Get coldkey account
        coldkey_account = wm.get_account(wallet_name, "validator")
        console.print(
            f"[green]✅ Coldkey account: {str(coldkey_account.address())}[/green]"
        )

        # Get hotkey account
        hotkey_account = wm.get_account(wallet_name, "validator", "validator_1")
        console.print(
            f"[green]✅ Hotkey account: {str(hotkey_account.address())}[/green]"
        )

        # === Step 6: Export Private Keys ===
        console.print("\n[bold blue]🔐 Step 6: Exporting Private Keys[/bold blue]")

        # Export coldkey private key
        coldkey_private = wm.export_private_key(wallet_name, "validator")
        console.print(
            f"[green]✅ Coldkey private key: {coldkey_private[:20]}...[/green]"
        )

        # Export hotkey private key
        hotkey_private = wm.export_private_key(wallet_name, "validator", "validator_1")
        console.print(f"[green]✅ Hotkey private key: {hotkey_private[:20]}...[/green]")

        # === Step 7: Display Wallet Information ===
        console.print("\n[bold blue]📊 Step 7: Wallet Information[/bold blue]")

        wm.display_wallet_info(wallet_name)

        # === Step 8: Import External Account ===
        console.print("\n[bold blue]📥 Step 8: Importing External Account[/bold blue]")

        # Create a sample private key for demo
        import secrets

        sample_private_key = secrets.token_bytes(32).hex()

        imported_info = wm.import_account_by_private_key(
            wallet_name, sample_private_key, "imported_account"
        )
        console.print(f"[green]✅ Imported account: {imported_info['address']}[/green]")

        # === Step 9: Restore Wallet Demo ===
        console.print("\n[bold blue]🔄 Step 9: Wallet Restoration Demo[/bold blue]")

        # Create a new wallet to restore from mnemonic
        restored_wallet = "restored_wallet"
        success = wm.restore_wallet(restored_wallet, mnemonic, password)
        console.print(f"[green]✅ Wallet restored: {success}[/green]")

        # Load the restored wallet
        success = wm.load_wallet(restored_wallet, password)
        console.print(f"[green]✅ Restored wallet loaded: {success}[/green]")

        # === Step 10: List All Wallets ===
        console.print("\n[bold blue]📋 Step 10: Listing All Wallets[/bold blue]")

        wallets = wm.list_wallets()
        table = Table(title="Available Wallets")
        table.add_column("Wallet Name", style="cyan")
        table.add_column("Status", style="green")

        for wallet in wallets:
            status = (
                "✅ Available"
                if wallet in [wallet_name, restored_wallet]
                else "❌ Not loaded"
            )
            table.add_row(wallet, status)

        console.print(table)

        # === Final Summary ===
        console.print("\n" + "=" * 60)
        console.print(
            Panel.fit(
                "[bold green]🎉 HD Wallet Demo Completed Successfully![/bold green]\n\n"
                "[yellow]Key Features Demonstrated:[/yellow]\n"
                "• BIP44 HD wallet creation with 24-word mnemonic\n"
                "• Encrypted mnemonic storage with password protection\n"
                "• Hierarchical coldkey/hotkey structure\n"
                "• Multiple account derivation paths\n"
                "• Private key export functionality\n"
                "• External account import\n"
                "• Wallet restoration from mnemonic\n"
                "• Comprehensive wallet management\n\n"
                "[bold cyan]Ready for production use with ModernTensor Aptos![/bold cyan]",
                title="Demo Complete",
                border_style="green",
            )
        )

        console.print(f"\n[dim]Demo files were created in: {tmpdir}[/dim]")
        console.print(f"[dim]In production, set HOTKEY_BASE_DIR in settings[/dim]")


if __name__ == "__main__":
    demo_hd_wallet_system()

#!/usr/bin/env python3
"""
HD Wallet Demo for ModernTensor Aptos
Demonstrates Bittensor-like coldkey/hotkey system using HD wallets

This script shows:
1. Creating an HD wallet with mnemonic
2. Creating coldkeys (master accounts)
3. Creating hotkeys (derived accounts)
4. Using the accounts for transactions
5. Exporting/importing keys
"""

import os
import sys
import asyncio
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mt_aptos.keymanager.hd_wallet_manager import AptosHDWalletManager
from mt_aptos.config.settings import settings
from rich.console import Console
from rich.panel import Panel

console = Console()


def setup_demo_environment():
    """Setup demo environment with temporary directory"""
    demo_dir = Path("./demo_wallets")
    demo_dir.mkdir(exist_ok=True)
    
    # Override settings for demo
    settings.HOTKEY_BASE_DIR = str(demo_dir)
    
    return demo_dir


def demo_basic_usage():
    """Demonstrate basic HD wallet usage"""
    console.print(Panel.fit(
        "[bold cyan]🏦 HD Wallet Demo - Basic Usage[/bold cyan]\n\n"
        "This demo shows how to create and use HD wallets\n"
        "similar to Bittensor's coldkey/hotkey system",
        title="ModernTensor HD Wallet Demo",
        border_style="cyan"
    ))
    
    # Initialize HD wallet manager
    wallet_manager = AptosHDWalletManager()
    
    # Step 1: Create a new HD wallet
    console.print("\n[bold yellow]Step 1: Creating HD Wallet[/bold yellow]")
    wallet_name = "demo_wallet"
    password = "demo_password_123"  # In real usage, use secure password
    
    try:
        mnemonic = wallet_manager.create_wallet(wallet_name, password, words_count=24)
        console.print(f"[green]✅ Wallet '{wallet_name}' created successfully[/green]")
        console.print(f"[dim]Mnemonic (first 4 words): {' '.join(mnemonic.split()[:4])}...[/dim]")
    except Exception as e:
        console.print(f"[red]❌ Error creating wallet: {e}[/red]")
        return
    
    # Step 2: Load the wallet
    console.print("\n[bold yellow]Step 2: Loading Wallet[/bold yellow]")
    if wallet_manager.load_wallet(wallet_name, password):
        console.print(f"[green]✅ Wallet '{wallet_name}' loaded successfully[/green]")
    else:
        console.print("[red]❌ Failed to load wallet[/red]")
        return
    
    # Step 3: Create coldkeys (master accounts)
    console.print("\n[bold yellow]Step 3: Creating Coldkeys[/bold yellow]")
    
    # Create validator coldkey
    validator_coldkey = wallet_manager.create_coldkey(wallet_name, "validator", account_index=0)
    console.print(f"[green]✅ Validator coldkey created[/green]")
    console.print(f"[dim]Address: {validator_coldkey['address']}[/dim]")
    
    # Create miner coldkey
    miner_coldkey = wallet_manager.create_coldkey(wallet_name, "miner", account_index=1)
    console.print(f"[green]✅ Miner coldkey created[/green]")
    console.print(f"[dim]Address: {miner_coldkey['address']}[/dim]")
    
    # Step 4: Create hotkeys (derived accounts)
    console.print("\n[bold yellow]Step 4: Creating Hotkeys[/bold yellow]")
    
    # Create hotkeys for validator
    val_hotkey1 = wallet_manager.create_hotkey(wallet_name, "validator", "val_operator", address_index=1)
    val_hotkey2 = wallet_manager.create_hotkey(wallet_name, "validator", "val_backup", address_index=2)
    
    # Create hotkeys for miner
    miner_hotkey1 = wallet_manager.create_hotkey(wallet_name, "miner", "miner_worker", address_index=1)
    miner_hotkey2 = wallet_manager.create_hotkey(wallet_name, "miner", "miner_staking", address_index=2)
    
    console.print(f"[green]✅ Created 4 hotkeys under 2 coldkeys[/green]")
    
    # Step 5: Display wallet structure
    console.print("\n[bold yellow]Step 5: Wallet Structure[/bold yellow]")
    wallet_manager.display_wallet_info(wallet_name)
    
    # Step 6: Get Aptos accounts for usage
    console.print("\n[bold yellow]Step 6: Getting Account Objects[/bold yellow]")
    
    # Get validator coldkey account
    validator_account = wallet_manager.get_account(wallet_name, "validator")
    console.print(f"[green]✅ Validator coldkey account loaded[/green]")
    console.print(f"[dim]Address: {validator_account.address().hex()}[/dim]")
    
    # Get miner hotkey account
    miner_worker_account = wallet_manager.get_account(wallet_name, "miner", "miner_worker")
    console.print(f"[green]✅ Miner worker hotkey account loaded[/green]")
    console.print(f"[dim]Address: {miner_worker_account.address().hex()}[/dim]")
    
    # Step 7: Export private keys (for demonstration)
    console.print("\n[bold yellow]Step 7: Private Key Export Demo[/bold yellow]")
    
    validator_private_key = wallet_manager.export_private_key(wallet_name, "validator")
    console.print(f"[green]✅ Validator coldkey private key exported[/green]")
    console.print(f"[dim]Key (first 16 chars): {validator_private_key[:16]}...[/dim]")
    
    miner_worker_private_key = wallet_manager.export_private_key(wallet_name, "miner", "miner_worker")
    console.print(f"[green]✅ Miner worker private key exported[/green]")
    console.print(f"[dim]Key (first 16 chars): {miner_worker_private_key[:16]}...[/dim]")
    
    # Summary
    console.print(Panel.fit(
        "[bold green]🎉 Demo Completed Successfully![/bold green]\n\n"
        "Created:\n"
        "• 1 HD Wallet with 24-word mnemonic\n"
        "• 2 Coldkeys (validator, miner)\n"
        "• 4 Hotkeys (2 per coldkey)\n"
        "• All keys derived from single mnemonic\n\n"
        "[bold yellow]Key Features:[/bold yellow]\n"
        "• BIP44 HD derivation (m/44'/637'/account'/0'/address')\n"
        "• Encrypted mnemonic storage\n"
        "• Hierarchical key management\n"
        "• Compatible with Aptos ecosystem\n"
        "• Similar to Bittensor's key system",
        title="✅ Demo Summary",
        border_style="green"
    ))
    
    return wallet_manager, wallet_name


def demo_wallet_restoration():
    """Demonstrate wallet restoration from mnemonic"""
    console.print(Panel.fit(
        "[bold cyan]🔄 HD Wallet Demo - Restoration[/bold cyan]\n\n"
        "This demo shows how to restore wallets from mnemonic",
        title="Wallet Restoration Demo",
        border_style="cyan"
    ))
    
    wallet_manager = AptosHDWalletManager()
    
    # Example mnemonic (DO NOT use in production)
    demo_mnemonic = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
    
    console.print("\n[bold yellow]Restoring wallet from mnemonic...[/bold yellow]")
    
    restored_wallet = "restored_wallet"
    password = "restore_password_123"
    
    if wallet_manager.restore_wallet(restored_wallet, demo_mnemonic, password):
        console.print(f"[green]✅ Wallet '{restored_wallet}' restored successfully[/green]")
        
        # Load the restored wallet
        if wallet_manager.load_wallet(restored_wallet, password):
            console.print(f"[green]✅ Restored wallet loaded[/green]")
            
            # Create some accounts to verify restoration
            coldkey = wallet_manager.create_coldkey(restored_wallet, "restored_coldkey", 0)
            hotkey = wallet_manager.create_hotkey(restored_wallet, "restored_coldkey", "restored_hotkey", 1)
            
            console.print(f"[green]✅ Created accounts in restored wallet[/green]")
            wallet_manager.display_wallet_info(restored_wallet)
    
    return wallet_manager


def demo_key_import():
    """Demonstrate importing external private keys"""
    console.print(Panel.fit(
        "[bold cyan]📥 HD Wallet Demo - Key Import[/bold cyan]\n\n"
        "This demo shows how to import external private keys",
        title="Key Import Demo",
        border_style="cyan"
    ))
    
    wallet_manager = AptosHDWalletManager()
    
    # First create a wallet to import into
    wallet_name = "import_wallet"
    password = "import_password_123"
    
    wallet_manager.create_wallet(wallet_name, password, 12)
    wallet_manager.load_wallet(wallet_name, password)
    
    # Import an external private key (example key - DO NOT use in production)
    example_private_key = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
    
    try:
        imported_account = wallet_manager.import_account_by_private_key(
            wallet_name, 
            example_private_key, 
            "imported_account"
        )
        
        console.print(f"[green]✅ External private key imported successfully[/green]")
        console.print(f"[dim]Address: {imported_account['address']}[/dim]")
        
        # Show the wallet structure
        wallet_manager.display_wallet_info(wallet_name)
        
    except Exception as e:
        console.print(f"[red]❌ Error importing key: {e}[/red]")


def demo_cli_usage():
    """Show CLI usage examples"""
    console.print(Panel.fit(
        "[bold cyan]💻 CLI Usage Examples[/bold cyan]\n\n"
        "[bold yellow]Create a new HD wallet:[/bold yellow]\n"
        "[cyan]mtcli hdwallet create --name my_wallet --words 24[/cyan]\n\n"
        "[bold yellow]Load a wallet:[/bold yellow]\n"
        "[cyan]mtcli hdwallet load --name my_wallet[/cyan]\n\n"
        "[bold yellow]Create coldkey:[/bold yellow]\n"
        "[cyan]mtcli hdwallet create-coldkey --wallet my_wallet --name validator[/cyan]\n\n"
        "[bold yellow]Create hotkey:[/bold yellow]\n"
        "[cyan]mtcli hdwallet create-hotkey --wallet my_wallet --coldkey validator --name operator[/cyan]\n\n"
        "[bold yellow]Export private key:[/bold yellow]\n"
        "[cyan]mtcli hdwallet export-key --wallet my_wallet --coldkey validator --hotkey operator[/cyan]\n\n"
        "[bold yellow]Show wallet info:[/bold yellow]\n"
        "[cyan]mtcli hdwallet info --wallet my_wallet[/cyan]\n\n"
        "[bold yellow]Restore from mnemonic:[/bold yellow]\n"
        "[cyan]mtcli hdwallet restore --name restored_wallet[/cyan]",
        title="🏦 HD Wallet CLI Commands",
        border_style="cyan"
    ))


def cleanup_demo():
    """Clean up demo files"""
    import shutil
    demo_dir = Path("./demo_wallets")
    if demo_dir.exists():
        shutil.rmtree(demo_dir)
        console.print("[yellow]🧹 Demo files cleaned up[/yellow]")


def main():
    """Main demo function"""
    console.print("[bold blue]🚀 Starting ModernTensor HD Wallet Demo[/bold blue]\n")
    
    # Setup demo environment
    setup_demo_environment()
    
    try:
        # Run basic usage demo
        demo_basic_usage()
        
        console.print("\n" + "="*80 + "\n")
        
        # Run restoration demo
        demo_wallet_restoration()
        
        console.print("\n" + "="*80 + "\n")
        
        # Run import demo
        demo_key_import()
        
        console.print("\n" + "="*80 + "\n")
        
        # Show CLI usage
        demo_cli_usage()
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Demo interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Demo error: {e}[/red]")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up
        cleanup_demo()
    
    console.print("\n[bold green]🎉 HD Wallet Demo Complete![/bold green]")
    console.print("\n[bold yellow]Next Steps:[/bold yellow]")
    console.print("1. Try the CLI commands: [cyan]mtcli hdwallet --help[/cyan]")
    console.print("2. Create your own HD wallet for development")
    console.print("3. Integrate with your ModernTensor applications")


if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
"""
Migration Helper for ModernTensor Aptos HD Wallet System
Helps migrate from old keymanager systems and hardcoded private keys to HD wallet
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from aptos_sdk.account import Account

# Add parent directories to path for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir.parent.parent.parent))

from moderntensor.mt_aptos.keymanager.hd_wallet_manager import AptosHDWalletManager
from moderntensor.mt_aptos.keymanager.wallet_utils import WalletUtils
from moderntensor.mt_aptos.config.settings import logger

console = Console()

class MigrationHelper:
    """
    Helper class to migrate from old keymanager systems to HD wallet
    """
    
    def __init__(self, base_dir: str = None):
        """
        Initialize migration helper
        
        Args:
            base_dir: Base directory for HD wallet storage
        """
        self.base_dir = base_dir or "./wallets"
        self.hd_wallet_manager = AptosHDWalletManager(self.base_dir)
        self.utils = WalletUtils(self.base_dir)
    
    def create_migration_wallet(self, wallet_name: str, password: str, word_count: int = 24) -> str:
        """
        Create a new HD wallet for migration
        
        Args:
            wallet_name: Name for the new wallet
            password: Password for the wallet
            word_count: Number of words in mnemonic (12 or 24)
            
        Returns:
            str: Generated mnemonic phrase
        """
        console.print(f"\n[bold blue]🔄 Creating migration wallet: {wallet_name}[/bold blue]")
        
        try:
            mnemonic = self.hd_wallet_manager.create_wallet(wallet_name, password, word_count)
            console.print(f"[green]✅ Created migration wallet: {wallet_name}[/green]")
            console.print(f"[yellow]📝 Mnemonic: {mnemonic}[/yellow]")
            return mnemonic
        except Exception as e:
            console.print(f"[red]❌ Failed to create migration wallet: {e}[/red]")
            raise
    
    def migrate_from_private_keys(self, private_keys: Dict[str, str], 
                                 wallet_name: str, password: str, 
                                 coldkey_name: str = "migrated_coldkey") -> Dict[str, str]:
        """
        Migrate from hardcoded private keys to HD wallet structure
        
        Args:
            private_keys: Dictionary of {account_name: private_key_hex}
            wallet_name: Name for the new wallet
            password: Password for the wallet
            coldkey_name: Name for the coldkey
            
        Returns:
            Dict mapping old account names to new HD wallet addresses
        """
        console.print(f"\n[bold blue]🔄 Migrating {len(private_keys)} private keys to HD wallet[/bold blue]")
        
        # Create wallet if it doesn't exist
        if not self.hd_wallet_manager.wallet_exists(wallet_name):
            self.create_migration_wallet(wallet_name, password)
        
        # Load wallet
        self.hd_wallet_manager.load_wallet(wallet_name, password)
        
        # Create coldkey if it doesn't exist
        if not self.hd_wallet_manager.coldkey_exists(wallet_name, coldkey_name):
            self.hd_wallet_manager.create_coldkey(wallet_name, coldkey_name)
        
        # Track migration results
        migration_results = {}
        
        console.print(f"\n[yellow]Migrating individual private keys...[/yellow]")
        
        for account_name, private_key_hex in private_keys.items():
            try:
                # Clean private key
                if private_key_hex.startswith("0x"):
                    private_key_hex = private_key_hex[2:]
                
                # Verify private key is valid
                test_account = Account.load_key(bytes.fromhex(private_key_hex))
                original_address = str(test_account.address())
                
                # Create hotkey with the same name
                hotkey_info = self.hd_wallet_manager.create_hotkey(wallet_name, coldkey_name, account_name)
                new_address = hotkey_info['address']
                
                migration_results[account_name] = {
                    'old_address': original_address,
                    'new_address': new_address,
                    'hotkey_name': account_name,
                    'derivation_path': hotkey_info['derivation_path']
                }
                
                console.print(f"[green]✅ Migrated {account_name}:[/green]")
                console.print(f"  [dim]Old: {original_address}[/dim]")
                console.print(f"  [dim]New: {new_address}[/dim]")
                console.print(f"  [dim]Path: {hotkey_info['derivation_path']}[/dim]")
                
            except Exception as e:
                console.print(f"[red]❌ Failed to migrate {account_name}: {e}[/red]")
                
        return migration_results
    
    def migrate_from_old_keymanager(self, old_keymanager_dir: str, 
                                   wallet_name: str, password: str) -> Dict[str, str]:
        """
        Migrate from old keymanager format to HD wallet
        
        Args:
            old_keymanager_dir: Directory containing old keymanager files
            wallet_name: Name for the new wallet
            password: Password for the wallet
            
        Returns:
            Dict with migration results
        """
        console.print(f"\n[bold blue]🔄 Migrating from old keymanager: {old_keymanager_dir}[/bold blue]")
        
        # Look for old keymanager files
        old_dir = Path(old_keymanager_dir)
        if not old_dir.exists():
            console.print(f"[red]❌ Old keymanager directory not found: {old_keymanager_dir}[/red]")
            return {}
        
        # Create new wallet
        if not self.hd_wallet_manager.wallet_exists(wallet_name):
            self.create_migration_wallet(wallet_name, password)
        
        # Load wallet
        self.hd_wallet_manager.load_wallet(wallet_name, password)
        
        migration_results = {}
        
        # Look for hotkeys.json
        hotkeys_file = old_dir / "hotkeys.json"
        if hotkeys_file.exists():
            try:
                with open(hotkeys_file, 'r') as f:
                    hotkeys_data = json.load(f)
                
                console.print(f"[yellow]Found {len(hotkeys_data)} accounts in hotkeys.json[/yellow]")
                
                for coldkey_name, coldkey_data in hotkeys_data.items():
                    # Create coldkey
                    if not self.hd_wallet_manager.coldkey_exists(wallet_name, coldkey_name):
                        self.hd_wallet_manager.create_coldkey(wallet_name, coldkey_name)
                    
                    # Process hotkeys
                    if "hotkeys" in coldkey_data:
                        for hotkey_name, hotkey_data in coldkey_data["hotkeys"].items():
                            try:
                                # Create hotkey in new system
                                hotkey_info = self.hd_wallet_manager.create_hotkey(wallet_name, coldkey_name, hotkey_name)
                                
                                migration_results[f"{coldkey_name}.{hotkey_name}"] = {
                                    'old_address': hotkey_data.get('address', 'unknown'),
                                    'new_address': hotkey_info['address'],
                                    'derivation_path': hotkey_info['derivation_path']
                                }
                                
                                console.print(f"[green]✅ Migrated {coldkey_name}.{hotkey_name}[/green]")
                                
                            except Exception as e:
                                console.print(f"[red]❌ Failed to migrate {coldkey_name}.{hotkey_name}: {e}[/red]")
                
            except Exception as e:
                console.print(f"[red]❌ Failed to read hotkeys.json: {e}[/red]")
        
        return migration_results
    
    def generate_migration_config(self, migration_results: Dict[str, str], 
                                 wallet_name: str, coldkey_name: str = "migrated_coldkey") -> str:
        """
        Generate configuration file for migrated accounts
        
        Args:
            migration_results: Results from migration
            wallet_name: Name of the wallet
            coldkey_name: Name of the coldkey
            
        Returns:
            str: Path to generated config file
        """
        config_content = f"""# ModernTensor HD Wallet Migration Config
# Generated on: {datetime.now().isoformat()}

# HD Wallet Configuration
HD_WALLET_NAME = "{wallet_name}"
HD_WALLET_COLDKEY = "{coldkey_name}"

# Migrated Account Mapping
"""
        
        for account_name, info in migration_results.items():
            if isinstance(info, dict):
                config_content += f"""
# {account_name}
{account_name.upper()}_HD_WALLET = "{wallet_name}"
{account_name.upper()}_HD_COLDKEY = "{coldkey_name}"
{account_name.upper()}_HD_HOTKEY = "{info.get('hotkey_name', account_name)}"
{account_name.upper()}_HD_ADDRESS = "{info.get('new_address', '')}"
{account_name.upper()}_HD_PATH = "{info.get('derivation_path', '')}"
"""
        
        # Write config file
        config_file = Path(self.base_dir) / f"{wallet_name}_migration_config.py"
        with open(config_file, 'w') as f:
            f.write(config_content)
        
        console.print(f"[green]✅ Generated migration config: {config_file}[/green]")
        return str(config_file)
    
    def create_migration_summary(self, migration_results: Dict[str, str], 
                                wallet_name: str) -> None:
        """
        Create and display migration summary
        
        Args:
            migration_results: Results from migration
            wallet_name: Name of the wallet
        """
        console.print(f"\n[bold blue]📊 Migration Summary for {wallet_name}[/bold blue]")
        
        # Create summary table
        table = Table(title=f"Migration Results - {wallet_name}")
        table.add_column("Account", style="cyan")
        table.add_column("Old Address", style="red")
        table.add_column("New Address", style="green")
        table.add_column("Derivation Path", style="yellow")
        
        for account_name, info in migration_results.items():
            if isinstance(info, dict):
                old_addr = info.get('old_address', 'N/A')
                new_addr = info.get('new_address', 'N/A')
                table.add_row(
                    account_name,
                    f"{old_addr[:10]}...{old_addr[-6:]}" if len(old_addr) > 16 else old_addr,
                    f"{new_addr[:10]}...{new_addr[-6:]}" if len(new_addr) > 16 else new_addr,
                    info.get('derivation_path', 'N/A')
                )
        
        console.print(table)
        
        # Summary stats
        console.print(f"\n[bold green]✅ Migration Complete![/bold green]")
        console.print(f"[yellow]• Total accounts migrated: {len(migration_results)}[/yellow]")
        console.print(f"[yellow]• HD Wallet: {wallet_name}[/yellow]")
        console.print(f"[yellow]• Base directory: {self.base_dir}[/yellow]")
    
    def generate_code_migration_templates(self, migration_results: Dict[str, str], 
                                        wallet_name: str, coldkey_name: str = "migrated_coldkey") -> Dict[str, str]:
        """
        Generate code templates for migrating from old Account.load_key() to HD wallet
        
        Args:
            migration_results: Results from migration
            wallet_name: Name of the wallet
            coldkey_name: Name of the coldkey
            
        Returns:
            Dict with different migration templates
        """
        templates = {}
        
        # Template 1: Basic account loading
        templates["basic_loading"] = f"""
# OLD CODE:
# account = Account.load_key(private_key)

# NEW CODE:
from moderntensor.mt_aptos.keymanager.wallet_utils import WalletUtils
utils = WalletUtils()
account = utils.quick_load_account('{wallet_name}', '{coldkey_name}', 'HOTKEY_NAME')
"""
        
        # Template 2: Account loading with password
        templates["with_password"] = f"""
# OLD CODE:
# account = Account.load_key(private_key)

# NEW CODE:
from moderntensor.mt_aptos.keymanager.wallet_utils import WalletUtils
utils = WalletUtils()
account = utils.quick_load_account('{wallet_name}', '{coldkey_name}', 'HOTKEY_NAME', 'PASSWORD')
"""
        
        # Template 3: Account manager initialization
        templates["account_manager"] = f"""
# OLD CODE:
# from mt_aptos.keymanager.account_manager import AccountManager
# account_manager = AccountManager()

# NEW CODE:
from moderntensor.mt_aptos.keymanager.hd_wallet_manager import AptosHDWalletManager
from moderntensor.mt_aptos.keymanager.wallet_utils import WalletUtils
hd_wallet = AptosHDWalletManager()
utils = WalletUtils()
"""
        
        # Template 4: Multiple account loading
        account_examples = []
        for account_name, info in migration_results.items():
            if isinstance(info, dict):
                hotkey_name = info.get('hotkey_name', account_name)
                account_examples.append(f"# {account_name} account\n{account_name}_account = utils.quick_load_account('{wallet_name}', '{coldkey_name}', '{hotkey_name}')")
        
        templates["multiple_accounts"] = f"""
# OLD CODE:
# validator_account = Account.load_key(VALIDATOR_PRIVATE_KEY)
# miner_account = Account.load_key(MINER_PRIVATE_KEY)

# NEW CODE:
from moderntensor.mt_aptos.keymanager.wallet_utils import WalletUtils
utils = WalletUtils()

{chr(10).join(account_examples)}
"""
        
        # Template 5: Configuration migration
        templates["config_migration"] = f"""
# OLD CONFIG:
# VALIDATOR_PRIVATE_KEY = "0x..."
# MINER_PRIVATE_KEY = "0x..."

# NEW CONFIG:
HD_WALLET_NAME = "{wallet_name}"
HD_WALLET_COLDKEY = "{coldkey_name}"
HD_WALLET_PASSWORD = "your_wallet_password"

# Account mappings:
"""
        
        for account_name, info in migration_results.items():
            if isinstance(info, dict):
                hotkey_name = info.get('hotkey_name', account_name)
                templates["config_migration"] += f"""
{account_name.upper()}_HD_WALLET = "{wallet_name}"
{account_name.upper()}_HD_COLDKEY = "{coldkey_name}"
{account_name.upper()}_HD_HOTKEY = "{hotkey_name}"
"""
        
        return templates
    
    def interactive_migration_wizard(self) -> None:
        """
        Interactive wizard for migration
        """
        console.print(Panel.fit(
            "[bold cyan]🧙 ModernTensor HD Wallet Migration Wizard[/bold cyan]\n\n"
            "[yellow]This wizard will help you migrate from old keymanager or private keys to HD wallet[/yellow]",
            title="Migration Wizard",
            border_style="cyan"
        ))
        
        # Choose migration type
        console.print("\n[bold blue]Select Migration Type:[/bold blue]")
        console.print("[1] Migrate from hardcoded private keys")
        console.print("[2] Migrate from old keymanager")
        console.print("[3] Manual migration guidance")
        
        choice = Prompt.ask("Choose option", choices=["1", "2", "3"])
        
        if choice == "1":
            self._migrate_private_keys_wizard()
        elif choice == "2":
            self._migrate_old_keymanager_wizard()
        elif choice == "3":
            self._manual_migration_guidance()
    
    def _migrate_private_keys_wizard(self) -> None:
        """
        Wizard for migrating private keys
        """
        console.print("\n[bold blue]🔐 Private Key Migration Wizard[/bold blue]")
        
        # Get wallet details
        wallet_name = Prompt.ask("Enter new wallet name", default="migrated_wallet")
        password = Prompt.ask("Enter wallet password", password=True)
        coldkey_name = Prompt.ask("Enter coldkey name", default="migrated_coldkey")
        
        # Get private keys
        private_keys = {}
        console.print("\n[yellow]Enter private keys (enter empty name to finish):[/yellow]")
        
        while True:
            account_name = Prompt.ask("Account name")
            if not account_name:
                break
            
            private_key = Prompt.ask("Private key", password=True)
            if private_key:
                private_keys[account_name] = private_key
        
        if not private_keys:
            console.print("[red]No private keys provided. Exiting.[/red]")
            return
        
        # Perform migration
        try:
            migration_results = self.migrate_from_private_keys(
                private_keys, wallet_name, password, coldkey_name
            )
            
            # Generate summary and configs
            self.create_migration_summary(migration_results, wallet_name)
            self.generate_migration_config(migration_results, wallet_name, coldkey_name)
            
            # Generate code templates
            templates = self.generate_code_migration_templates(migration_results, wallet_name, coldkey_name)
            
            # Save templates
            template_file = Path(self.base_dir) / f"{wallet_name}_migration_templates.py"
            with open(template_file, 'w') as f:
                f.write("# ModernTensor HD Wallet Migration Templates\n\n")
                for template_name, template_code in templates.items():
                    f.write(f"# {template_name.upper()}\n")
                    f.write(template_code)
                    f.write("\n\n")
            
            console.print(f"[green]✅ Migration templates saved: {template_file}[/green]")
            
        except Exception as e:
            console.print(f"[red]❌ Migration failed: {e}[/red]")
    
    def _migrate_old_keymanager_wizard(self) -> None:
        """
        Wizard for migrating from old keymanager
        """
        console.print("\n[bold blue]🔄 Old Keymanager Migration Wizard[/bold blue]")
        
        # Get directories
        old_dir = Prompt.ask("Enter old keymanager directory")
        wallet_name = Prompt.ask("Enter new wallet name", default="migrated_wallet")
        password = Prompt.ask("Enter wallet password", password=True)
        
        # Perform migration
        try:
            migration_results = self.migrate_from_old_keymanager(old_dir, wallet_name, password)
            
            if migration_results:
                self.create_migration_summary(migration_results, wallet_name)
                self.generate_migration_config(migration_results, wallet_name)
            else:
                console.print("[yellow]No accounts found to migrate.[/yellow]")
                
        except Exception as e:
            console.print(f"[red]❌ Migration failed: {e}[/red]")
    
    def _manual_migration_guidance(self) -> None:
        """
        Provide manual migration guidance
        """
        console.print("\n[bold blue]📖 Manual Migration Guidance[/bold blue]")
        
        guidance = """
[bold cyan]Step-by-step migration process:[/bold cyan]

[yellow]1. Create HD Wallet:[/yellow]
   from moderntensor.mt_aptos.keymanager.hd_wallet_manager import AptosHDWalletManager
   hd_wallet = AptosHDWalletManager()
   mnemonic = hd_wallet.create_wallet("my_wallet", "password")

[yellow]2. Load Wallet:[/yellow]
   hd_wallet.load_wallet("my_wallet", "password")

[yellow]3. Create Coldkey:[/yellow]
   coldkey_info = hd_wallet.create_coldkey("my_wallet", "master_key")

[yellow]4. Create Hotkeys:[/yellow]
   hotkey_info = hd_wallet.create_hotkey("my_wallet", "master_key", "validator")

[yellow]5. Update Your Code:[/yellow]
   # OLD: account = Account.load_key(private_key)
   # NEW: 
   from moderntensor.mt_aptos.keymanager.wallet_utils import WalletUtils
   utils = WalletUtils()
   account = utils.quick_load_account("my_wallet", "master_key", "validator")

[yellow]6. Update Configuration:[/yellow]
   # Replace private key configs with HD wallet configs
   HD_WALLET_NAME = "my_wallet"
   HD_WALLET_COLDKEY = "master_key"
   HD_WALLET_PASSWORD = "password"
"""
        
        console.print(Panel(guidance, title="Migration Guidance", border_style="yellow"))


if __name__ == "__main__":
    # Example usage
    migration_helper = MigrationHelper()
    migration_helper.interactive_migration_wizard() 
#!/usr/bin/env python3
"""
Wallet Utility Functions for ModernTensor Aptos
Provides convenient functions for HD wallet operations and account loading
"""

import os
from typing import Optional, Dict, Any
from rich.console import Console
from rich.prompt import Prompt
import getpass

from .hd_wallet_manager import CoreHDWalletManager
from ..account import Account
from ..config.settings import settings, logger

console = Console()


class WalletUtils:
    """
    Utility class for convenient HD wallet operations
    """
    
    def __init__(self, base_dir: str = None):
        """
        Initialize wallet utilities
        
        Args:
            base_dir: Base directory for wallet storage
        """
        self.base_dir = base_dir or settings.HOTKEY_BASE_DIR
        if not self.base_dir:
            raise ValueError("Wallet base directory not configured")
        
        self.wallet_manager = CoreHDWalletManager(self.base_dir)
        self._loaded_wallets = {}
    
    def quick_load_account(
        self, 
        wallet_name: str, 
        coldkey_name: str, 
        hotkey_name: str = None, 
        password: str = None
    ) -> Optional[Account]:
        """
        Quick function to load an account from HD wallet
        
        Args:
            wallet_name: Name of the wallet
            coldkey_name: Name of the coldkey
            hotkey_name: Name of the hotkey (None for coldkey)
            password: Wallet password (will prompt if None)
            
        Returns:
            Account object or None if failed
        """
        try:
            # Load wallet if not already loaded
            if wallet_name not in self._loaded_wallets:
                if password is None:
                    password = getpass.getpass(f"🔐 Password for wallet '{wallet_name}': ")
                
                if not self.wallet_manager.load_wallet(wallet_name, password):
                    logger.error(f"Failed to load wallet '{wallet_name}'")
                    return None
                
                self._loaded_wallets[wallet_name] = True
                logger.info(f"✅ Loaded wallet '{wallet_name}'")
            
            # Get account
            account = self.wallet_manager.get_account(wallet_name, coldkey_name, hotkey_name)
            
            key_type = "hotkey" if hotkey_name else "coldkey"
            key_name = hotkey_name if hotkey_name else coldkey_name
            logger.info(f"✅ Loaded {key_type} '{key_name}': {str(account.address())}")
            
            return account
            
        except Exception as e:
            logger.error(f"❌ Failed to load account: {e}")
            return None
    
    def decrypt_and_get_account(
        self, 
        wallet_name: str, 
        coldkey_name: str, 
        hotkey_name: str = None,
        interactive: bool = True
    ) -> Optional[Account]:
        """
        Decrypt wallet and get account (interactive mode)
        
        Args:
            wallet_name: Name of the wallet
            coldkey_name: Name of the coldkey  
            hotkey_name: Name of the hotkey (None for coldkey)
            interactive: Whether to use interactive prompts
            
        Returns:
            Account object or None if failed
        """
        try:
            if interactive:
                console.print(f"\n[bold cyan]🔐 Loading Account from HD Wallet[/bold cyan]")
                console.print(f"[dim]Wallet: {wallet_name}[/dim]")
                console.print(f"[dim]Coldkey: {coldkey_name}[/dim]")
                if hotkey_name:
                    console.print(f"[dim]Hotkey: {hotkey_name}[/dim]")
                
                password = getpass.getpass("🔐 Enter wallet password: ")
            else:
                password = getpass.getpass()
            
            # Load and get account
            account = self.quick_load_account(wallet_name, coldkey_name, hotkey_name, password)
            
            if account and interactive:
                console.print(f"[bold green]✅ Account loaded successfully![/bold green]")
                console.print(f"[dim]Address: {str(account.address())}[/dim]")
            
            return account
            
        except Exception as e:
            if interactive:
                console.print(f"[bold red]❌ Error: {e}[/bold red]")
            logger.error(f"Failed to decrypt and get account: {e}")
            return None
    
    def get_private_key(
        self, 
        wallet_name: str, 
        coldkey_name: str, 
        hotkey_name: str = None,
        password: str = None
    ) -> Optional[str]:
        """
        Get private key for an account
        
        Args:
            wallet_name: Name of the wallet
            coldkey_name: Name of the coldkey
            hotkey_name: Name of the hotkey (None for coldkey)
            password: Wallet password (will prompt if None)
            
        Returns:
            Private key hex string or None if failed
        """
        try:
            # Load wallet if needed
            if wallet_name not in self._loaded_wallets:
                if password is None:
                    password = getpass.getpass(f"🔐 Password for wallet '{wallet_name}': ")
                
                if not self.wallet_manager.load_wallet(wallet_name, password):
                    return None
                
                self._loaded_wallets[wallet_name] = True
            
            # Export private key
            private_key = self.wallet_manager.export_private_key(wallet_name, coldkey_name, hotkey_name)
            return private_key
            
        except Exception as e:
            logger.error(f"Failed to get private key: {e}")
            return None
    
    def list_available_accounts(self, wallet_name: str = None) -> Dict[str, Any]:
        """
        List all available accounts in wallet(s)
        
        Args:
            wallet_name: Specific wallet name (None for all wallets)
            
        Returns:
            Dictionary with wallet and account information
        """
        try:
            result = {}
            
            if wallet_name:
                wallets = [wallet_name]
            else:
                wallets = self.wallet_manager.list_wallets()
            
            for wallet in wallets:
                try:
                    # Try to load metadata without password (just structure)
                    wallet_dir = os.path.join(self.base_dir, wallet)
                    metadata_path = os.path.join(wallet_dir, "metadata.json")
                    
                    if os.path.exists(metadata_path):
                        import json
                        with open(metadata_path, 'r') as f:
                            metadata = json.load(f)
                        
                        accounts = {}
                        for account_index, account_data in metadata.get("accounts", {}).items():
                            coldkey_name = account_data.get("name", f"coldkey_{account_index}")
                            accounts[coldkey_name] = {
                                "address": account_data.get("address", ""),
                                "derivation_path": account_data.get("derivation_path", ""),
                                "hotkeys": list(account_data.get("hotkeys", {}).keys())
                            }
                        
                        result[wallet] = {
                            "created_at": metadata.get("created_at", ""),
                            "accounts": accounts
                        }
                
                except Exception as e:
                    logger.debug(f"Could not read metadata for wallet '{wallet}': {e}")
                    result[wallet] = {"error": str(e)}
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to list accounts: {e}")
            return {}
    
    def display_account_summary(self, wallet_name: str = None):
        """
        Display a summary of available accounts
        
        Args:
            wallet_name: Specific wallet name (None for all wallets)
        """
        accounts = self.list_available_accounts(wallet_name)
        
        if not accounts:
            console.print("[yellow]No wallets found or accessible.[/yellow]")
            return
        
        from rich.table import Table
        
        for wallet, wallet_info in accounts.items():
            if "error" in wallet_info:
                console.print(f"[red]❌ Wallet '{wallet}': {wallet_info['error']}[/red]")
                continue
            
            console.print(f"\n[bold cyan]🏦 Wallet: {wallet}[/bold cyan]")
            console.print(f"[dim]Created: {wallet_info.get('created_at', 'Unknown')}[/dim]")
            
            accounts_data = wallet_info.get("accounts", {})
            if accounts_data:
                table = Table(title=f"Accounts in {wallet}")
                table.add_column("Coldkey", style="cyan")
                table.add_column("Address", style="green") 
                table.add_column("Hotkeys", style="yellow")
                
                for coldkey_name, coldkey_data in accounts_data.items():
                    address = coldkey_data.get("address", "")
                    hotkeys = coldkey_data.get("hotkeys", [])
                    
                    hotkey_display = f"{len(hotkeys)} keys: {', '.join(hotkeys[:3])}"
                    if len(hotkeys) > 3:
                        hotkey_display += "..."
                    
                    table.add_row(
                        coldkey_name,
                        f"{address[:10]}...{address[-6:]}" if address else "Unknown",
                        hotkey_display if hotkeys else "None"
                    )
                
                console.print(table)
            else:
                console.print("[dim]No accounts found in this wallet.[/dim]")
    
    def show_all_wallets(self):
        """
        Show summary of all available wallets
        """
        self.display_account_summary()


# Convenient standalone functions
def load_account_quick(
    wallet_name: str, 
    coldkey_name: str, 
    hotkey_name: str = None,
    base_dir: str = None
) -> Optional[Account]:
    """
    Quick standalone function to load an account
    
    Args:
        wallet_name: Name of the wallet
        coldkey_name: Name of the coldkey
        hotkey_name: Name of the hotkey (None for coldkey)
        base_dir: Base directory for wallets
        
    Returns:
        Account object or None if failed
    """
    utils = WalletUtils(base_dir)
    return utils.decrypt_and_get_account(wallet_name, coldkey_name, hotkey_name)


def get_account_for_validator(
    wallet_name: str = "validator_wallet",
    coldkey_name: str = "validator",
    hotkey_name: str = "main",
    base_dir: str = None
) -> Optional[Account]:
    """
    Convenient function to load validator account with defaults
    
    Args:
        wallet_name: Name of the validator wallet
        coldkey_name: Name of the validator coldkey
        hotkey_name: Name of the validator hotkey
        base_dir: Base directory for wallets
        
    Returns:
        Account object for validator operations
    """
    utils = WalletUtils(base_dir)
    console.print("[bold yellow]🔑 Loading Validator Account[/bold yellow]")
    return utils.decrypt_and_get_account(wallet_name, coldkey_name, hotkey_name)


def show_all_wallets(base_dir: str = None):
    """
    Show summary of all available wallets
    
    Args:
        base_dir: Base directory for wallets
    """
    utils = WalletUtils(base_dir)
    utils.display_account_summary()


if __name__ == "__main__":
    # Demo usage
    show_all_wallets() 
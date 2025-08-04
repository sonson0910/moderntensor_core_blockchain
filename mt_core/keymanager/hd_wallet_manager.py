# moderntensor/mt_core/keymanager/hd_wallet_manager.py

import os
import json
from typing import Optional, Dict, List, Tuple
from bip_utils import (
    Bip39MnemonicGenerator,
    Bip39Languages,
    Bip39SeedGenerator,
    Bip39MnemonicValidator,
    Bip44,
    Bip44Coins,
    Bip44Changes
)
from cryptography.fernet import Fernet, InvalidToken
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
import hashlib
import hmac
import datetime

from ..account import Account
from .encryption_utils import get_cipher_suite
from ..config.settings import settings, logger


class CoreHDWalletManager:
    """
    HD Wallet Manager for Aptos using BIP44 derivation
    Supports Bittensor-like coldkey/hotkey system with hierarchical deterministic wallets
    
    Derivation path: m/44'/637'/{account_index}'/0'/0'
    - 44: BIP44 standard
    - 637: Aptos coin type
    - account_index: Account index (0, 1, 2, ...)
    - 0: External chain (receiving addresses)
    - 0: Address index
    """
    
    APTOS_COIN_TYPE = 637
    
    def __init__(self, base_dir: str = None):
        """
        Initialize HD Wallet Manager
        
        Args:
            base_dir: Base directory for storing wallets
        """
        self.base_dir = base_dir or settings.HOTKEY_BASE_DIR
        if not self.base_dir:
            raise ValueError("Base directory not configured")
        
        os.makedirs(self.base_dir, exist_ok=True)
        self.console = Console()
        
        # In-memory storage for loaded wallets
        self.wallets: Dict[str, Dict] = {}
    
    def create_wallet(self, wallet_name: str, password: str, words_count: int = 24) -> str:
        """
        Create new HD wallet with encrypted mnemonic
        
        Args:
            wallet_name: Unique name for the wallet
            password: Password to encrypt the mnemonic
            words_count: Number of words in mnemonic (12, 15, 18, 21, 24)
            
        Returns:
            Generated mnemonic phrase
        """
        wallet_dir = os.path.join(self.base_dir, wallet_name)
        
        # Check if wallet already exists
        if os.path.exists(wallet_dir):
            raise ValueError(f"Wallet '{wallet_name}' already exists")
        
        os.makedirs(wallet_dir, exist_ok=True)
        
        # Generate mnemonic
        mnemonic = Bip39MnemonicGenerator(Bip39Languages.ENGLISH).FromWordsNumber(words_count)
        mnemonic_str = str(mnemonic)
        
        # Encrypt and save mnemonic
        cipher_suite = get_cipher_suite(password, wallet_dir)
        encrypted_mnemonic = cipher_suite.encrypt(mnemonic_str.encode('utf-8'))
        
        mnemonic_path = os.path.join(wallet_dir, "mnemonic.enc")
        with open(mnemonic_path, 'wb') as f:
            f.write(encrypted_mnemonic)
        
        # Create wallet metadata
        metadata = {
            "wallet_name": wallet_name,
            "created_at": datetime.datetime.now().isoformat(),
            "coin_type": self.APTOS_COIN_TYPE,
            "accounts": {},
            "next_account_index": 0
        }
        
        metadata_path = os.path.join(wallet_dir, "metadata.json")
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Display mnemonic to user
        self.console.print(Panel.fit(
            f"[bold yellow]🔐 Generated Mnemonic Phrase:[/bold yellow]\n\n"
            f"[bold white]{mnemonic_str}[/bold white]\n\n"
            f"[bold red]⚠️  CRITICAL: Store this mnemonic securely![/bold red]\n"
            f"[red]This is the ONLY way to recover your wallet![/red]",
            title="🏦 New Wallet Created",
            border_style="yellow"
        ))
        
        logger.info(f"Created HD wallet '{wallet_name}' with {words_count} words")
        return mnemonic_str
    
    def load_wallet(self, wallet_name: str, password: str) -> bool:
        """
        Load and decrypt wallet
        
        Args:
            wallet_name: Name of the wallet to load
            password: Password to decrypt the mnemonic
            
        Returns:
            True if successful, False otherwise
        """
        wallet_dir = os.path.join(self.base_dir, wallet_name)
        
        if not os.path.exists(wallet_dir):
            self.console.print(f"[bold red]❌ Wallet '{wallet_name}' not found[/bold red]")
            return False
        
        try:
            # Load metadata
            metadata_path = os.path.join(wallet_dir, "metadata.json")
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            # Decrypt mnemonic
            cipher_suite = get_cipher_suite(password, wallet_dir)
            mnemonic_path = os.path.join(wallet_dir, "mnemonic.enc")
            
            with open(mnemonic_path, 'rb') as f:
                encrypted_mnemonic = f.read()
            
            mnemonic = cipher_suite.decrypt(encrypted_mnemonic).decode('utf-8')
            
            # Generate master seed
            seed = Bip39SeedGenerator(mnemonic).Generate()
            
            # Store in memory
            self.wallets[wallet_name] = {
                "mnemonic": mnemonic,
                "seed": seed,
                "metadata": metadata,
                "cipher_suite": cipher_suite,
                "wallet_dir": wallet_dir
            }
            
            self.console.print(f"[bold green]✅ Wallet '{wallet_name}' loaded successfully[/bold green]")
            return True
            
        except InvalidToken:
            self.console.print(f"[bold red]❌ Invalid password for wallet '{wallet_name}'[/bold red]")
            return False
        except Exception as e:
            self.console.print(f"[bold red]❌ Error loading wallet '{wallet_name}': {e}[/bold red]")
            return False
    
    def create_coldkey(self, wallet_name: str, coldkey_name: str, account_index: int = None) -> Dict:
        """
        Create a coldkey (master account) from HD wallet
        
        Args:
            wallet_name: Name of the loaded wallet
            coldkey_name: Name for the coldkey
            account_index: Specific account index (auto-increment if None)
            
        Returns:
            Dictionary with coldkey info
        """
        if wallet_name not in self.wallets:
            raise ValueError(f"Wallet '{wallet_name}' not loaded")
        
        wallet_data = self.wallets[wallet_name]
        metadata = wallet_data["metadata"]
        
        # Determine account index
        if account_index is None:
            account_index = metadata["next_account_index"]
            metadata["next_account_index"] += 1
        
        # Check if account index already exists
        if str(account_index) in metadata["accounts"]:
            raise ValueError(f"Account index {account_index} already exists")
        
        # Generate key using BIP44 derivation
        # Path: m/44'/637'/{account_index}'/0'/0'
        try:
            # Create BIP44 object using Aptos coin
            bip44_obj = Bip44.FromSeed(wallet_data["seed"], Bip44Coins.APTOS)
            
            # Manual derivation for Aptos
            # m/44'/637'/{account_index}'/0'/0'
            purpose = bip44_obj.Purpose()
            coin = purpose.Coin()
            account = coin.Account(account_index)
            change = account.Change(Bip44Changes.CHAIN_EXT)
            address = change.AddressIndex(0)
            
            # Get private key
            private_key_bytes = address.PrivateKey().Raw().ToBytes()
            
            # Create Aptos account
            aptos_account = Account.load_key(private_key_bytes)
            address_hex = str(aptos_account.address())
            if not address_hex.startswith("0x"):
                address_hex = f"0x{address_hex}"
            
            # Create coldkey info
            coldkey_info = {
                "name": coldkey_name,
                "account_index": account_index,
                "derivation_path": f"m/44'/{self.APTOS_COIN_TYPE}'/{account_index}'/0'/0'",
                "address": address_hex,
                "public_key": str(aptos_account.public_key()),
                "created_at": datetime.datetime.now().isoformat(),
                "hotkeys": {}
            }
            
            # Store in metadata
            metadata["accounts"][str(account_index)] = coldkey_info
            
            # Save metadata
            self._save_metadata(wallet_name)
            
            self.console.print(f"[bold green]✅ Coldkey '{coldkey_name}' created[/bold green]")
            self.console.print(f"[dim]Address: {address_hex}[/dim]")
            self.console.print(f"[dim]Path: {coldkey_info['derivation_path']}[/dim]")
            
            return coldkey_info
            
        except Exception as e:
            raise ValueError(f"Failed to create coldkey: {e}")
    
    def create_hotkey(self, wallet_name: str, coldkey_name: str, hotkey_name: str, address_index: int = None) -> Dict:
        """
        Create a hotkey derived from coldkey
        
        Args:
            wallet_name: Name of the loaded wallet
            coldkey_name: Name of the parent coldkey
            hotkey_name: Name for the hotkey
            address_index: Specific address index (auto-increment if None)
            
        Returns:
            Dictionary with hotkey info
        """
        if wallet_name not in self.wallets:
            raise ValueError(f"Wallet '{wallet_name}' not loaded")
        
        wallet_data = self.wallets[wallet_name]
        metadata = wallet_data["metadata"]
        
        # Find coldkey
        coldkey_info = None
        coldkey_account_index = None
        
        for account_index, account_data in metadata["accounts"].items():
            if account_data["name"] == coldkey_name:
                coldkey_info = account_data
                coldkey_account_index = int(account_index)
                break
        
        if not coldkey_info:
            raise ValueError(f"Coldkey '{coldkey_name}' not found")
        
        # Determine address index
        if address_index is None:
            address_index = len(coldkey_info["hotkeys"]) + 1
        
        # Check if hotkey already exists
        if hotkey_name in coldkey_info["hotkeys"]:
            raise ValueError(f"Hotkey '{hotkey_name}' already exists")
        
        # Generate hotkey using BIP44 derivation
        # Path: m/44'/637'/{account_index}'/0'/{address_index}'
        try:
            bip44_obj = Bip44.FromSeed(wallet_data["seed"], Bip44Coins.APTOS)
            purpose = bip44_obj.Purpose()
            coin = purpose.Coin()
            account = coin.Account(coldkey_account_index)
            change = account.Change(Bip44Changes.CHAIN_EXT)
            address = change.AddressIndex(address_index)
            
            # Get private key
            private_key_bytes = address.PrivateKey().Raw().ToBytes()
            
            # Create Aptos account
            aptos_account = Account.load_key(private_key_bytes)
            address_hex = str(aptos_account.address())
            if not address_hex.startswith("0x"):
                address_hex = f"0x{address_hex}"
            
            # Create hotkey info
            hotkey_info = {
                "name": hotkey_name,
                "address_index": address_index,
                "derivation_path": f"m/44'/{self.APTOS_COIN_TYPE}'/{coldkey_account_index}'/0'/{address_index}'",
                "address": address_hex,
                "public_key": str(aptos_account.public_key()),
                "created_at": datetime.datetime.now().isoformat()
            }
            
            # Store in coldkey
            coldkey_info["hotkeys"][hotkey_name] = hotkey_info
            
            # Save metadata
            self._save_metadata(wallet_name)
            
            self.console.print(f"[bold green]✅ Hotkey '{hotkey_name}' created under coldkey '{coldkey_name}'[/bold green]")
            self.console.print(f"[dim]Address: {address_hex}[/dim]")
            self.console.print(f"[dim]Path: {hotkey_info['derivation_path']}[/dim]")
            
            return hotkey_info
            
        except Exception as e:
            raise ValueError(f"Failed to create hotkey: {e}")
    
    def get_account(self, wallet_name: str, coldkey_name: str, hotkey_name: str = None) -> Account:
        """
        Get Aptos Account object for coldkey or hotkey
        
        Args:
            wallet_name: Name of the loaded wallet
            coldkey_name: Name of the coldkey
            hotkey_name: Name of the hotkey (None for coldkey)
            
        Returns:
            Aptos Account object
        """
        if wallet_name not in self.wallets:
            raise ValueError(f"Wallet '{wallet_name}' not loaded")
        
        wallet_data = self.wallets[wallet_name]
        metadata = wallet_data["metadata"]
        
        # Find coldkey
        coldkey_info = None
        coldkey_account_index = None
        
        for account_index, account_data in metadata["accounts"].items():
            if account_data["name"] == coldkey_name:
                coldkey_info = account_data
                coldkey_account_index = int(account_index)
                break
        
        if not coldkey_info:
            raise ValueError(f"Coldkey '{coldkey_name}' not found")
        
        # Determine derivation path
        if hotkey_name is None:
            # Return coldkey account
            address_index = 0
        else:
            # Return hotkey account
            if hotkey_name not in coldkey_info["hotkeys"]:
                raise ValueError(f"Hotkey '{hotkey_name}' not found")
            
            hotkey_info = coldkey_info["hotkeys"][hotkey_name]
            address_index = hotkey_info["address_index"]
        
        # Generate account using BIP44
        try:
            bip44_obj = Bip44.FromSeed(wallet_data["seed"], Bip44Coins.APTOS)
            purpose = bip44_obj.Purpose()
            coin = purpose.Coin()
            account = coin.Account(coldkey_account_index)
            change = account.Change(Bip44Changes.CHAIN_EXT)
            address = change.AddressIndex(address_index)
            
            private_key_bytes = address.PrivateKey().Raw().ToBytes()
            return Account.load_key(private_key_bytes)
            
        except Exception as e:
            raise ValueError(f"Failed to get account: {e}")
    
    def list_wallets(self) -> List[str]:
        """List all available wallets"""
        wallets = []
        if os.path.exists(self.base_dir):
            for item in os.listdir(self.base_dir):
                wallet_dir = os.path.join(self.base_dir, item)
                if os.path.isdir(wallet_dir) and os.path.exists(os.path.join(wallet_dir, "metadata.json")):
                    wallets.append(item)
        return wallets
    
    def display_wallet_info(self, wallet_name: str):
        """Display detailed wallet information"""
        if wallet_name not in self.wallets:
            self.console.print(f"[bold red]❌ Wallet '{wallet_name}' not loaded[/bold red]")
            return
        
        wallet_data = self.wallets[wallet_name]
        metadata = wallet_data["metadata"]
        
        # Create main table
        table = Table(title=f"🏦 Wallet: {wallet_name}")
        table.add_column("Coldkey", style="cyan")
        table.add_column("Address", style="green")
        table.add_column("Hotkeys", style="yellow")
        
        for account_index, account_data in metadata["accounts"].items():
            coldkey_name = account_data["name"]
            address = account_data["address"]
            hotkey_count = len(account_data["hotkeys"])
            
            hotkey_names = ", ".join(account_data["hotkeys"].keys()) if hotkey_count > 0 else "None"
            
            table.add_row(
                coldkey_name,
                f"{address[:10]}...{address[-6:]}",
                f"{hotkey_count} keys: {hotkey_names}"
            )
        
        self.console.print(table)
    
    def restore_wallet(self, wallet_name: str, mnemonic: str, password: str) -> bool:
        """
        Restore wallet from mnemonic phrase
        
        Args:
            wallet_name: Name for the restored wallet
            mnemonic: Mnemonic phrase to restore from
            password: Password to encrypt the wallet
            
        Returns:
            True if successful, False otherwise
        """
        wallet_dir = os.path.join(self.base_dir, wallet_name)
        
        if os.path.exists(wallet_dir):
            import shutil
            shutil.rmtree(wallet_dir)
        
        try:
            os.makedirs(wallet_dir, exist_ok=True)
            
            # Validate mnemonic
            if not Bip39MnemonicValidator().IsValid(mnemonic):
                raise ValueError("Invalid mnemonic phrase")
            
            # Encrypt and save mnemonic
            cipher_suite = get_cipher_suite(password, wallet_dir)
            encrypted_mnemonic = cipher_suite.encrypt(mnemonic.encode('utf-8'))
            
            mnemonic_path = os.path.join(wallet_dir, "mnemonic.enc")
            with open(mnemonic_path, 'wb') as f:
                f.write(encrypted_mnemonic)
            
            # Create metadata
            metadata = {
                "wallet_name": wallet_name,
                "created_at": datetime.datetime.now().isoformat(),
                "coin_type": self.APTOS_COIN_TYPE,
                "accounts": {},
                "next_account_index": 0,
                "restored": True
            }
            
            metadata_path = os.path.join(wallet_dir, "metadata.json")
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            self.console.print(f"[bold green]✅ Wallet '{wallet_name}' restored successfully[/bold green]")
            return True
            
        except Exception as e:
            self.console.print(f"[bold red]❌ Error restoring wallet: {e}[/bold red]")
            return False
    
    def _save_metadata(self, wallet_name: str):
        """Save wallet metadata to disk"""
        if wallet_name not in self.wallets:
            return
        
        wallet_data = self.wallets[wallet_name]
        metadata_path = os.path.join(wallet_data["wallet_dir"], "metadata.json")
        
        with open(metadata_path, 'w') as f:
            json.dump(wallet_data["metadata"], f, indent=2)
    
    def export_private_key(self, wallet_name: str, coldkey_name: str, hotkey_name: str = None) -> str:
        """
        Export private key for coldkey or hotkey
        
        Args:
            wallet_name: Name of the loaded wallet
            coldkey_name: Name of the coldkey
            hotkey_name: Name of the hotkey (None for coldkey)
            
        Returns:
            Private key as hex string
        """
        account = self.get_account(wallet_name, coldkey_name, hotkey_name)
        return account.private_key.hex()
    
    def import_account_by_private_key(self, wallet_name: str, private_key_hex: str, account_name: str) -> Dict:
        """
        Import an account using private key (creates a new account entry)
        
        Args:
            wallet_name: Name of the loaded wallet
            private_key_hex: Private key as hex string
            account_name: Name for the imported account
            
        Returns:
            Account info dictionary
        """
        if wallet_name not in self.wallets:
            raise ValueError(f"Wallet '{wallet_name}' not loaded")
        
        try:
            # Create account from private key
            private_key_bytes = bytes.fromhex(private_key_hex)
            aptos_account = Account.load_key(private_key_bytes)
            
            address = str(aptos_account.address())
            if not address.startswith("0x"):
                address = f"0x{address}"
            
            # Create account info (non-HD derivation)
            account_info = {
                "name": account_name,
                "account_index": -1,  # Mark as imported
                "derivation_path": "imported",
                "address": address,
                "public_key": str(aptos_account.public_key()),
                "created_at": datetime.datetime.now().isoformat(),
                "hotkeys": {},
                "imported": True,
                "private_key_hex": private_key_hex  # Store for imported accounts
            }
            
            wallet_data = self.wallets[wallet_name]
            metadata = wallet_data["metadata"]
            
            # Use negative indices for imported accounts
            import_index = -1
            while str(import_index) in metadata["accounts"]:
                import_index -= 1
            
            metadata["accounts"][str(import_index)] = account_info
            self._save_metadata(wallet_name)
            
            self.console.print(f"[bold green]✅ Account '{account_name}' imported successfully[/bold green]")
            self.console.print(f"[dim]Address: {address}[/dim]")
            
            return account_info
            
        except Exception as e:
            raise ValueError(f"Failed to import account: {e}") 
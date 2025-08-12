# moderntensor/mt_aptos/cli/hd_wallet_cli.py

import click
import getpass
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt, Confirm
from typing import Optional

from ..keymanager.hd_wallet_manager import CoreHDWalletManager
from ..keymanager.wallet_utils import WalletUtils
from ..config.settings import settings

console = Console()

# Global wallet utils instance for persistent loading
_wallet_utils = WalletUtils()


@click.group()
@click.pass_context
def hdwallet(ctx):
    """🏦 HD Wallet Management - ModernTensor-like coldkey/hotkey system for Core"""
    ctx.ensure_object(dict)
    ctx.obj["wallet_manager"] = CoreHDWalletManager()
    ctx.obj["wallet_utils"] = _wallet_utils


@hdwallet.command()
@click.option("--name", required=True, help="Name for the new wallet")
@click.option(
    "--words",
    default="24",
    type=click.Choice(["12", "15", "18", "21", "24"]),
    help="Number of words in mnemonic",
)
@click.pass_context
def create(ctx, name: str, words: str):
    """🆕 Create a new HD wallet with encrypted mnemonic"""
    wallet_manager = ctx.obj["wallet_manager"]

    try:
        # Get password
        password = getpass.getpass("🔐 Enter password to encrypt wallet: ")
        confirm_password = getpass.getpass("🔐 Confirm password: ")

        if password != confirm_password:
            console.print("[bold red]❌ Passwords do not match![/bold red]")
            return

        if len(password) < 8:
            console.print(
                "[bold red]❌ Password must be at least 8 characters![/bold red]"
            )
            return

        # Create wallet
        mnemonic = wallet_manager.create_wallet(name, password, int(words))

        console.print(
            f"\n[bold green]✅ HD Wallet '{name}' created successfully![/bold green]"
        )
        console.print("\n[bold yellow]📋 Next steps:[/bold yellow]")
        console.print("1. [dim]Store your mnemonic phrase securely[/dim]")
        console.print(
            "2. [dim]Load the wallet: [/dim][cyan]mtcli hdwallet load --name {name}[/cyan]"
        )
        console.print(
            "3. [dim]Create a coldkey: [/dim][cyan]mtcli hdwallet create-coldkey --wallet {name} --name my_coldkey[/cyan]"
        )

    except Exception as e:
        console.print(f"[bold red]❌ Error creating wallet: {e}[/bold red]")


@hdwallet.command()
@click.option("--name", required=True, help="Name of the wallet to load")
@click.pass_context
def load(ctx, name: str):
    """📂 Load and decrypt an existing HD wallet"""
    wallet_manager = ctx.obj["wallet_manager"]
    wallet_utils = ctx.obj["wallet_utils"]

    try:
        password = getpass.getpass("🔐 Enter wallet password: ")

        # Load in both wallet_manager and wallet_utils for persistence
        if wallet_manager.load_wallet(name, password):
            # Also load in wallet_utils for persistent access
            wallet_utils._loaded_wallets[name] = True

            console.print(
                f"\n[bold green]✅ Wallet '{name}' loaded successfully![/bold green]"
            )

            # Show wallet info
            wallet_manager.display_wallet_info(name)

            console.print("\n[bold yellow]📋 Available commands:[/bold yellow]")
            console.print(
                "• [cyan]mtcli hdwallet create-coldkey[/cyan] - Create a new coldkey"
            )
            console.print(
                "• [cyan]mtcli hdwallet create-hotkey[/cyan] - Create a new hotkey"
            )
            console.print(
                "• [cyan]mtcli hdwallet export-key[/cyan] - Export private key"
            )
            console.print(
                "• [cyan]mtcli hdwallet info[/cyan] - Show wallet information"
            )

    except Exception as e:
        console.print(f"[bold red]❌ Error loading wallet: {e}[/bold red]")


@hdwallet.command()
@click.option("--wallet", required=True, help="Name of the wallet")
@click.option("--name", required=True, help="Name for the coldkey")
@click.option(
    "--index", type=int, help="Specific account index (auto-increment if not specified)"
)
@click.pass_context
def create_coldkey(ctx, wallet: str, name: str, index: Optional[int]):
    """🔑 Create a new coldkey (master account) from HD wallet"""
    wallet_utils = ctx.obj["wallet_utils"]

    try:
        # Auto-load wallet if not loaded
        if wallet not in wallet_utils._loaded_wallets:
            password = getpass.getpass(f"🔐 Password for wallet '{wallet}': ")
            if not wallet_utils.wallet_manager.load_wallet(wallet, password):
                console.print(
                    f"[bold red]❌ Failed to load wallet '{wallet}'[/bold red]"
                )
                return
            wallet_utils._loaded_wallets[wallet] = True

        coldkey_info = wallet_utils.wallet_manager.create_coldkey(wallet, name, index)

        console.print("\n[bold green]✅ Coldkey created successfully![/bold green]")
        console.print(f"[dim]Name: {coldkey_info['name']}[/dim]")
        console.print(f"[dim]Address: {coldkey_info['address']}[/dim]")
        console.print(f"[dim]Derivation Path: {coldkey_info['derivation_path']}[/dim]")

        console.print("\n[bold yellow]📋 Next steps:[/bold yellow]")
        console.print(
            f"• [cyan]mtcli hdwallet create-hotkey --wallet {wallet} --coldkey {name} --name my_hotkey[/cyan]"
        )
        console.print(
            f"• [cyan]mtcli hdwallet export-key --wallet {wallet} --coldkey {name}[/cyan]"
        )

    except Exception as e:
        console.print(f"[bold red]❌ Error creating coldkey: {e}[/bold red]")


@hdwallet.command()
@click.option("--wallet", required=True, help="Name of the wallet")
@click.option("--coldkey", required=True, help="Name of the parent coldkey")
@click.option("--name", required=True, help="Name for the hotkey")
@click.option(
    "--index", type=int, help="Specific address index (auto-increment if not specified)"
)
@click.pass_context
def create_hotkey(ctx, wallet: str, coldkey: str, name: str, index: Optional[int]):
    """🔥 Create a new hotkey derived from coldkey"""
    wallet_utils = ctx.obj["wallet_utils"]

    try:
        # Auto-load wallet if not loaded
        if wallet not in wallet_utils._loaded_wallets:
            password = getpass.getpass(f"🔐 Password for wallet '{wallet}': ")
            if not wallet_utils.wallet_manager.load_wallet(wallet, password):
                console.print(
                    f"[bold red]❌ Failed to load wallet '{wallet}'[/bold red]"
                )
                return
            wallet_utils._loaded_wallets[wallet] = True

        hotkey_info = wallet_utils.wallet_manager.create_hotkey(
            wallet, coldkey, name, index
        )

        console.print("\n[bold green]✅ Hotkey created successfully![/bold green]")
        console.print(f"[dim]Name: {hotkey_info['name']}[/dim]")
        console.print(f"[dim]Address: {hotkey_info['address']}[/dim]")
        console.print(f"[dim]Derivation Path: {hotkey_info['derivation_path']}[/dim]")

        console.print("\n[bold yellow]📋 Usage:[/bold yellow]")
        console.print(
            f"• [cyan]mtcli hdwallet export-key --wallet {wallet} --coldkey {coldkey} --hotkey {name}[/cyan]"
        )
        console.print(
            f"• [cyan]mtcli hdwallet get-account --wallet {wallet} --coldkey {coldkey} --hotkey {name}[/cyan]"
        )

    except Exception as e:
        console.print(f"[bold red]❌ Error creating hotkey: {e}[/bold red]")


@hdwallet.command()
@click.option("--wallet", required=True, help="Name of the wallet")
@click.option("--coldkey", required=True, help="Name of the coldkey")
@click.option("--hotkey", help="Name of the hotkey (leave empty for coldkey)")
@click.option("--yes", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def export_key(ctx, wallet: str, coldkey: str, hotkey: Optional[str], yes: bool):
    """🔐 Export private key for coldkey or hotkey"""
    wallet_utils = ctx.obj["wallet_utils"]

    try:
        # Auto-load wallet if not loaded
        if wallet not in wallet_utils._loaded_wallets:
            password = getpass.getpass(f"🔐 Password for wallet '{wallet}': ")
            if not wallet_utils.wallet_manager.load_wallet(wallet, password):
                console.print(
                    f"[bold red]❌ Failed to load wallet '{wallet}'[/bold red]"
                )
                return
            wallet_utils._loaded_wallets[wallet] = True

        # Security confirmation
        key_type = "hotkey" if hotkey else "coldkey"
        key_name = hotkey if hotkey else coldkey

        if not yes:
            try:
                if not Confirm.ask(
                    f"⚠️  Export private key for {key_type} '{key_name}'?"
                ):
                    console.print("[yellow]Export cancelled[/yellow]")
                    return
            except (EOFError, KeyboardInterrupt):
                console.print("\n[yellow]Export cancelled[/yellow]")
                return

        private_key = wallet_utils.wallet_manager.export_private_key(
            wallet, coldkey, hotkey
        )

        console.print(
            Panel.fit(
                f"[bold red]🔐 Private Key for {key_type} '{key_name}':[/bold red]\n\n"
                f"[bold white]{private_key}[/bold white]\n\n"
                f"[bold red]⚠️  CRITICAL: Keep this private key secure![/bold red]\n"
                f"[red]Anyone with this key can access your funds![/red]",
                title="🔑 Private Key Export",
                border_style="red",
            )
        )

    except Exception as e:
        console.print(f"[bold red]❌ Error exporting key: {e}[/bold red]")


@hdwallet.command()
@click.option("--wallet", required=True, help="Name of the wallet")
@click.option("--coldkey", required=True, help="Name of the coldkey")
@click.option("--hotkey", help="Name of the hotkey (leave empty for coldkey)")
@click.pass_context
def get_account(ctx, wallet: str, coldkey: str, hotkey: Optional[str]):
    """📋 Get account information for coldkey or hotkey"""
    wallet_utils = ctx.obj["wallet_utils"]

    try:
        # Auto-load wallet if not loaded
        if wallet not in wallet_utils._loaded_wallets:
            password = getpass.getpass(f"🔐 Password for wallet '{wallet}': ")
            if not wallet_utils.wallet_manager.load_wallet(wallet, password):
                console.print(
                    f"[bold red]❌ Failed to load wallet '{wallet}'[/bold red]"
                )
                return
            wallet_utils._loaded_wallets[wallet] = True

        account = wallet_utils.wallet_manager.get_account(wallet, coldkey, hotkey)

        key_type = "hotkey" if hotkey else "coldkey"
        key_name = hotkey if hotkey else coldkey

        address = str(account.address())
        if not address.startswith("0x"):
            address = f"0x{address}"

        public_key = str(account.public_key())

        console.print(
            Panel.fit(
                f"[bold cyan]📋 Account Information:[/bold cyan]\n\n"
                f"[bold]Type:[/bold] {key_type}\n"
                f"[bold]Name:[/bold] {key_name}\n"
                f"[bold]Address:[/bold] {address}\n"
                f"[bold]Public Key:[/bold] {public_key[:20]}...{public_key[-20:]}\n\n"
                f"[dim]Use this address to receive funds[/dim]",
                title="🏦 Account Info",
                border_style="cyan",
            )
        )

    except Exception as e:
        console.print(f"[bold red]❌ Error getting account: {e}[/bold red]")


@hdwallet.command()
@click.option(
    "--wallet", help="Name of specific wallet to show (shows all if not specified)"
)
@click.pass_context
def info(ctx, wallet: Optional[str]):
    """📊 Display wallet information"""
    wallet_manager = ctx.obj["wallet_manager"]

    if wallet:
        # Show specific wallet info
        wallet_manager.display_wallet_info(wallet)
    else:
        # Show all wallets
        wallets = wallet_manager.list_wallets()

        if not wallets:
            console.print("[yellow]No wallets found. Create one with:[/yellow]")
            console.print("[cyan]mtcli hdwallet create --name my_wallet[/cyan]")
            return

        table = Table(title="🏦 Available HD Wallets")
        table.add_column("Wallet Name", style="cyan")
        table.add_column("Status", style="yellow")

        for wallet_name in wallets:
            status = (
                "✅ Loaded"
                if wallet_name in wallet_manager.wallets
                else "⭕ Not loaded"
            )
            table.add_row(wallet_name, status)

        console.print(table)

        console.print("\n[bold yellow]📋 Commands:[/bold yellow]")
        console.print(
            "• [cyan]mtcli hdwallet load --name <wallet>[/cyan] - Load a wallet"
        )
        console.print(
            "• [cyan]mtcli hdwallet info --wallet <wallet>[/cyan] - Show wallet details"
        )


@hdwallet.command()
@click.option("--name", required=True, help="Name for the restored wallet")
@click.pass_context
def restore(ctx, name: str):
    """🔄 Restore HD wallet from mnemonic phrase"""
    wallet_manager = ctx.obj["wallet_manager"]

    try:
        console.print("[bold yellow]🔄 Wallet Restoration[/bold yellow]")
        console.print("Enter your mnemonic phrase (12-24 words):")

        mnemonic = Prompt.ask("Mnemonic", password=True)

        if not mnemonic or len(mnemonic.split()) < 12:
            console.print("[bold red]❌ Invalid mnemonic phrase![/bold red]")
            return

        password = getpass.getpass("🔐 Enter password to encrypt restored wallet: ")
        confirm_password = getpass.getpass("🔐 Confirm password: ")

        if password != confirm_password:
            console.print("[bold red]❌ Passwords do not match![/bold red]")
            return

        if wallet_manager.restore_wallet(name, mnemonic, password):
            console.print(
                f"\n[bold green]✅ Wallet '{name}' restored successfully![/bold green]"
            )

            # Auto-load the wallet
            if wallet_manager.load_wallet(name, password):
                console.print(
                    f"[bold green]✅ Wallet '{name}' loaded and ready to use![/bold green]"
                )

                console.print("\n[bold yellow]📋 Next steps:[/bold yellow]")
                console.print("1. [dim]Create coldkeys for your accounts[/dim]")
                console.print("2. [dim]Create hotkeys for operations[/dim]")
                console.print("3. [dim]Export keys as needed[/dim]")

    except Exception as e:
        console.print(f"[bold red]❌ Error restoring wallet: {e}[/bold red]")


@hdwallet.command()
@click.option("--wallet", required=True, help="Name of the loaded wallet")
@click.option("--name", required=True, help="Name for the imported account")
@click.pass_context
def import_key(ctx, wallet: str, name: str):
    """📥 Import account using private key"""
    wallet_manager = ctx.obj["wallet_manager"]

    try:
        console.print("[bold yellow]📥 Import Account by Private Key[/bold yellow]")

        private_key = Prompt.ask("Private Key (hex)", password=True)

        if not private_key or len(private_key) < 64:
            console.print("[bold red]❌ Invalid private key![/bold red]")
            return

        # Remove 0x prefix if present
        if private_key.startswith("0x"):
            private_key = private_key[2:]

        account_info = wallet_manager.import_account_by_private_key(
            wallet, private_key, name
        )

        console.print(
            f"\n[bold green]✅ Account '{name}' imported successfully![/bold green]"
        )
        console.print(f"[dim]Address: {account_info['address']}[/dim]")
        console.print(f"[dim]Note: This is an imported account (not HD-derived)[/dim]")

    except Exception as e:
        console.print(f"[bold red]❌ Error importing account: {e}[/bold red]")


@hdwallet.command()
@click.pass_context
def help(ctx):
    """❓ Show detailed help and examples"""
    console.print(
        Panel.fit(
            """[bold cyan]🏦 Aptos HD Wallet CLI Help[/bold cyan]

[bold yellow]📋 Basic Workflow:[/bold yellow]
1. [cyan]mtcli hdwallet create --name my_wallet[/cyan]
2. [cyan]mtcli hdwallet load --name my_wallet[/cyan]
3. [cyan]mtcli hdwallet create-coldkey --wallet my_wallet --name validator[/cyan]
4. [cyan]mtcli hdwallet create-hotkey --wallet my_wallet --coldkey validator --name operator[/cyan]

[bold yellow]🔑 Key Management:[/bold yellow]
• [cyan]export-key[/cyan] - Export private keys
• [cyan]get-account[/cyan] - Get account information
• [cyan]import-key[/cyan] - Import external private keys

[bold yellow]🔄 Wallet Operations:[/bold yellow]
• [cyan]restore[/cyan] - Restore from mnemonic
• [cyan]info[/cyan] - Show wallet information
• [cyan]help[/cyan] - Show this help

[bold yellow]📖 Examples:[/bold yellow]
[dim]# Create and setup a complete wallet[/dim]
[cyan]mtcli hdwallet create --name main_wallet --words 24[/cyan]
[cyan]mtcli hdwallet load --name main_wallet[/cyan]
[cyan]mtcli hdwallet create-coldkey --wallet main_wallet --name validator1[/cyan]
[cyan]mtcli hdwallet create-hotkey --wallet main_wallet --coldkey validator1 --name miner1[/cyan]
[cyan]mtcli hdwallet create-hotkey --wallet main_wallet --coldkey validator1 --name miner2[/cyan]

[dim]# Export keys for usage[/dim]
[cyan]mtcli hdwallet export-key --wallet main_wallet --coldkey validator1[/cyan]
[cyan]mtcli hdwallet export-key --wallet main_wallet --coldkey validator1 --hotkey miner1[/cyan]

[bold red]⚠️  Security Notes:[/bold red]
• Always backup your mnemonic phrase securely
• Keep private keys confidential
• Use strong passwords for wallet encryption
• Test with small amounts first""",
            title="🏦 HD Wallet CLI Help",
            border_style="cyan",
        )
    )


# Add to main CLI
def register_hd_wallet_commands(cli_group):
    """Register HD wallet commands with main CLI"""
    cli_group.add_command(hdwallet)


if __name__ == "__main__":
    hdwallet()

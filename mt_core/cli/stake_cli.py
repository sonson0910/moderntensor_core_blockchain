# sdk/cli/stake_cli.py
import click
from rich.console import Console
from rich.panel import Panel
from typing import Any, Optional
import json
import os

from moderntensor_aptos.mt_core.config.settings import settings, logger
from moderntensor_aptos.mt_core.core_client.contract_client import (
    stake_tokens,
    unstake_tokens,
    claim_rewards,
    get_staking_info,
)
from moderntensor_aptos.mt_core.account import Account
from moderntensor_aptos.mt_core.async_client import ModernTensorCoreClient
from moderntensor_aptos.mt_core.keymanager.wallet_manager import WalletManager
import asyncio


# ------------------------------------------------------------------------------
# STAKE COMMAND GROUP
# ------------------------------------------------------------------------------
@click.group()
def stake_cli():
    """
    🛡️ Commands for Core blockchain staking operations (stake, unstake, claim rewards). 🛡️
    """
    pass


# Helper function to load account from disk or HD wallet
def _load_account(
    account_name: str, password: str = None, base_dir: str = None
) -> Optional[Account]:
    console = Console()

    # Check if account_name is in HD wallet format
    if "." in account_name:
        parts = account_name.split(".")
        if len(parts) == 2:
            wallet_name, coldkey_name = parts
            hotkey_name = None
        elif len(parts) == 3:
            wallet_name, coldkey_name, hotkey_name = parts
        else:
            console.print(
                f"[bold red]Error:[/bold red] Invalid account format. Use 'wallet.coldkey' or 'wallet.coldkey.hotkey'"
            )
            return None

        # Load from HD wallet
        try:
            wm = WalletManager(base_dir=base_dir or "./wallets")
            account = wm.load_account(wallet_name, coldkey_name, hotkey_name, password)
            if account:
                console.print(
                    f"✅ HD Wallet account loaded: [blue]{account.address}[/blue]"
                )
            return account
        except Exception as e:
            console.print(f"[bold red]Error loading HD wallet account:[/bold red] {e}")
            logger.exception(f"Error loading HD wallet account {account_name}")
            return None

    # Traditional JSON account file loading
    try:
        if base_dir is None:
            base_dir = getattr(settings, "ACCOUNT_BASE_DIR", "./wallets")

        account_path = os.path.join(base_dir, f"{account_name}.json")
        if not os.path.exists(account_path):
            console.print(
                f"[bold red]Error:[/bold red] Account file {account_path} not found"
            )
            console.print(
                f"[bold yellow]Tip:[/bold yellow] Use HD wallet format: 'wallet.coldkey' or 'wallet.coldkey.hotkey'"
            )
            return None

        with open(account_path, "r") as f:
            account_data = json.load(f)
            private_key_hex = account_data["private_key"]
            account = Account.from_key(private_key_hex)
            console.print(
                f"✅ Traditional account loaded: [blue]{account.address}[/blue]"
            )
            return account
    except Exception as e:
        console.print(f"[bold red]Error loading traditional account:[/bold red] {e}")
        logger.exception(f"Error loading account {account_name}")
        return None


# Helper function to get Core Client
def _get_client(network: str) -> ModernTensorCoreClient:
    if network == "mainnet":
        return ModernTensorCoreClient("https://rpc.coredao.org")
    elif network == "testnet":
        return ModernTensorCoreClient("https://rpc.test.btcs.network")
    elif network == "devnet":
        return ModernTensorCoreClient("https://rpc.dev.btcs.network")
    else:
        return ModernTensorCoreClient("https://rpc.test.btcs.network")


# ------------------------------------------------------------------------------
# STAKE TOKENS COMMAND
# ------------------------------------------------------------------------------
@stake_cli.command("stake")
@click.option(
    "--account",
    help="Staker account name (HD wallet format: wallet.coldkey or wallet.coldkey.hotkey).",
)
@click.option("--address", help="Staker address (alternative to account name).")
@click.option("--password", help="Account password (will prompt if not provided).")
@click.option("--validator", required=True, help="Validator address to stake to.")
@click.option(
    "--amount",
    required=True,
    type=int,
    help="Amount to stake in wei (1 CORE = 10^18 wei).",
)
@click.option(
    "--network",
    default="testnet",
    type=click.Choice(["mainnet", "testnet", "devnet", "local"]),
    help="Select Core blockchain network.",
)
@click.option(
    "--base-dir",
    default="./wallets",
    help="Base directory where account files reside.",
)
@click.option("--yes", is_flag=True, help="Skip confirmation prompt.")
def stake_cmd(account, address, password, validator, amount, network, base_dir, yes):
    """
    ⛏️ Stake CORE tokens to a validator.

    Examples:
    \b
    • Stake using HD wallet:
      mtcore stake stake --account wallet.coldkey --validator 0x123... --amount 1000000000000000000

    • Stake using address directly:
      mtcore stake stake --address 0x123... --validator 0x456... --amount 1000000000000000000
    """
    console = Console()

    # Load account if provided
    account_obj = None
    if account:
        if password is None:
            password = click.prompt("Password", hide_input=True)
        account_obj = _load_account(account, password, base_dir)
        if not account_obj:
            return
    elif address:
        console.print(
            "[bold red]Error:[/bold red] Address-only mode requires account loading for signing transactions"
        )
        console.print(
            "[bold yellow]Tip:[/bold yellow] Use --account option with HD wallet format"
        )
        return
    else:
        console.print(
            "[bold red]Error:[/bold red] Either --account or --address must be provided"
        )
        return

    client = _get_client(network)

    # Format validator address
    if not validator.startswith("0x"):
        validator = f"0x{validator}"

    # Display staking info
    console.print(f"⛏️ Preparing staking transaction...")
    console.print(f"  Staker: [blue]{account_obj.address}[/blue]")
    console.print(f"  Validator: [green]{validator}[/green]")
    console.print(
        f"  Amount: [yellow]{amount:,}[/yellow] wei ({amount / 10**18:.8f} CORE)"
    )
    console.print(f"  Network: [yellow]{network.upper()}[/yellow]")

    if not yes:
        click.confirm(
            "Do you want to proceed with this staking transaction?", abort=True
        )

    try:
        console.print("⏳ Staking tokens...")
        tx_hash = asyncio.run(
            stake_tokens(
                client=client,
                staker=account_obj,
                validator_address=validator,
                amount=amount,
            )
        )

        console.print(
            f":heavy_check_mark: [bold green]Staking transaction submitted![/bold green]"
        )
        console.print(f"  Transaction hash: [bold blue]{tx_hash}[/bold blue]")

    except Exception as e:
        console.print(f"[bold red]Error staking tokens:[/bold red] {e}")
        logger.exception("Stake command failed")


# ------------------------------------------------------------------------------
# UNSTAKE TOKENS COMMAND
# ------------------------------------------------------------------------------
@stake_cli.command("unstake")
@click.option("--account", required=True, help="Account name.")
@click.option("--password", prompt=True, hide_input=True, help="Account password.")
@click.option(
    "--amount",
    required=True,
    type=int,
    help="Amount to unstake in wei (1 CORE = 10^18 wei).",
)
@click.option("--subnet-uid", type=int, help="Subnet ID to unstake from (optional).")
@click.option(
    "--contract-address",
    default=lambda: settings.APTOS_CONTRACT_ADDRESS,
    help="ModernTensor contract address.",
)
@click.option(
    "--network",
    default=lambda: settings.APTOS_NETWORK,
    type=click.Choice(["mainnet", "testnet", "devnet", "local"]),
    help="Select Aptos network.",
)
@click.option(
    "--base-dir",
    default=lambda: settings.ACCOUNT_BASE_DIR,
    help="Base directory where account files reside.",
)
@click.option("--yes", is_flag=True, help="Skip confirmation prompt.")
def unstake_cmd(
    account, password, amount, subnet_uid, contract_address, network, base_dir, yes
):
    """
    🔙 Unstake tokens from the ModernTensor contract.
    """
    console = Console()
    account_obj = _load_account(account, password, base_dir)
    if not account_obj:
        return

    client = _get_client(network)

    # Display information about the unstake
    console.print(
        f"❓ Attempting to unstake [yellow]{amount}[/yellow] wei from account [blue]{account_obj.address}[/blue]"
    )
    if subnet_uid is not None:
        console.print(f"  Subnet: [cyan]{subnet_uid}[/cyan]")

    if not yes:
        click.confirm("This will submit a transaction. Proceed?", abort=True)

    console.print("⏳ Submitting unstaking transaction...")
    try:
        # Call the unstake_tokens function
        tx_hash = asyncio.run(
            unstake_tokens(
                client=client,
                account=account_obj,
                contract_address=contract_address,
                amount=amount,
                subnet_uid=subnet_uid,
            )
        )

        if tx_hash:
            console.print(
                f":heavy_check_mark: [bold green]Unstaking transaction submitted![/bold green]"
            )
            console.print(f"  Transaction hash: [bold blue]{tx_hash}[/bold blue]")
        else:
            console.print(
                ":cross_mark: [bold red]Unstaking failed. Check logs for details.[/bold red]"
            )
    except Exception as e:
        console.print(f":cross_mark: [bold red]Error during unstaking:[/bold red] {e}")
        logger.exception("Unstaking command failed")


# ------------------------------------------------------------------------------
# CLAIM REWARDS COMMAND
# ------------------------------------------------------------------------------
@stake_cli.command("claim")
@click.option("--account", required=True, help="Account name.")
@click.option("--password", prompt=True, hide_input=True, help="Account password.")
@click.option(
    "--subnet-uid", type=int, help="Subnet ID to claim rewards from (optional)."
)
@click.option(
    "--contract-address",
    default=lambda: settings.APTOS_CONTRACT_ADDRESS,
    help="ModernTensor contract address.",
)
@click.option(
    "--network",
    default=lambda: settings.APTOS_NETWORK,
    type=click.Choice(["mainnet", "testnet", "devnet", "local"]),
    help="Select Aptos network.",
)
@click.option(
    "--base-dir",
    default=lambda: settings.ACCOUNT_BASE_DIR,
    help="Base directory where account files reside.",
)
@click.option("--yes", is_flag=True, help="Skip confirmation prompt.")
def claim_cmd(account, password, subnet_uid, contract_address, network, base_dir, yes):
    """
    💰 Claim staking rewards from the ModernTensor contract.
    """
    console = Console()
    account_obj = _load_account(account, password, base_dir)
    if not account_obj:
        return

    client = _get_client(network)

    # Display information about the claim
    console.print(
        f"❓ Attempting to claim rewards for account [blue]{account_obj.address}[/blue]"
    )
    if subnet_uid is not None:
        console.print(f"  Subnet: [cyan]{subnet_uid}[/cyan]")

    if not yes:
        click.confirm("This will submit a transaction. Proceed?", abort=True)

    console.print("⏳ Submitting claim transaction...")
    try:
        # Call the claim_rewards function
        tx_hash = asyncio.run(
            claim_rewards(
                client=client,
                account=account_obj,
                contract_address=contract_address,
                subnet_uid=subnet_uid,
            )
        )

        if tx_hash:
            console.print(
                f":heavy_check_mark: [bold green]Claim transaction submitted![/bold green]"
            )
            console.print(f"  Transaction hash: [bold blue]{tx_hash}[/bold blue]")
        else:
            console.print(
                ":cross_mark: [bold red]Claim failed. Check logs for details.[/bold red]"
            )
    except Exception as e:
        console.print(f":cross_mark: [bold red]Error during claim:[/bold red] {e}")
        logger.exception("Claim command failed")


# ------------------------------------------------------------------------------
# STAKING INFO COMMAND
# ------------------------------------------------------------------------------
@stake_cli.command("info")
@click.option("--account", help="Account name (required if --address not provided).")
@click.option("--address", help="Alternative address to check (instead of account).")
@click.option("--subnet-uid", type=int, help="Subnet ID to get info from (optional).")
@click.option(
    "--contract-address",
    default=lambda: settings.APTOS_CONTRACT_ADDRESS,
    help="ModernTensor contract address.",
)
@click.option(
    "--network",
    default=lambda: settings.APTOS_NETWORK,
    type=click.Choice(["mainnet", "testnet", "devnet", "local"]),
    help="Select Aptos network.",
)
@click.option(
    "--base-dir",
    default=lambda: settings.ACCOUNT_BASE_DIR,
    help="Base directory where account files reside.",
)
def info_cmd(account, address, subnet_uid, contract_address, network, base_dir):
    """
    ℹ️ Display staking information for an account.
    """
    console = Console()
    client = _get_client(network)

    # Validate inputs
    if not account and not address:
        console.print(
            "[bold red]Error:[/bold red] Either --account or --address must be provided"
        )
        return

    # Determine the address to check
    query_address = None
    if address:
        query_address = address
    else:
        # Try to load account using HD wallet or legacy method
        try:
            # Try HD wallet format first
            if "." in account:
                parts = account.split(".")
                if len(parts) == 2:
                    wallet_name, coldkey_name = parts
                    hotkey_name = None
                elif len(parts) == 3:
                    wallet_name, coldkey_name, hotkey_name = parts
                else:
                    raise ValueError("Invalid account format")

                console.print(
                    f"🔑 Loading HD wallet for address lookup: {wallet_name}.{coldkey_name}"
                    + (f".{hotkey_name}" if hotkey_name else "")
                )
                wm = WalletManager(base_dir=base_dir)

                # Get address from HD wallet without loading full account
                accounts = wm.list_available_accounts(wallet_name)
                if wallet_name in accounts and "accounts" in accounts[wallet_name]:
                    wallet_accounts = accounts[wallet_name]["accounts"]
                    if coldkey_name in wallet_accounts:
                        if hotkey_name:
                            # For hotkey, we need to derive the address
                            account_obj = wm.load_account(
                                wallet_name=wallet_name,
                                coldkey_name=coldkey_name,
                                hotkey_name=hotkey_name,
                                password="dummy",  # Won't be used for address lookup
                            )
                            if account_obj:
                                query_address = account_obj.address
                        else:
                            # For coldkey, get address from metadata
                            query_address = wallet_accounts[coldkey_name]["address"]

                if query_address:
                    console.print(
                        f"✅ HD wallet address found: [blue]{query_address}[/blue]"
                    )
                else:
                    console.print(f"[red]Failed to get address from HD wallet[/red]")
                    return
            else:
                raise ValueError("Not HD wallet format, trying legacy")

        except Exception:
            # Fallback to legacy account loading
            account_path = os.path.join(base_dir, f"{account}.json")
            if not os.path.exists(account_path):
                console.print(
                    f"[bold red]Error:[/bold red] Account file {account_path} not found"
                )
                console.print(
                    f"[yellow]💡 Use HD wallet format: 'wallet_name.coldkey_name' or 'wallet_name.coldkey_name.hotkey_name'[/yellow]"
                )
                console.print(
                    f"[yellow]💡 Example: test_real_wallet.validator_main[/yellow]"
                )
                return

            try:
                with open(account_path, "r") as f:
                    account_data = json.load(f)
                    query_address = account_data.get("address")
                    if not query_address:
                        console.print(
                            f"[bold red]Error:[/bold red] Could not determine address from account file"
                        )
                        return
                    console.print(
                        f"✅ Legacy account address found: [blue]{query_address}[/blue]"
                    )
            except Exception as e:
                console.print(f"[bold red]Error loading account:[/bold red] {e}")
                return

    console.print(
        f"⏳ Fetching staking info for address [blue]{query_address}[/blue]..."
    )
    if subnet_uid is not None:
        console.print(f"  Subnet: [cyan]{subnet_uid}[/cyan]")

    try:
        # Call the get_staking_info function
        info = asyncio.run(
            get_staking_info(
                client=client,
                account_address=query_address,
                contract_address=contract_address,
                subnet_uid=subnet_uid,
            )
        )

        if info:
            # Create a nice panel with the info
            info_text = [
                f"[bold]Staked Amount:[/bold] [yellow]{info['staked_amount'] / 10**18:.8f}[/yellow] CORE",
                f"[bold]Pending Rewards:[/bold] [green]{info['pending_rewards'] / 10**18:.8f}[/green] CORE",
                f"[bold]Staking Period:[/bold] {info['staking_period']} seconds",
                f"[bold]Last Claim:[/bold] {info['last_claim_time']} seconds ago",
            ]

            if subnet_uid is not None:
                info_text.append(f"[bold]Subnet:[/bold] [cyan]{subnet_uid}[/cyan]")

            console.print(
                Panel(
                    "\n".join(info_text),
                    title=f"[bold]Staking Info for {query_address}[/bold]",
                    border_style="blue",
                )
            )
        else:
            console.print(
                "[bold yellow]No staking information found for this address[/bold yellow]"
            )
    except Exception as e:
        console.print(f"[bold red]Error retrieving staking info:[/bold red] {e}")
        logger.exception("Info command failed")

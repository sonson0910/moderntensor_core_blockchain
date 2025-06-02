# sdk/cli/stake_cli.py
import click
from rich.console import Console
from rich.panel import Panel
from typing import Any, Optional
import json
import os

from mt_aptos.config.settings import settings, logger
from mt_aptos.aptos import (
    stake_tokens,
    unstake_tokens,
    claim_rewards,
    get_staking_info
)
from mt_aptos.account import Account, AccountAddress
from mt_aptos.async_client import RestClient
import asyncio


# ------------------------------------------------------------------------------
# STAKE COMMAND GROUP
# ------------------------------------------------------------------------------
@click.group()
def stake_cli():
    """
    🛡️ Commands for Aptos staking operations (stake, unstake, claim rewards). 🛡️
    """
    pass


# Helper function to load account from disk
def _load_account(account_name: str, password: str, base_dir: str) -> Optional[Account]:
    console = Console()
    try:
        account_path = os.path.join(base_dir, f"{account_name}.json")
        if not os.path.exists(account_path):
            console.print(f"[bold red]Error:[/bold red] Account file {account_path} not found")
            return None
            
        # In a real implementation, you would decrypt the account file with the password
        # For now, we'll just load the account from disk
        with open(account_path, "r") as f:
            account_data = json.load(f)
            # This is simplified - in a real implementation, you'd need to decrypt private keys
            private_key_bytes = bytes.fromhex(account_data["private_key"])
            account = Account.load(private_key_bytes)
            console.print(f"✅ Account loaded: [blue]{account.address().hex()}[/blue]")
            return account
    except Exception as e:
        console.print(f"[bold red]Error loading account:[/bold red] {e}")
        logger.exception(f"Error loading account {account_name}")
        return None


# Helper function to get RestClient
def _get_client(network: str) -> RestClient:
    if network == "mainnet":
        return RestClient("https://fullnode.mainnet.aptoslabs.com/v1")
    elif network == "testnet":
        return RestClient("https://fullnode.testnet.aptoslabs.com/v1")
    elif network == "devnet":
        return RestClient("https://fullnode.devnet.aptoslabs.com/v1")
    else:
        # Default to local node
        return RestClient("http://localhost:8080/v1")


# ------------------------------------------------------------------------------
# STAKE TOKENS COMMAND
# ------------------------------------------------------------------------------
@stake_cli.command("stake")
@click.option("--account", required=True, help="Account name to use for staking.")
@click.option("--password", prompt=True, hide_input=True, help="Account password.")
@click.option("--amount", required=True, type=int, help="Amount to stake in octas (1 APT = 10^8 octas).")
@click.option("--subnet-uid", type=int, help="Subnet ID to stake in (optional).")
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
def stake_cmd(account, password, amount, subnet_uid, contract_address, network, base_dir, yes):
    """
    📜 Stake tokens in the ModernTensor contract.
    """
    console = Console()
    account_obj = _load_account(account, password, base_dir)
    if not account_obj:
        return

    client = _get_client(network)
    
    # Display information about the stake
    console.print(f"❓ Attempting to stake [yellow]{amount}[/yellow] octas from account [blue]{account_obj.address().hex()}[/blue]")
    if subnet_uid is not None:
        console.print(f"  Subnet: [cyan]{subnet_uid}[/cyan]")
    
    if not yes:
        click.confirm("This will submit a transaction. Proceed?", abort=True)
    
    console.print("⏳ Submitting staking transaction...")
    try:
        # Call the stake_tokens function
        tx_hash = asyncio.run(stake_tokens(
            client=client,
            account=account_obj,
            contract_address=contract_address,
            amount=amount,
            subnet_uid=subnet_uid
        ))
        
        if tx_hash:
            console.print(f":heavy_check_mark: [bold green]Staking transaction submitted![/bold green]")
            console.print(f"  Transaction hash: [bold blue]{tx_hash}[/bold blue]")
        else:
            console.print(":cross_mark: [bold red]Staking failed. Check logs for details.[/bold red]")
    except Exception as e:
        console.print(f":cross_mark: [bold red]Error during staking:[/bold red] {e}")
        logger.exception("Staking command failed")


# ------------------------------------------------------------------------------
# UNSTAKE TOKENS COMMAND
# ------------------------------------------------------------------------------
@stake_cli.command("unstake")
@click.option("--account", required=True, help="Account name.")
@click.option("--password", prompt=True, hide_input=True, help="Account password.")
@click.option("--amount", required=True, type=int, help="Amount to unstake in octas (1 APT = 10^8 octas).")
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
def unstake_cmd(account, password, amount, subnet_uid, contract_address, network, base_dir, yes):
    """
    🔙 Unstake tokens from the ModernTensor contract.
    """
    console = Console()
    account_obj = _load_account(account, password, base_dir)
    if not account_obj:
        return

    client = _get_client(network)
    
    # Display information about the unstake
    console.print(f"❓ Attempting to unstake [yellow]{amount}[/yellow] octas from account [blue]{account_obj.address().hex()}[/blue]")
    if subnet_uid is not None:
        console.print(f"  Subnet: [cyan]{subnet_uid}[/cyan]")
    
    if not yes:
        click.confirm("This will submit a transaction. Proceed?", abort=True)
    
    console.print("⏳ Submitting unstaking transaction...")
    try:
        # Call the unstake_tokens function
        tx_hash = asyncio.run(unstake_tokens(
            client=client,
            account=account_obj,
            contract_address=contract_address,
            amount=amount,
            subnet_uid=subnet_uid
        ))
        
        if tx_hash:
            console.print(f":heavy_check_mark: [bold green]Unstaking transaction submitted![/bold green]")
            console.print(f"  Transaction hash: [bold blue]{tx_hash}[/bold blue]")
        else:
            console.print(":cross_mark: [bold red]Unstaking failed. Check logs for details.[/bold red]")
    except Exception as e:
        console.print(f":cross_mark: [bold red]Error during unstaking:[/bold red] {e}")
        logger.exception("Unstaking command failed")


# ------------------------------------------------------------------------------
# CLAIM REWARDS COMMAND
# ------------------------------------------------------------------------------
@stake_cli.command("claim")
@click.option("--account", required=True, help="Account name.")
@click.option("--password", prompt=True, hide_input=True, help="Account password.")
@click.option("--subnet-uid", type=int, help="Subnet ID to claim rewards from (optional).")
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
    console.print(f"❓ Attempting to claim rewards for account [blue]{account_obj.address().hex()}[/blue]")
    if subnet_uid is not None:
        console.print(f"  Subnet: [cyan]{subnet_uid}[/cyan]")
    
    if not yes:
        click.confirm("This will submit a transaction. Proceed?", abort=True)
    
    console.print("⏳ Submitting claim transaction...")
    try:
        # Call the claim_rewards function
        tx_hash = asyncio.run(claim_rewards(
            client=client,
            account=account_obj,
            contract_address=contract_address,
            subnet_uid=subnet_uid
        ))
        
        if tx_hash:
            console.print(f":heavy_check_mark: [bold green]Claim transaction submitted![/bold green]")
            console.print(f"  Transaction hash: [bold blue]{tx_hash}[/bold blue]")
        else:
            console.print(":cross_mark: [bold red]Claim failed. Check logs for details.[/bold red]")
    except Exception as e:
        console.print(f":cross_mark: [bold red]Error during claim:[/bold red] {e}")
        logger.exception("Claim command failed")


# ------------------------------------------------------------------------------
# STAKING INFO COMMAND
# ------------------------------------------------------------------------------
@stake_cli.command("info")
@click.option("--account", required=True, help="Account name.")
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
    
    # Determine the address to check
    query_address = None
    if address:
        query_address = address
    else:
        # Load account only to get the address
        account_path = os.path.join(base_dir, f"{account}.json")
        if not os.path.exists(account_path):
            console.print(f"[bold red]Error:[/bold red] Account file {account_path} not found")
            return
            
        try:
            with open(account_path, "r") as f:
                account_data = json.load(f)
                query_address = account_data.get("address")
                if not query_address:
                    console.print(f"[bold red]Error:[/bold red] Could not determine address from account file")
                    return
        except Exception as e:
            console.print(f"[bold red]Error loading account:[/bold red] {e}")
            return
    
    console.print(f"⏳ Fetching staking info for address [blue]{query_address}[/blue]...")
    if subnet_uid is not None:
        console.print(f"  Subnet: [cyan]{subnet_uid}[/cyan]")
    
    try:
        # Call the get_staking_info function
        info = asyncio.run(get_staking_info(
            client=client,
            account_address=query_address,
            contract_address=contract_address,
            subnet_uid=subnet_uid
        ))
        
        if info:
            # Create a nice panel with the info
            info_text = [
                f"[bold]Staked Amount:[/bold] [yellow]{info['staked_amount'] / 100_000_000:.8f}[/yellow] APT",
                f"[bold]Pending Rewards:[/bold] [green]{info['pending_rewards'] / 100_000_000:.8f}[/green] APT",
                f"[bold]Staking Period:[/bold] {info['staking_period']} seconds",
                f"[bold]Last Claim:[/bold] {info['last_claim_time']} seconds ago"
            ]
            
            if subnet_uid is not None:
                info_text.append(f"[bold]Subnet:[/bold] [cyan]{subnet_uid}[/cyan]")
            
            console.print(Panel(
                "\n".join(info_text),
                title=f"[bold]Staking Info for {query_address}[/bold]",
                border_style="blue"
            ))
        else:
            console.print("[bold yellow]No staking information found for this address[/bold yellow]")
    except Exception as e:
        console.print(f"[bold red]Error retrieving staking info:[/bold red] {e}")
        logger.exception("Info command failed")

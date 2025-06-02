# file: sdk/cli/tx_cli.py
import click
import os
import json
from typing import Optional
import asyncio

from rich.console import Console
from rich.table import Table

from mt_aptos.account import Account
from mt_aptos.async_client import RestClient

from mt_aptos.config.settings import settings, logger
from mt_aptos.aptos import (
    send_coin, 
    send_token, 
    submit_transaction,
    get_transaction_details, 
    get_account_transactions
)


# ------------------------------------------------------------------------------
# TRANSACTION COMMAND GROUP
# ------------------------------------------------------------------------------
@click.group()
def tx_cli():
    """
    💸 Commands for creating and sending transactions on Aptos. 💸
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
# SEND TRANSACTION COMMAND
# ------------------------------------------------------------------------------
@tx_cli.command("send")
@click.option("--account", required=True, help="Sender account name.")
@click.option("--password", prompt=True, hide_input=True, help="Sender account password.")
@click.option("--to", required=True, help="Recipient address.")
@click.option("--amount", required=True, type=int, help="Amount to send in octas (1 APT = 10^8 octas).")
@click.option(
    "--token", 
    default="apt", 
    help="Token to send. Use 'apt' for native Aptos coin or 'token_address::token_name::token_name' for other tokens."
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
def send_cmd(account, password, to, amount, token, network, base_dir, yes):
    """
    ➡️ Send APT or other tokens to an address.
    """
    console = Console()
    account_obj = _load_account(account, password, base_dir)
    if not account_obj:
        return

    client = _get_client(network)

    # Format recipient address
    if not to.startswith("0x"):
        to = f"0x{to}"

    # Display transaction info
    console.print(f"🚀 Preparing transaction...")
    console.print(f"  Sender: [blue]{account_obj.address().hex()}[/blue]")
    console.print(f"  Amount: [yellow]{amount:,}[/yellow] octas ({amount / 100_000_000:.8f} APT)")
    console.print(f"  To: [green]{to}[/green]")
    console.print(f"  Network: [yellow]{network.upper()}[/yellow]")
    
    if not yes:
        click.confirm("Do you want to proceed with this transaction?", abort=True)
    
    try:
        if token.lower() == "apt":
            console.print("⏳ Sending APT...")
            tx_hash = asyncio.run(send_coin(
                client=client,
                sender=account_obj,
                recipient_address=to,
                amount=amount
            ))
        else:
            console.print(f"⏳ Sending token {token}...")
            # Parse token info from format: address::module::name
            token_parts = token.split("::")
            if len(token_parts) != 3:
                console.print("[bold red]Error:[/bold red] Invalid token format. Use 'address::module::name'")
                return
            
            token_address, token_module, token_name = token_parts
            
            tx_hash = asyncio.run(send_token(
                client=client,
                sender=account_obj,
                recipient_address=to,
                token_address=token_address,
                token_name=token_name, 
                amount=amount
            ))
        
        console.print(f":heavy_check_mark: [bold green]Transaction submitted![/bold green]")
        console.print(f"  Transaction hash: [bold blue]{tx_hash}[/bold blue]")
        
    except Exception as e:
        console.print(f"[bold red]Error sending transaction:[/bold red] {e}")
        logger.exception("Send command failed")


# ------------------------------------------------------------------------------
# GET TRANSACTION COMMAND
# ------------------------------------------------------------------------------
@tx_cli.command("get")
@click.option("--hash", required=True, help="Transaction hash to lookup.")
@click.option(
    "--network",
    default=lambda: settings.APTOS_NETWORK,
    type=click.Choice(["mainnet", "testnet", "devnet", "local"]),
    help="Select Aptos network.",
)
def get_tx_cmd(hash, network):
    """
    🔍 Get details about a transaction by hash.
    """
    console = Console()
    client = _get_client(network)
    
    # Format hash
    if not hash.startswith("0x"):
        hash = f"0x{hash}"
    
    console.print(f"⏳ Looking up transaction [blue]{hash}[/blue]...")
    
    try:
        tx_details = asyncio.run(get_transaction_details(client=client, txn_hash=hash))
        
        if "error" in tx_details:
            console.print(f"[bold red]Error:[/bold red] {tx_details['error']}")
            return
            
        # Display transaction details in a nice table
        table = Table(title=f"Transaction {hash}", border_style="blue")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="green")
        
        # Add basic transaction info
        table.add_row("Version", str(tx_details.get("version", "N/A")))
        table.add_row("Status", tx_details.get("success", False) and "[green]Success[/green]" or "[red]Failed[/red]")
        table.add_row("Type", tx_details.get("type", "N/A"))
        table.add_row("Timestamp", tx_details.get("timestamp", "N/A"))
        table.add_row("Sender", tx_details.get("sender", "N/A"))
        
        # Add gas info
        table.add_row("Gas Used", str(tx_details.get("gas_used", "N/A")))
        table.add_row("Gas Unit Price", str(tx_details.get("gas_unit_price", "N/A")))
        table.add_row("Max Gas", str(tx_details.get("max_gas_amount", "N/A")))
        
        console.print(table)
        
        # If it's a function call, show details
        if "payload" in tx_details and tx_details["payload"].get("type") == "entry_function_payload":
            payload = tx_details["payload"]
            function = payload.get("function", "N/A")
            console.print(f"\n[bold]Function called:[/bold] [yellow]{function}[/yellow]")
            
            if "arguments" in payload and payload["arguments"]:
                console.print("\n[bold]Arguments:[/bold]")
                for i, arg in enumerate(payload["arguments"]):
                    console.print(f"  {i+1}. [cyan]{arg}[/cyan]")
                    
        # If there are events, show them
        if "events" in tx_details and tx_details["events"]:
            console.print("\n[bold]Events:[/bold]")
            for i, event in enumerate(tx_details["events"]):
                console.print(f"\n  [bold cyan]Event {i+1}:[/bold cyan] {event.get('type', 'Unknown')}")
                if "data" in event:
                    for key, value in event["data"].items():
                        console.print(f"    [green]{key}:[/green] {value}")
        
    except Exception as e:
        console.print(f"[bold red]Error retrieving transaction:[/bold red] {e}")
        logger.exception("Get transaction command failed")


# ------------------------------------------------------------------------------
# LIST TRANSACTIONS COMMAND
# ------------------------------------------------------------------------------
@tx_cli.command("list")
@click.option("--address", required=True, help="Account address to list transactions for.")
@click.option("--limit", default=10, type=int, help="Maximum number of transactions to show.")
@click.option(
    "--network",
    default=lambda: settings.APTOS_NETWORK,
    type=click.Choice(["mainnet", "testnet", "devnet", "local"]),
    help="Select Aptos network.",
)
def list_tx_cmd(address, limit, network):
    """
    📋 List transactions for an account.
    """
    console = Console()
    client = _get_client(network)
    
    # Format address
    if not address.startswith("0x"):
        address = f"0x{address}"
    
    console.print(f"⏳ Fetching transactions for [blue]{address}[/blue]...")
    
    try:
        transactions = asyncio.run(get_account_transactions(
            client=client,
            address=address,
            limit=limit
        ))
        
        if not transactions:
            console.print(f"No transactions found for address {address}")
            return
            
        # Display transactions in a table
        table = Table(title=f"Transactions for {address}", border_style="blue")
        table.add_column("Version", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Timestamp", style="dim")
        table.add_column("Status", style="green")
        table.add_column("Hash", style="blue")
        
        for tx in transactions:
            status = tx.get("success", False) and "[green]Success[/green]" or "[red]Failed[/red]"
            hash = tx.get("hash", "N/A")
            tx_type = tx.get("type", "N/A")
            version = str(tx.get("version", "N/A"))
            timestamp = tx.get("timestamp", "N/A")
            
            table.add_row(version, tx_type, timestamp, status, hash)
            
        console.print(table)
        
    except Exception as e:
        console.print(f"[bold red]Error listing transactions:[/bold red] {e}")
        logger.exception("List transactions command failed")

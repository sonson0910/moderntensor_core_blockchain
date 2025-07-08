# sdk/cli/query_cli.py
"""
Command-line interface for querying Core blockchain data.

This module provides commands to query account information, transaction details,
network status, and other blockchain-related data from Core blockchain.
"""

import click
import asyncio
from typing import Dict, Any, List, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from moderntensor_aptos.mt_core.async_client import ModernTensorCoreClient
from moderntensor_aptos.mt_core.account import Account
from moderntensor_aptos.mt_core.config.settings import settings, logger
from moderntensor_aptos.mt_core.core_client.contract_client import (
    get_all_miners,
    get_all_validators,
)


@click.group()
def query_cli():
    """
    🔍 Commands for querying Core blockchain data.
    """
    pass


@query_cli.command("account")
@click.option(
    "--address", required=True, help="Core blockchain account address to query."
)
@click.option(
    "--node-url",
    help="Custom Core node URL (uses settings.CORE_NODE_URL by default).",
)
@click.option(
    "--network",
    type=click.Choice(["mainnet", "testnet", "devnet", "local"]),
    default="testnet",
    help="Select Core blockchain network.",
)
def query_account_cmd(address, node_url, network):
    """
    📊 Query Core blockchain account balance and details.

    Shows account balance and other details for a given address.
    """
    console = Console()
    console.print(f"⏳ Querying account [blue]{address}[/blue]...")

    # Format address if needed
    if not address.startswith("0x"):
        address = f"0x{address}"

    async def query_account():
        try:
            # Determine node URL
            if not node_url:
                if network == "mainnet":
                    node_url_final = "https://rpc.coredao.org"
                elif network == "testnet":
                    node_url_final = "https://rpc.test.btcs.network"
                elif network == "devnet":
                    node_url_final = "https://rpc.dev.btcs.network"
                else:  # local
                    node_url_final = "https://rpc.test.btcs.network"
            else:
                node_url_final = node_url

            # Create Core client and get account info
            client = ModernTensorCoreClient(node_url_final)

            # Get CORE balance (in wei)
            balance_wei = await client.get_balance(address)
            balance_core = balance_wei / 10**18  # Convert wei to CORE

            # Display account information
            console.print(
                Panel(
                    f"[bold]Address:[/bold] [blue]{address}[/blue]\n"
                    f"[bold]CORE Balance:[/bold] [green]{balance_core:.8f} CORE[/green] ([yellow]{balance_wei:,} wei[/yellow])\n"
                    f"[bold]Network:[/bold] {network}\n"
                    f"[bold]Node URL:[/bold] {node_url_final}\n",
                    title="Account Information",
                    expand=False,
                )
            )

            # Check if account is funded
            if balance_core > 0:
                console.print(
                    "✅ [bold green]Account is funded and ready to use![/bold green]"
                )
            else:
                console.print("❌ [bold red]Account has no CORE balance[/bold red]")
                console.print(
                    f"[yellow]To fund this account on {network}, use the faucet:[/yellow]"
                )
                if network == "testnet":
                    console.print(f"[cyan]https://faucet.test.btcs.network[/cyan]")

        except Exception as e:
            console.print(f"❌ [bold red]Error:[/bold red] {e}")
            logger.exception(e)

    asyncio.run(query_account())


@query_cli.command("network")
@click.option(
    "--node-url", help="Custom Core node URL (uses settings.CORE_NODE_URL by default)."
)
@click.option(
    "--network",
    type=click.Choice(["mainnet", "testnet", "devnet", "local"]),
    default="testnet",
    help="Select Core blockchain network.",
)
def query_network_cmd(node_url, network):
    """
    📡 Query Core blockchain network information.

    Shows network health, chain ID, and other ledger information.
    """
    console = Console()
    console.print(f"⏳ Querying Core {network} network status...")

    async def query_network():
        try:
            # Determine node URL
            if not node_url:
                if network == "mainnet":
                    node_url_final = "https://rpc.coredao.org"
                elif network == "testnet":
                    node_url_final = "https://rpc.test.btcs.network"
                elif network == "devnet":
                    node_url_final = "https://rpc.dev.btcs.network"
                else:  # local
                    node_url_final = "https://rpc.test.btcs.network"
            else:
                node_url_final = node_url

            # Create client and get network info
            client = ModernTensorCoreClient(node_url_final)

            # Get chain ID and latest block
            chain_id = await client.get_chain_id()
            latest_block = await client.get_latest_block_number()

            # Display network information
            console.print(
                Panel(
                    f"[bold]Network:[/bold] [green]{network}[/green]\n"
                    f"[bold]Chain ID:[/bold] {chain_id}\n"
                    f"[bold]Latest Block:[/bold] {latest_block}\n"
                    f"[bold]Node URL:[/bold] {node_url_final}\n",
                    title="Core Blockchain Network Status",
                    expand=False,
                )
            )

        except Exception as e:
            console.print(f"❌ [bold red]Error:[/bold red] {e}")
            logger.exception(e)

    asyncio.run(query_network())

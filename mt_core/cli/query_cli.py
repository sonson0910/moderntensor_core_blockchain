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
from rich.tree import Tree
from rich.json import JSON
from web3 import Web3

from moderntensor_aptos.mt_core.async_client import CoreAsyncClient
from moderntensor_aptos.mt_core.account import Account
from moderntensor_aptos.mt_core.config.settings import settings, logger
from moderntensor_aptos.mt_core.core_client.contract_client import (
    get_all_miners,
    get_all_validators,
    ModernTensorCoreClient as MTCoreClient,
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


@query_cli.command("subnet")
@click.option("--subnet-id", required=True, type=int, help="Subnet ID to query.")
@click.option(
    "--contract-address",
    help="ModernTensor contract address (uses settings.CORE_CONTRACT_ADDRESS by default).",
)
@click.option(
    "--node-url", help="Custom Core node URL (uses settings.CORE_NODE_URL by default)."
)
@click.option(
    "--network",
    type=click.Choice(["mainnet", "testnet", "devnet", "local"]),
    default="testnet",
    help="Select Core blockchain network.",
)
@click.option(
    "--format",
    type=click.Choice(["table", "json", "tree"]),
    default="table",
    help="Output format.",
)
def query_subnet_cmd(subnet_id, contract_address, node_url, network, format):
    """
    🔍 Query subnet information using getSubnet function.

    Displays complete subnet data including static, dynamic, miners, and validators.
    """
    console = Console()
    console.print(f"⏳ Querying subnet [blue]{subnet_id}[/blue]...")

    async def query_subnet():
        try:
            # Determine node URL
            if not node_url:
                if network == "mainnet":
                    node_url_final = "https://rpc.coredao.org"
                elif network == "testnet":
                    node_url_final = "https://rpc.test2.btcs.network"
                elif network == "devnet":
                    node_url_final = "https://rpc.dev.btcs.network"
                else:  # local
                    node_url_final = "https://rpc.test2.btcs.network"
            else:
                node_url_final = node_url

            # Use contract address from settings if not provided
            if not contract_address:
                contract_address_final = settings.CORE_CONTRACT_ADDRESS
            else:
                contract_address_final = contract_address

            console.print(f"📍 Contract: [cyan]{contract_address_final}[/cyan]")
            console.print(f"🌐 Network: [green]{network}[/green] ({node_url_final})")

            # Create Web3 client
            w3 = Web3(Web3.HTTPProvider(node_url_final))

            if not w3.is_connected():
                console.print(
                    "❌ [bold red]Failed to connect to Core network[/bold red]"
                )
                return

            # Create ModernTensor client
            mt_client = MTCoreClient(w3=w3, contract_address=contract_address_final)

            # Call getSubnet function
            console.print(f"🔍 Calling getSubnet({subnet_id})...")

            try:
                subnet_data = mt_client.contract.functions.getSubnet(subnet_id).call()

                static_data, dynamic_data, miner_addresses, validator_addresses = (
                    subnet_data
                )

                if format == "json":
                    # Format as JSON
                    subnet_json = {
                        "subnet_id": subnet_id,
                        "static_data": {
                            "net_uid": static_data[0],
                            "name": static_data[1],
                            "description": static_data[2],
                            "owner": static_data[3],
                            "created_at": static_data[4],
                            "ai_model_type": static_data[5],
                            "consensus_type": static_data[6],
                        },
                        "dynamic_data": {
                            "total_miners": dynamic_data[0],
                            "total_validators": dynamic_data[1],
                            "total_staked_core": str(dynamic_data[2]),
                            "total_staked_btc": str(dynamic_data[3]),
                            "epoch": dynamic_data[4],
                            "last_update": dynamic_data[5],
                            "status": dynamic_data[6],
                        },
                        "miners": list(miner_addresses),
                        "validators": list(validator_addresses),
                    }
                    console.print(JSON(subnet_json))

                elif format == "tree":
                    # Format as tree
                    tree = Tree(f"🌐 Subnet {subnet_id}", style="bold blue")

                    # Static data branch
                    static_branch = tree.add("📋 Static Data", style="cyan")
                    static_branch.add(f"Net UID: {static_data[0]}")
                    static_branch.add(f"Name: {static_data[1]}")
                    static_branch.add(f"Description: {static_data[2]}")
                    static_branch.add(f"Owner: {static_data[3]}")
                    static_branch.add(f"Created: {static_data[4]}")
                    static_branch.add(f"AI Model: {static_data[5]}")
                    static_branch.add(f"Consensus: {static_data[6]}")

                    # Dynamic data branch
                    dynamic_branch = tree.add("🔄 Dynamic Data", style="yellow")
                    dynamic_branch.add(f"Miners: {dynamic_data[0]}")
                    dynamic_branch.add(f"Validators: {dynamic_data[1]}")
                    dynamic_branch.add(
                        f"CORE Staked: {dynamic_data[2] / 10**18:.4f} CORE"
                    )
                    dynamic_branch.add(f"BTC Staked: {dynamic_data[3] / 10**8:.8f} BTC")
                    dynamic_branch.add(f"Epoch: {dynamic_data[4]}")
                    dynamic_branch.add(f"Last Update: {dynamic_data[5]}")
                    dynamic_branch.add(f"Status: {dynamic_data[6]}")

                    # Miners branch
                    if miner_addresses:
                        miners_branch = tree.add(
                            f"⛏️  Miners ({len(miner_addresses)})", style="green"
                        )
                        for i, miner in enumerate(miner_addresses):
                            miners_branch.add(f"{i+1}. {miner}")

                    # Validators branch
                    if validator_addresses:
                        validators_branch = tree.add(
                            f"✅ Validators ({len(validator_addresses)})",
                            style="magenta",
                        )
                        for i, validator in enumerate(validator_addresses):
                            validators_branch.add(f"{i+1}. {validator}")

                    console.print(tree)

                else:  # table format (default)
                    # Display static data
                    static_table = Table(
                        title=f"Subnet {subnet_id} - Static Data", border_style="cyan"
                    )
                    static_table.add_column("Property", style="bold")
                    static_table.add_column("Value", style="cyan")

                    static_table.add_row("Net UID", str(static_data[0]))
                    static_table.add_row("Name", static_data[1])
                    static_table.add_row("Description", static_data[2])
                    static_table.add_row("Owner", static_data[3])
                    static_table.add_row("Created At", str(static_data[4]))
                    static_table.add_row("AI Model Type", static_data[5])
                    static_table.add_row("Consensus Type", static_data[6])

                    console.print(static_table)

                    # Display dynamic data
                    dynamic_table = Table(
                        title=f"Subnet {subnet_id} - Dynamic Data",
                        border_style="yellow",
                    )
                    dynamic_table.add_column("Property", style="bold")
                    dynamic_table.add_column("Value", style="yellow")

                    dynamic_table.add_row("Total Miners", str(dynamic_data[0]))
                    dynamic_table.add_row("Total Validators", str(dynamic_data[1]))
                    dynamic_table.add_row(
                        "Total CORE Staked", f"{dynamic_data[2] / 10**18:.4f} CORE"
                    )
                    dynamic_table.add_row(
                        "Total BTC Staked", f"{dynamic_data[3] / 10**8:.8f} BTC"
                    )
                    dynamic_table.add_row("Current Epoch", str(dynamic_data[4]))
                    dynamic_table.add_row("Last Update", str(dynamic_data[5]))
                    dynamic_table.add_row("Status", str(dynamic_data[6]))

                    console.print(dynamic_table)

                    # Display miners
                    if miner_addresses:
                        miners_table = Table(
                            title=f"Subnet {subnet_id} - Miners", border_style="green"
                        )
                        miners_table.add_column("Index", style="bold")
                        miners_table.add_column("Address", style="green")

                        for i, miner in enumerate(miner_addresses):
                            miners_table.add_row(str(i + 1), miner)

                        console.print(miners_table)

                    # Display validators
                    if validator_addresses:
                        validators_table = Table(
                            title=f"Subnet {subnet_id} - Validators",
                            border_style="magenta",
                        )
                        validators_table.add_column("Index", style="bold")
                        validators_table.add_column("Address", style="magenta")

                        for i, validator in enumerate(validator_addresses):
                            validators_table.add_row(str(i + 1), validator)

                        console.print(validators_table)

                # Summary panel
                console.print(
                    Panel(
                        f"[bold]Subnet ID:[/bold] [blue]{subnet_id}[/blue]\n"
                        f"[bold]Name:[/bold] [cyan]{static_data[1]}[/cyan]\n"
                        f"[bold]Miners:[/bold] [green]{len(miner_addresses)}[/green]\n"
                        f"[bold]Validators:[/bold] [magenta]{len(validator_addresses)}[/magenta]\n"
                        f"[bold]Total Staked:[/bold] [yellow]{dynamic_data[2] / 10**18:.4f} CORE + {dynamic_data[3] / 10**8:.8f} BTC[/yellow]",
                        title="📊 Subnet Summary",
                        expand=False,
                    )
                )

            except Exception as contract_error:
                if "Subnet not found" in str(contract_error):
                    console.print(
                        f"❌ [bold red]Subnet {subnet_id} not found[/bold red]"
                    )
                    console.print(
                        "💡 Use 'mtcore query subnets' to see available subnets"
                    )
                else:
                    console.print(
                        f"❌ [bold red]Contract Error:[/bold red] {contract_error}"
                    )

        except Exception as e:
            console.print(f"❌ [bold red]Error:[/bold red] {e}")
            logger.exception(e)

    asyncio.run(query_subnet())


@query_cli.command("subnets")
@click.option(
    "--contract-address",
    help="ModernTensor contract address (uses settings.CORE_CONTRACT_ADDRESS by default).",
)
@click.option(
    "--node-url", help="Custom Core node URL (uses settings.CORE_NODE_URL by default)."
)
@click.option(
    "--network",
    type=click.Choice(["mainnet", "testnet", "devnet", "local"]),
    default="testnet",
    help="Select Core blockchain network.",
)
def query_subnets_cmd(contract_address, node_url, network):
    """
    📋 List all available subnets using getAllSubnetIds function.
    """
    console = Console()
    console.print("⏳ Fetching all subnets...")

    async def query_subnets():
        try:
            # Determine node URL
            if not node_url:
                if network == "mainnet":
                    node_url_final = "https://rpc.coredao.org"
                elif network == "testnet":
                    node_url_final = "https://rpc.test2.btcs.network"
                elif network == "devnet":
                    node_url_final = "https://rpc.dev.btcs.network"
                else:  # local
                    node_url_final = "https://rpc.test2.btcs.network"
            else:
                node_url_final = node_url

            # Use contract address from settings if not provided
            if not contract_address:
                contract_address_final = settings.CORE_CONTRACT_ADDRESS
            else:
                contract_address_final = contract_address

            console.print(f"📍 Contract: [cyan]{contract_address_final}[/cyan]")
            console.print(f"🌐 Network: [green]{network}[/green] ({node_url_final})")

            # Create Web3 client
            w3 = Web3(Web3.HTTPProvider(node_url_final))

            if not w3.is_connected():
                console.print(
                    "❌ [bold red]Failed to connect to Core network[/bold red]"
                )
                return

            # Create ModernTensor client
            mt_client = MTCoreClient(w3=w3, contract_address=contract_address_final)

            # Call getAllSubnetIds function
            console.print("🔍 Calling getAllSubnetIds()...")

            try:
                subnet_ids = mt_client.contract.functions.getAllSubnetIds().call()

                if not subnet_ids:
                    console.print("[bold yellow]No subnets found.[/bold yellow]")
                    return

                # Create table for subnet list
                table = Table(title="📋 Available Subnets", border_style="blue")
                table.add_column("Subnet ID", style="bold blue")
                table.add_column("Name", style="cyan")
                table.add_column("Miners", style="green")
                table.add_column("Validators", style="magenta")
                table.add_column("Total Staked", style="yellow")
                table.add_column("Status", style="bright_white")

                total_miners = 0
                total_validators = 0
                total_core_staked = 0
                total_btc_staked = 0

                for subnet_id in subnet_ids:
                    try:
                        # Get subnet static data only for faster loading
                        static_data = mt_client.contract.functions.getSubnetStatic(
                            subnet_id
                        ).call()
                        dynamic_data = mt_client.contract.functions.getSubnetDynamic(
                            subnet_id
                        ).call()

                        subnet_name = (
                            static_data[1] if static_data[1] else f"Subnet {subnet_id}"
                        )
                        miners_count = dynamic_data[0]
                        validators_count = dynamic_data[1]
                        core_staked = dynamic_data[2] / 10**18
                        btc_staked = dynamic_data[3] / 10**8
                        status = "Active" if dynamic_data[6] == 1 else "Inactive"

                        table.add_row(
                            str(subnet_id),
                            subnet_name,
                            str(miners_count),
                            str(validators_count),
                            f"{core_staked:.2f} CORE + {btc_staked:.4f} BTC",
                            (
                                f"[green]{status}[/green]"
                                if status == "Active"
                                else f"[red]{status}[/red]"
                            ),
                        )

                        total_miners += miners_count
                        total_validators += validators_count
                        total_core_staked += core_staked
                        total_btc_staked += btc_staked

                    except Exception as subnet_error:
                        console.print(
                            f"⚠️ Error getting data for subnet {subnet_id}: {subnet_error}"
                        )
                        table.add_row(
                            str(subnet_id),
                            "Error",
                            "N/A",
                            "N/A",
                            "N/A",
                            "[red]Error[/red]",
                        )

                console.print(table)

                # Network summary
                console.print(
                    Panel(
                        f"[bold]Total Subnets:[/bold] [blue]{len(subnet_ids)}[/blue]\n"
                        f"[bold]Total Miners:[/bold] [green]{total_miners}[/green]\n"
                        f"[bold]Total Validators:[/bold] [magenta]{total_validators}[/magenta]\n"
                        f"[bold]Total Staked:[/bold] [yellow]{total_core_staked:.2f} CORE + {total_btc_staked:.4f} BTC[/yellow]",
                        title="🌐 Network Summary",
                        expand=False,
                    )
                )

                console.print(
                    f"\n💡 Use [cyan]mtcore query subnet --subnet-id <ID>[/cyan] for detailed subnet information"
                )

            except Exception as contract_error:
                console.print(
                    f"❌ [bold red]Contract Error:[/bold red] {contract_error}"
                )

        except Exception as e:
            console.print(f"❌ [bold red]Error:[/bold red] {e}")
            logger.exception(e)

    asyncio.run(query_subnets())

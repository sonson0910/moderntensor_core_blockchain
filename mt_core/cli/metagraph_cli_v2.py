# mt_core/cli/metagraph_cli_v2.py - Core Blockchain Compatible Version
import click
import asyncio
import json
import os
import sys
from typing import Optional
from web3 import Web3
from dotenv import load_dotenv

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Add parent directories to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
mt_core_dir = os.path.dirname(os.path.dirname(current_dir))
moderntensor_root = os.path.dirname(mt_core_dir)
sys.path.insert(0, moderntensor_root)

# Load environment
load_dotenv()


# ------------------------------------------------------------------------------
# METAGRAPH COMMAND GROUP FOR CORE V2.0
# ------------------------------------------------------------------------------
@click.group()
def metagraph_cli():
    """
    🔄 Commands for working with ModernTensorAI v2.0 metagraph on Core blockchain. 🔄
    """
    pass


def _get_core_client():
    """Get Web3 client for Core blockchain"""
    rpc_url = os.getenv("CORE_NODE_URL", "https://rpc.test.btcs.network")
    w3 = Web3(Web3.HTTPProvider(rpc_url))

    # Add POA middleware
    try:
        from web3.middleware import ExtraDataToPOAMiddleware

        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    except ImportError:
        try:
            from web3.middleware import geth_poa_middleware

            w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        except ImportError:
            pass

    return w3


def _get_contract():
    """Get contract instance"""
    w3 = _get_core_client()
    contract_address = os.getenv("CORE_CONTRACT_ADDRESS")

    if not contract_address:
        raise ValueError("CORE_CONTRACT_ADDRESS not found in environment variables")

    # Contract ABI for v2.0
    contract_abi = [
        {
            "name": "getNetworkStats",
            "type": "function",
            "inputs": [],
            "outputs": [
                {"name": "totalMiners", "type": "uint256"},
                {"name": "totalValidators", "type": "uint256"},
                {"name": "totalStaked", "type": "uint256"},
                {"name": "totalRewards", "type": "uint256"},
            ],
            "stateMutability": "view",
        },
        {
            "name": "getSubnetMiners",
            "type": "function",
            "inputs": [{"name": "subnetId", "type": "uint64"}],
            "outputs": [{"name": "", "type": "address[]"}],
            "stateMutability": "view",
        },
        {
            "name": "getSubnetValidators",
            "type": "function",
            "inputs": [{"name": "subnetId", "type": "uint64"}],
            "outputs": [{"name": "", "type": "address[]"}],
            "stateMutability": "view",
        },
        {
            "name": "miners",
            "type": "function",
            "inputs": [{"name": "", "type": "address"}],
            "outputs": [
                {"name": "uid", "type": "bytes32"},
                {"name": "subnet_uid", "type": "uint64"},
                {"name": "stake", "type": "uint256"},
                {"name": "scaled_last_performance", "type": "uint64"},
                {"name": "scaled_trust_score", "type": "uint64"},
                {"name": "accumulated_rewards", "type": "uint256"},
                {"name": "last_update_time", "type": "uint64"},
                {"name": "performance_history_hash", "type": "bytes32"},
                {"name": "wallet_addr_hash", "type": "bytes32"},
                {"name": "status", "type": "uint8"},
                {"name": "registration_time", "type": "uint64"},
                {"name": "api_endpoint", "type": "string"},
            ],
            "stateMutability": "view",
        },
        {
            "name": "validators",
            "type": "function",
            "inputs": [{"name": "", "type": "address"}],
            "outputs": [
                {"name": "uid", "type": "bytes32"},
                {"name": "subnet_uid", "type": "uint64"},
                {"name": "stake", "type": "uint256"},
                {"name": "scaled_last_performance", "type": "uint64"},
                {"name": "scaled_trust_score", "type": "uint64"},
                {"name": "accumulated_rewards", "type": "uint256"},
                {"name": "last_update_time", "type": "uint64"},
                {"name": "performance_history_hash", "type": "bytes32"},
                {"name": "wallet_addr_hash", "type": "bytes32"},
                {"name": "status", "type": "uint8"},
                {"name": "registration_time", "type": "uint64"},
                {"name": "api_endpoint", "type": "string"},
            ],
            "stateMutability": "view",
        },
    ]

    return w3.eth.contract(address=contract_address, abi=contract_abi)


# ------------------------------------------------------------------------------
# NETWORK STATS COMMAND
# ------------------------------------------------------------------------------
@metagraph_cli.command("stats")
def network_stats_cmd():
    """
    📊 Show network statistics from ModernTensorAI v2.0 contract.
    """
    console = Console()
    console.print("⏳ Fetching network statistics...")

    try:
        w3 = _get_core_client()
        contract = _get_contract()

        console.print(f"✅ Connected to Core: {w3.is_connected()}")
        console.print(f"📝 Contract: {contract.address}")

        # Get network stats
        network_stats = contract.functions.getNetworkStats().call()

        # Create stats table
        table = Table(
            title="🌐 ModernTensorAI v2.0 Network Statistics", border_style="blue"
        )
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="bright_white")

        table.add_row("👥 Total Miners", str(network_stats[0]))
        table.add_row("🛡️ Total Validators", str(network_stats[1]))
        table.add_row(
            "💰 Total Staked", f"{Web3.from_wei(network_stats[2], 'ether')} CORE"
        )
        table.add_row(
            "🎁 Total Rewards", f"{Web3.from_wei(network_stats[3], 'ether')} CORE"
        )

        console.print(table)

    except Exception as e:
        console.print(f"[bold red]Error fetching network stats:[/bold red] {e}")


# ------------------------------------------------------------------------------
# LIST MINERS COMMAND
# ------------------------------------------------------------------------------
@metagraph_cli.command("list-miners")
@click.option(
    "--subnet-uid", default=0, type=int, help="Subnet ID to query (default: 0)."
)
def list_miners_cmd(subnet_uid):
    """
    📋 List all miners in the specified subnet.
    """
    console = Console()
    console.print(f"⏳ Fetching miners for subnet [cyan]{subnet_uid}[/cyan]...")

    try:
        w3 = _get_core_client()
        contract = _get_contract()

        # Get subnet miners
        miner_addresses = contract.functions.getSubnetMiners(subnet_uid).call()

        if not miner_addresses:
            console.print("[bold yellow]No miners found in this subnet.[/bold yellow]")
            return

        # Create miners table
        table = Table(title=f"👥 Miners in Subnet {subnet_uid}", border_style="blue")
        table.add_column("Address", style="blue")
        table.add_column("UID", style="magenta")
        table.add_column("Stake", style="yellow")
        table.add_column("Trust Score", style="cyan")
        table.add_column("Status", style="bright_white")
        table.add_column("API Endpoint", style="green")

        for address in miner_addresses:
            try:
                miner_data = contract.functions.miners(address).call()

                uid = miner_data[0].hex()[:16] + "..."  # Truncate UID
                stake = Web3.from_wei(miner_data[2], "ether")
                trust_score = miner_data[4] / 10000  # Convert from scaled
                status = ["Inactive", "Active", "Jailed"][miner_data[9]]
                api_endpoint = miner_data[11] or "N/A"

                status_style = (
                    "green"
                    if miner_data[9] == 1
                    else "yellow" if miner_data[9] == 0 else "red"
                )

                table.add_row(
                    address,
                    uid,
                    f"{stake:.4f} CORE",
                    f"{trust_score:.2f}%",
                    f"[{status_style}]{status}[/{status_style}]",
                    api_endpoint,
                )
            except Exception as e:
                table.add_row(address, "Error", "Error", "Error", "Error", str(e))

        console.print(table)
        console.print(f"Total miners: [bold cyan]{len(miner_addresses)}[/bold cyan]")

    except Exception as e:
        console.print(f"[bold red]Error listing miners:[/bold red] {e}")


# ------------------------------------------------------------------------------
# LIST VALIDATORS COMMAND
# ------------------------------------------------------------------------------
@metagraph_cli.command("list-validators")
@click.option(
    "--subnet-uid", default=0, type=int, help="Subnet ID to query (default: 0)."
)
def list_validators_cmd(subnet_uid):
    """
    📋 List all validators in the specified subnet.
    """
    console = Console()
    console.print(f"⏳ Fetching validators for subnet [cyan]{subnet_uid}[/cyan]...")

    try:
        w3 = _get_core_client()
        contract = _get_contract()

        # Get subnet validators
        validator_addresses = contract.functions.getSubnetValidators(subnet_uid).call()

        if not validator_addresses:
            console.print(
                "[bold yellow]No validators found in this subnet.[/bold yellow]"
            )
            return

        # Create validators table
        table = Table(title=f"🛡️ Validators in Subnet {subnet_uid}", border_style="blue")
        table.add_column("Address", style="blue")
        table.add_column("UID", style="magenta")
        table.add_column("Stake", style="yellow")
        table.add_column("Trust Score", style="cyan")
        table.add_column("Status", style="bright_white")
        table.add_column("API Endpoint", style="green")

        for address in validator_addresses:
            try:
                validator_data = contract.functions.validators(address).call()

                uid = validator_data[0].hex()[:16] + "..."  # Truncate UID
                stake = Web3.from_wei(validator_data[2], "ether")
                trust_score = validator_data[4] / 10000  # Convert from scaled
                status = ["Inactive", "Active", "Jailed"][validator_data[9]]
                api_endpoint = validator_data[11] or "N/A"

                status_style = (
                    "green"
                    if validator_data[9] == 1
                    else "yellow" if validator_data[9] == 0 else "red"
                )

                table.add_row(
                    address,
                    uid,
                    f"{stake:.4f} CORE",
                    f"{trust_score:.2f}%",
                    f"[{status_style}]{status}[/{status_style}]",
                    api_endpoint,
                )
            except Exception as e:
                table.add_row(address, "Error", "Error", "Error", "Error", str(e))

        console.print(table)
        console.print(
            f"Total validators: [bold cyan]{len(validator_addresses)}[/bold cyan]"
        )

    except Exception as e:
        console.print(f"[bold red]Error listing validators:[/bold red] {e}")


# ------------------------------------------------------------------------------
# METAGRAPH SUMMARY COMMAND
# ------------------------------------------------------------------------------
@metagraph_cli.command("summary")
def metagraph_summary_cmd():
    """
    📈 Show complete metagraph summary with all entities.
    """
    console = Console()
    console.print("⏳ Generating metagraph summary...")

    try:
        w3 = _get_core_client()
        contract = _get_contract()

        # Get network stats
        network_stats = contract.functions.getNetworkStats().call()

        # Get entities for default subnet (0)
        miner_addresses = contract.functions.getSubnetMiners(0).call()
        validator_addresses = contract.functions.getSubnetValidators(0).call()

        # Network overview panel
        overview_text = f"""
🌐 [bold]Network Overview[/bold]
├─ 👥 Miners: {network_stats[0]}
├─ 🛡️ Validators: {network_stats[1]}
├─ 💰 Total Staked: {Web3.from_wei(network_stats[2], 'ether')} CORE
└─ 🎁 Total Rewards: {Web3.from_wei(network_stats[3], 'ether')} CORE

🔗 Contract: {contract.address}
⛓️ Network: Core Testnet (Chain ID: 1115)
📊 Subnet 0: {len(miner_addresses)} miners, {len(validator_addresses)} validators
"""

        console.print(
            Panel(
                overview_text,
                title="🎯 ModernTensorAI v2.0 - Core Edition",
                border_style="bright_blue",
            )
        )

        # Entities status
        if miner_addresses or validator_addresses:
            status_text = "✅ Network is operational with registered entities\n"
            status_text += "✅ ModernTensor-style UID system active\n"
            status_text += "✅ Trust scores operational\n"
            status_text += "✅ Ready for consensus and AI task distribution"
            console.print(
                Panel(status_text, title="🚀 System Status", border_style="green")
            )
        else:
            console.print(
                Panel(
                    "⚠️ No entities registered yet",
                    title="System Status",
                    border_style="yellow",
                )
            )

    except Exception as e:
        console.print(f"[bold red]Error generating summary:[/bold red] {e}")


if __name__ == "__main__":
    metagraph_cli()

# sdk/cli/main.py

#!/usr/bin/env python3

import click
import logging
import importlib.metadata
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import box

from .wallet_cli import wallet_cli
from .query_cli import query_cli
from .tx_cli import tx_cli
from .metagraph_cli import metagraph_cli
from .stake_cli import stake_cli
from .hd_wallet_cli import hdwallet

# from .metagraph_cli import metagraph_cli  # If you have

logging.basicConfig(level=logging.INFO)

# ASCII Art for ModernTensor
ASCII_ART = r"""
███╗   ███╗ ██████╗ ██████╗ ███████╗██████╗ ███╗   ██╗████████╗███████╗███╗   ██╗███████╗ ██████╗ ██████╗ 
████╗ ████║██╔═══██╗██╔══██╗██╔════╝██╔══██╗████╗  ██║╚══██╔══╝██╔════╝████╗  ██║██╔════╝██╔═══██╗██╔══██╗
██╔████╔██║██║   ██║██║  ██║█████╗  ██████╔╝██╔██╗ ██║   ██║   █████╗  ██╔██╗ ██║███████╗██║   ██║██████╔╝
██║╚██╔╝██║██║   ██║██║  ██║██╔══╝  ██╔══██╗██║╚██╗██║   ██║   ██╔══╝  ██║╚██╗██║╚════██║██║   ██║██╔══██╗
██║ ╚═╝ ██║╚██████╔╝██████╔╝███████╗██║  ██║██║ ╚████║   ██║   ███████╗██║ ╚████║███████║╚██████╔╝██║  ██║
╚═╝     ╚═╝ ╚═════╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝   ╚══════╝╚═╝  ╚═══╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝
                                                                                                          
                                                                    
"""

# Colorful scheme v2
PROJECT_DESCRIPTION = """[bright_yellow]⭐ Moderntensor is a decentralized model training project built on the Core blockchain platform.
The project is developed by Vietnamese 🇻🇳  engineers from the Moderntensor Foundation.[/bright_yellow]"""
REPO_URL = "https://github.com/sonson0910/moderntensor_core.git"  # Replace
DOCS_URL = "https://github.com/sonson0910/moderntensor_core/blob/development_consensus/docs/WhitePaper.pdf"  # Replace
CHAT_URL = "https://t.me/+pDRlNXTi1wY2NTY1"  # Replace
CONTRIBUTE_URL = f"https://github.com/sonson0910/moderntensor_core/blob/main/docs/README.md"  # Adjust if needed


# Create the main CLI group
@click.group()
def mtcore():
    """
    🗳️ ModernTensor Core Control Tool - A command line interface for managing Core blockchain accounts and operations. 🗳️
    """
    pass


# Add all subcommands
mtcore.add_command(wallet_cli)
mtcore.add_command(query_cli)
mtcore.add_command(tx_cli)
mtcore.add_command(metagraph_cli)
mtcore.add_command(stake_cli)
mtcore.add_command(hdwallet)


@mtcore.command()
def version():
    """Show version information."""
    console = Console()
    console.print(
        Panel.fit(
            "[bold cyan]ModernTensor Core Control Tool[/bold cyan]\n"
            "Version: 0.2.0\n"
            "A command line interface for managing Core blockchain accounts and operations",
            title="About",
            border_style="cyan",
        )
    )


# Main entry point
def main():
    """Main entry point for mtcore CLI."""
    mtcore()


if __name__ == "__main__":
    main()

# Thêm group con:
# cli.add_command(wallet_cli, name="w")
# cli.add_command(tx_cli, name="tx")
# cli.add_command(query_cli, name="query")
# cli.add_command(stake_cli, name="stake")
# cli.add_command(metagraph_cli, name="metagraph")

# If you want, you can place the original command here:
# Remove the old version command if displaying version in splash screen
# @cli.command("version")
# def version_cmd():
#     click.echo("SDK version 0.1.0")

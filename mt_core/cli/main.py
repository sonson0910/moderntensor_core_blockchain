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

# 🔥 CYBERPUNK ASCII ART 🔥
CYBERPUNK_BANNER = r"""
▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
██████████████████████████████████████████████████████████████████████████████████████████████████████
███  ⚡ M O D E R N T E N S O R   C Y B E R P U N K   C L I   ⚡  ███
██    🤖 Q U A N T U M   B L O C K C H A I N   I N T E R F A C E   🤖    ██
██████████████████████████████████████████████████████████████████████████████████████████████████████
▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
"""

# 🤖 CYBERPUNK PROJECT DESCRIPTION 🤖
PROJECT_DESCRIPTION = """[bold bright_cyan]🔥 MODERNTENSOR NEURAL NETWORK:[/] [bright_green]Decentralized AI model training on Core blockchain[/]
[bold bright_magenta]🤖 QUANTUM FOUNDATION:[/] [bright_yellow]Built by Vietnamese 🇻🇳 cyber engineers[/]
[bold bright_red]⚡ NEURAL MATRIX:[/] [bright_cyan]Advanced consensus algorithms & cyberpunk interface[/]"""
REPO_URL = "https://github.com/sonson0910/moderntensor_core.git"  # Replace
DOCS_URL = "https://github.com/sonson0910/moderntensor_core/blob/development_consensus/docs/WhitePaper.pdf"  # Replace
CHAT_URL = "https://t.me/+pDRlNXTi1wY2NTY1"  # Replace
CONTRIBUTE_URL = f"https://github.com/sonson0910/moderntensor_core/blob/main/docs/README.md"  # Adjust if needed


# Create the main CLI group
@click.group()
def mtcore():
    """
    🔥 MODERNTENSOR CYBERPUNK CLI - Neural network command interface for quantum blockchain operations ⚡
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
    """🔥 Show cyberpunk version information ⚡"""
    console = Console(force_terminal=True, color_system="truecolor")

    # 🤖 CYBERPUNK VERSION PANEL 🤖
    console.print(CYBERPUNK_BANNER, style="bold bright_cyan")
    console.print(
        Panel.fit(
            "[bold bright_magenta]🔥 MODERNTENSOR CYBERPUNK CLI 🔥[/]\n"
            "[bright_green]Neural Version:[/] [bold bright_yellow]0.2.0[/]\n"
            "[bright_cyan]Quantum Interface:[/] [bright_yellow]Core blockchain neural command matrix[/]\n"
            "[bright_red]Cyber Status:[/] [bold bright_green blink]FULLY OPERATIONAL[/]",
            title="[bold bright_red blink]⚡ CYBER SYSTEM INFO ⚡[/]",
            border_style="bright_magenta",
            padding=(1, 2),
        )
    )
    console.print(PROJECT_DESCRIPTION)
    console.print("\n🔗 [bold bright_cyan]NEURAL LINKS:[/]")
    console.print(f"📋 [bright_green]Repository:[/] [bright_blue]{REPO_URL}[/]")
    console.print(f"📖 [bright_green]Documentation:[/] [bright_blue]{DOCS_URL}[/]")
    console.print(f"💬 [bright_green]Cyber Chat:[/] [bright_blue]{CHAT_URL}[/]")


# 🔥 CYBERPUNK MAIN ENTRY POINT 🔥
def main():
    """🤖 Cyberpunk main entry point for neural CLI matrix ⚡"""
    console = Console(force_terminal=True, color_system="truecolor")

    # Show cyberpunk banner on startup
    console.print(CYBERPUNK_BANNER, style="bold bright_cyan")
    console.print(
        "🔥 [bold bright_red blink]NEURAL MATRIX INITIALIZED[/] 🔥", justify="center"
    )
    console.print(
        "⚡ [bright_yellow]Type --help for cyber commands[/] ⚡\n", justify="center"
    )

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

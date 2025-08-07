#!/usr/bin/env python3
"""
🔥 CYBERPUNK UI UTILITIES - Epic visual effects for ModernTensor CLI 🔥

This module provides reusable cyberpunk-styled UI components for all CLI commands.
Create an immersive neural-hacker interface with quantum blockchain aesthetics.
"""

import asyncio
import time
from typing import Optional, Union, List

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from rich.columns import Columns
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TimeRemainingColumn,
)
from rich.prompt import Prompt, Confirm
from rich import box


# ==============================================================================
# 🔥 CYBERPUNK UI UTILITIES 🔥
# ==============================================================================


def create_cyberpunk_console():
    """Create a cyberpunk-styled Rich console"""
    return Console(force_terminal=True, color_system="truecolor", width=120)


def print_cyberpunk_header(console, title: str, subtitle: str = ""):
    """Print an epic cyberpunk header with neon frames"""

    # Create simple text for better compatibility
    title_str = f"⚡ {title.upper()} ⚡"
    subtitle_str = f"🔥 {subtitle} 🔥" if subtitle else ""

    # Create the epic frame with proper centering
    console.print("\n")
    console.print("╔" + "═" * 116 + "╗", style="bright_cyan bold")
    console.print("║" + " " * 116 + "║", style="bright_cyan bold")

    # Center the title
    title_padding = (116 - len(title_str)) // 2
    title_line = (
        " " * title_padding + title_str + " " * (116 - title_padding - len(title_str))
    )
    console.print("║" + title_line + "║", style="bright_cyan bold")

    # Center the subtitle if provided
    if subtitle:
        subtitle_padding = (116 - len(subtitle_str)) // 2
        subtitle_line = (
            " " * subtitle_padding
            + subtitle_str
            + " " * (116 - subtitle_padding - len(subtitle_str))
        )
        console.print("║" + subtitle_line + "║", style="bright_cyan bold")

    console.print("║" + " " * 116 + "║", style="bright_cyan bold")
    console.print("╚" + "═" * 116 + "╝", style="bright_cyan bold")

    # Add cyberpunk styled title and subtitle
    if title:
        title_text = Text()
        title_text.append("⚡ ", style="bright_yellow bold")
        title_text.append(title.upper(), style="bright_cyan bold")
        title_text.append(" ⚡", style="bright_yellow bold")
        console.print(Align.center(title_text), style="bright_cyan bold")

    if subtitle:
        subtitle_text = Text()
        subtitle_text.append("🔥 ", style="bright_red")
        subtitle_text.append(subtitle, style="bright_magenta")
        subtitle_text.append(" 🔥", style="bright_red")
        console.print(Align.center(subtitle_text), style="bright_magenta")

    console.print()


def print_cyberpunk_panel(console, content, title: str, style: str = "bright_cyan"):
    """Print content in a cyberpunk-styled panel with epic border"""
    # Choose border style based on type
    if style == "bright_green":
        border_char = "█"
        emoji = "🚀"
    elif style == "bright_red":
        border_char = "▓"
        emoji = "🚨"
    elif style == "bright_yellow":
        border_char = "░"
        emoji = "⚡"
    else:
        border_char = "▒"
        emoji = "🔥"

    console.print()
    console.print(border_char * 120, style=f"{style} bold")
    console.print(border_char + " " * 118 + border_char, style=f"{style} bold")

    # Title line with emojis
    title_str = f"{emoji} {title.upper()} {emoji}"
    title_padding = (118 - len(title_str)) // 2
    title_line = (
        " " * title_padding + title_str + " " * (118 - title_padding - len(title_str))
    )
    console.print(border_char + title_line + border_char, style=f"{style} bold")

    console.print(border_char + " " * 118 + border_char, style=f"{style} bold")

    # Content lines
    if isinstance(content, str):
        content_lines = content.split("\n")
    else:
        # Handle Text objects
        content_lines = str(content).split("\n")

    for line in content_lines:
        if line.strip():
            line_padding = (118 - len(line)) // 2
            content_line = (
                " " * line_padding + line + " " * (118 - line_padding - len(line))
            )
            console.print(
                border_char + content_line + border_char, style=f"{style} bold"
            )

    console.print(border_char + " " * 118 + border_char, style=f"{style} bold")
    console.print(border_char * 120, style=f"{style} bold")
    console.print()


def print_cyberpunk_table(
    console, title: str, headers: list, rows: list, style: str = "bright_cyan"
):
    """Create a cyberpunk-styled table"""
    table = Table(
        title=f"⚡ {title.upper()} ⚡",
        title_style="bold bright_cyan",
        border_style=style,
        header_style=f"bold {style}",
        show_header=True,
        show_lines=True,
        box=box.DOUBLE_EDGE,
        row_styles=["", "dim"],
    )

    # Add headers with cyberpunk styling
    for header in headers:
        table.add_column(f"🔥 {header} 🔥", justify="center", style="bright_white")

    # Add rows
    for row in rows:
        table.add_row(*[str(cell) for cell in row])

    console.print(table)


def cyberpunk_progress_context(console, description: str):
    """Create a cyberpunk-styled progress context"""
    return Progress(
        SpinnerColumn(),
        TextColumn(f"⚡ {description} ⚡"),
        BarColumn(bar_width=40),
        TextColumn("[progress.percentage]{task.percentage:>3.1f}%"),
        TimeRemainingColumn(),
        console=console,
        transient=False,
    )


def print_cyberpunk_success(console, message: str):
    """Print a cyberpunk success message with epic border"""
    # Create epic cyberpunk border
    console.print()
    console.print("┏" + "━" * 118 + "┓", style="bright_green bold")
    console.print("┃" + " " * 118 + "┃", style="bright_green bold")
    console.print("┃" + "🔥" * 59 + "┃", style="bright_green bold")

    # Center the success message
    msg_str = f"✅ [QUANTUM SUCCESS] {message} 🚀"
    padding = (118 - len(msg_str)) // 2
    msg_line = " " * padding + msg_str + " " * (118 - padding - len(msg_str))
    console.print("┃" + msg_line + "┃", style="bright_green bold")

    console.print("┃" + "🔥" * 59 + "┃", style="bright_green bold")
    console.print("┃" + " " * 118 + "┃", style="bright_green bold")
    console.print("┗" + "━" * 118 + "┛", style="bright_green bold")
    console.print()


def print_cyberpunk_error(console, message: str):
    """Print a cyberpunk error message with epic border"""
    # Create epic cyberpunk error border
    console.print()
    console.print("╔" + "═" * 118 + "╗", style="bright_red bold")
    console.print("║" + " " * 118 + "║", style="bright_red bold")
    console.print("║" + "⚠️" * 59 + "║", style="bright_red bold")

    # Center the error message
    msg_str = f"❌ [MATRIX ERROR] {message} 🚨"
    padding = (118 - len(msg_str)) // 2
    msg_line = " " * padding + msg_str + " " * (118 - padding - len(msg_str))
    console.print("║" + msg_line + "║", style="bright_red bold")

    console.print("║" + "⚠️" * 59 + "║", style="bright_red bold")
    console.print("║" + " " * 118 + "║", style="bright_red bold")
    console.print("╚" + "═" * 118 + "╝", style="bright_red bold")
    console.print()


def print_cyberpunk_warning(console, message: str):
    """Print a cyberpunk warning message with epic border"""
    # Create epic cyberpunk warning border
    console.print()
    console.print("▓" + "▓" * 118 + "▓", style="bright_yellow bold")
    console.print("▓" + " " * 118 + "▓", style="bright_yellow bold")
    console.print("▓" + "⚡" * 59 + "▓", style="bright_yellow bold")

    # Center the warning message
    msg_str = f"⚠️ [NEURAL WARNING] {message} ⚡"
    padding = (118 - len(msg_str)) // 2
    msg_line = " " * padding + msg_str + " " * (118 - padding - len(msg_str))
    console.print("▓" + msg_line + "▓", style="bright_yellow bold")

    console.print("▓" + "⚡" * 59 + "▓", style="bright_yellow bold")
    console.print("▓" + " " * 118 + "▓", style="bright_yellow bold")
    console.print("▓" + "▓" * 118 + "▓", style="bright_yellow bold")
    console.print()


def cyberpunk_confirm(console, message: str) -> bool:
    """Cyberpunk-styled confirmation prompt with epic border"""
    # Create epic cyberpunk confirmation border
    console.print()
    console.print("╭" + "─" * 118 + "╮", style="bright_cyan bold")
    console.print("│" + " " * 118 + "│", style="bright_cyan bold")
    console.print("│" + "🤖" * 59 + "│", style="bright_cyan bold")

    # Center the confirmation message
    msg_str = f"🤖 [NEURAL QUERY] {message} [Y/n]"
    padding = (118 - len(msg_str)) // 2
    msg_line = " " * padding + msg_str + " " * (118 - padding - len(msg_str))
    console.print("│" + msg_line + "│", style="bright_cyan bold")

    console.print("│" + "🤖" * 59 + "│", style="bright_cyan bold")
    console.print("│" + " " * 118 + "│", style="bright_cyan bold")
    console.print("╰" + "─" * 118 + "╯", style="bright_cyan bold")
    console.print()

    return Confirm.ask("", default=True, console=console)


def print_cyberpunk_transaction_frame(console, tx_hash: str, operation: str):
    """Print an epic transaction frame with cyberpunk styling"""
    console.print()
    # Create epic transaction border with mixed characters
    console.print(
        "╔" + "═" * 40 + "╦" + "═" * 36 + "╦" + "═" * 40 + "╗", style="bright_cyan bold"
    )
    console.print(
        "║" + " " * 40 + "║" + " " * 36 + "║" + " " * 40 + "║", style="bright_cyan bold"
    )

    # Operation header
    op_str = f"🔥 {operation.upper()} COMPLETE 🔥"
    op_padding = (116 - len(op_str)) // 2
    op_line = " " * op_padding + op_str + " " * (116 - op_padding - len(op_str))
    console.print("║" + op_line + "║", style="bright_cyan bold")

    console.print("║" + " " * 116 + "║", style="bright_cyan bold")
    console.print("╠" + "═" * 116 + "╣", style="bright_cyan bold")

    # Transaction hash section
    console.print("║" + "⚡" * 58 + "║", style="bright_yellow bold")
    tx_str = f"🚀 TX HASH: {tx_hash}"
    tx_padding = (116 - len(tx_str)) // 2
    tx_line = " " * tx_padding + tx_str + " " * (116 - tx_padding - len(tx_str))
    console.print("║" + tx_line + "║", style="bright_yellow bold")
    console.print("║" + "⚡" * 58 + "║", style="bright_yellow bold")

    console.print("║" + " " * 116 + "║", style="bright_cyan bold")
    console.print("╚" + "═" * 116 + "╝", style="bright_cyan bold")
    console.print()


def print_cyberpunk_loading_frame(console, message: str):
    """Print a cyberpunk loading frame"""
    console.print()
    console.print("▒" * 120, style="bright_magenta bold")
    console.print("▒" + " " * 118 + "▒", style="bright_magenta bold")

    # Loading message
    msg_padding = (118 - len(message)) // 2
    msg_line = " " * msg_padding + message + " " * (118 - msg_padding - len(message))
    console.print("▒" + msg_line + "▒", style="bright_magenta bold")

    console.print("▒" + " " * 118 + "▒", style="bright_magenta bold")
    console.print("▒" * 120, style="bright_magenta bold")
    console.print()


def print_cyberpunk_info(console, info_dict: dict, title: str = "SYSTEM INFO"):
    """Print information in a cyberpunk info panel"""
    info_text = Text()

    for key, value in info_dict.items():
        info_text.append(f"🔥 {key.upper()}: ", style="bright_cyan bold")
        info_text.append(f"{value}\n", style="bright_white")

    print_cyberpunk_panel(console, info_text, title, "bright_cyan")


def cyberpunk_spinner_task(console, description: str, duration: float = 2.0):
    """Create a cyberpunk spinner for long-running tasks"""

    async def _run_spinner():
        with cyberpunk_progress_context(console, description) as progress:
            task = progress.add_task("Processing...", total=100)

            steps = int(duration * 10)  # 10 steps per second
            for i in range(steps):
                await asyncio.sleep(0.1)
                progress.update(task, advance=100 / steps)

    return _run_spinner()


def print_cyberpunk_ascii_art(console, title: str = "MODERNTENSOR"):
    """Print epic ASCII art header"""
    ascii_art = f"""
╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                                                       ║
║  ███╗   ███╗ ██████╗ ██████╗ ███████╗██████╗ ███╗   ██╗████████╗███████╗███╗   ██╗███████╗ ██████╗ ██████╗          ║
║  ████╗ ████║██╔═══██╗██╔══██╗██╔════╝██╔══██╗████╗  ██║╚══██╔══╝██╔════╝████╗  ██║██╔════╝██╔═══██╗██╔══██╗         ║
║  ██╔████╔██║██║   ██║██║  ██║█████╗  ██████╔╝██╔██╗ ██║   ██║   █████╗  ██╔██╗ ██║███████╗██║   ██║██████╔╝         ║
║  ██║╚██╔╝██║██║   ██║██║  ██║██╔══╝  ██╔══██╗██║╚██╗██║   ██║   ██╔══╝  ██║╚██╗██║╚════██║██║   ██║██╔══██╗         ║
║  ██║ ╚═╝ ██║╚██████╔╝██████╔╝███████╗██║  ██║██║ ╚████║   ██║   ███████╗██║ ╚████║███████║╚██████╔╝██║  ██║         ║
║  ╚═╝     ╚═╝ ╚═════╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝   ╚══════╝╚═╝  ╚═══╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝         ║
║                                                                                                                       ║
║                              ⚡ CYBERPUNK QUANTUM BLOCKCHAIN INTERFACE ⚡                                           ║
║                                    🤖 NEURAL COMMAND MATRIX ONLINE 🤖                                              ║
║                                                                                                                       ║
╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
"""

    console.print(ascii_art, style="bright_cyan bold")


def print_cyberpunk_command_help(console, commands: List[dict]):
    """Print available commands in cyberpunk style"""
    print_cyberpunk_header(
        console, "AVAILABLE NEURAL COMMANDS", "Select your quantum operation"
    )

    # Create command table
    table = Table(
        title="🔥 CYBERPUNK COMMAND MATRIX 🔥",
        title_style="bold bright_cyan",
        border_style="bright_cyan",
        header_style="bold bright_cyan",
        show_header=True,
        show_lines=True,
        box=box.DOUBLE_EDGE,
    )

    table.add_column("🤖 Command", justify="left", style="bright_yellow bold")
    table.add_column("⚡ Description", justify="left", style="bright_white")
    table.add_column("🔥 Usage", justify="left", style="bright_green")

    for cmd in commands:
        table.add_row(
            cmd.get("name", ""), cmd.get("description", ""), cmd.get("usage", "")
        )

    console.print(table)


# Network status indicators
def get_cyberpunk_network_status(network: str) -> tuple:
    """Get cyberpunk styling for network status"""
    network_styles = {
        "mainnet": ("🔥", "bright_red", "PRODUCTION MATRIX"),
        "testnet": ("⚡", "bright_yellow", "TESTING NEURAL NET"),
        "devnet": ("🤖", "bright_cyan", "DEVELOPMENT CORE"),
        "local": ("🚀", "bright_magenta", "LOCAL QUANTUM NODE"),
    }

    return network_styles.get(
        network.lower(), ("❓", "bright_white", "UNKNOWN NETWORK")
    )


def print_cyberpunk_network_info(console, network: str, node_url: str = ""):
    """Print network information with cyberpunk styling"""
    emoji, style, status = get_cyberpunk_network_status(network)

    network_info = {
        "Neural Network": f"{emoji} {network.upper()}",
        "Matrix Status": status,
        "Quantum Node": node_url if node_url else "DEFAULT_NODE_URL",
        "Connection": "🟢 ONLINE" if network != "unknown" else "🔴 OFFLINE",
    }

    print_cyberpunk_info(console, network_info, "NETWORK STATUS")

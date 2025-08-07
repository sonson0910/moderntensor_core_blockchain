#!/usr/bin/env python3
"""
Extended Cyberpunk UI for Scoring and Metagraph Updates
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TimeRemainingColumn,
)
from rich.live import Live
import time


def create_cyberpunk_console():
    """Create a console with cyberpunk styling"""
    return Console(force_terminal=True, color_system="truecolor")


def print_cyberpunk_scoring_header(validator_uid: str, slot: int, num_tasks: int):
    """Print cyberpunk-style scoring header with animations"""
    console = create_cyberpunk_console()

    # Enhanced cyberpunk frame with double borders and effects
    console.print()
    console.print("[bold bright_red]" + "▀" * 80 + "[/bold bright_red]")
    console.print("[bold bright_cyan]" + "█" * 80 + "[/bold bright_cyan]")

    # Animated header with glitch effects
    header_text = "🧠⚡ QUANTUM NEURAL SCORING MATRIX ONLINE ⚡🧠"
    console.print(
        f"[bold bright_yellow on bright_red]{header_text:^80}[/bold bright_yellow on bright_red]"
    )

    # Add scanning effect
    console.print("[bold bright_green]" + "░▒▓█" * 20 + "[/bold bright_green]")

    # Validator info with more style
    console.print()
    console.print(
        f"[bold bright_cyan]║[/bold bright_cyan] [bright_magenta]🤖 VALIDATOR UNIT:[/bright_magenta] [bright_white]{validator_uid[:25]}...[/bright_white] [bold bright_cyan]║[/bold bright_cyan]"
    )
    console.print(
        f"[bold bright_cyan]║[/bold bright_cyan] [bright_yellow]⚡ SLOT SECTOR:[/bright_yellow] [bright_green]{slot}[/bright_green] [bright_yellow]| TASK COUNT:[/bright_yellow] [bright_red]{num_tasks}[/bright_red] [bold bright_cyan]║[/bold bright_cyan]"
    )
    console.print()

    # Status indicators
    console.print(
        f"[bold bright_cyan]║[/bold bright_cyan] [bright_green]● CLIP ENGINE:[/bright_green] [bright_white]ACTIVE[/bright_white] [bright_cyan]● NEURAL NET:[/bright_cyan] [bright_white]ONLINE[/bright_white] [bold bright_cyan]║[/bold bright_cyan]"
    )
    console.print(
        f"[bold bright_cyan]║[/bold bright_cyan] [bright_yellow]● SCORING AI:[/bright_yellow] [bright_white]READY[/bright_white] [bright_magenta]● QUANTUM CORE:[/bright_magenta] [bright_white]SYNCHRONIZED[/bright_white] [bold bright_cyan]║[/bold bright_cyan]"
    )
    console.print()

    console.print("[bold bright_red]" + "▄" * 80 + "[/bold bright_red]")
    console.print()


def print_cyberpunk_task_score(
    task_id: str, miner_uid: str, score: float, max_score: float = 1.0
):
    """Print individual task score in cyberpunk style with enhanced effects"""
    console = create_cyberpunk_console()

    # Score percentage and bar
    percentage = (score / max_score) * 100 if max_score > 0 else 0
    bar_length = 30  # Increased bar length
    filled_length = int(bar_length * score / max_score) if max_score > 0 else 0

    # Enhanced color and rank system
    if percentage >= 90:
        score_color = "bright_green"
        bar_color = "bright_green"
        rank = "🔥 LEGENDARY"
        rank_color = "bright_green"
        effect = "✨"
    elif percentage >= 80:
        score_color = "bright_green"
        bar_color = "bright_green"
        rank = "⚡ ELITE"
        rank_color = "bright_green"
        effect = "💎"
    elif percentage >= 60:
        score_color = "bright_yellow"
        bar_color = "bright_yellow"
        rank = "🎯 SUPERIOR"
        rank_color = "bright_yellow"
        effect = "🌟"
    elif percentage >= 40:
        score_color = "yellow"
        bar_color = "yellow"
        rank = "💪 DECENT"
        rank_color = "yellow"
        effect = "⭐"
    else:
        score_color = "bright_red"
        bar_color = "bright_red"
        rank = "🤖 BASIC"
        rank_color = "bright_red"
        effect = "🔧"

    # Create animated progress bar with gradient effect
    bar_chars = ["█", "▓", "▒", "░"]
    bar = ""
    for i in range(bar_length):
        if i < filled_length:
            # Add some gradient effect
            if i < filled_length * 0.7:
                bar += bar_chars[0]  # Full
            elif i < filled_length * 0.9:
                bar += bar_chars[1]  # Three-quarters
            else:
                bar += bar_chars[2]  # Half
        else:
            bar += bar_chars[3]  # Empty

    # Add scanning effect for high scores
    if percentage >= 80:
        scan_effect = "[blink bright_white]◄►[/blink bright_white]"
    else:
        scan_effect = ""

    # Print with enhanced styling
    console.print(
        f"[bold bright_cyan]═══════════════════════════════════════════════════════════════════════════════[/bold bright_cyan]"
    )
    console.print(
        f"[bright_cyan]🎯 TASK ID:[/bright_cyan] [bright_white]{task_id[:15]}...[/bright_white] "
        f"{scan_effect} "
        f"[bright_cyan]MINER:[/bright_cyan] [bright_magenta]{miner_uid[:12]}...[/bright_magenta]"
    )
    console.print(
        f"[bright_cyan]🧠 AI SCORE:[/bright_cyan] [{score_color}]{score:.6f}[/{score_color}] "
        f"[bright_cyan]RATING:[/bright_cyan] [{rank_color}]{rank}[/{rank_color}] "
        f"{effect}"
    )
    console.print(
        f"[bright_cyan]📊 PROGRESS:[/bright_cyan] [{bar_color}]{bar}[/{bar_color}] "
        f"[{score_color}]{percentage:.1f}%[/{score_color}]"
    )
    console.print()


def print_cyberpunk_scoring_summary(
    total_tasks: int, total_scores: int, avg_score: float
):
    """Print cyberpunk-style scoring summary with enhanced stats"""
    console = create_cyberpunk_console()

    # Calculate efficiency and performance level
    efficiency = (total_scores / total_tasks * 100) if total_tasks > 0 else 0
    avg_percentage = avg_score * 100

    # Determine overall performance level
    if avg_percentage >= 80:
        performance_level = "🔥 QUANTUM SUPREMACY"
        performance_color = "bright_green"
        status_icon = "🚀"
    elif avg_percentage >= 60:
        performance_level = "⚡ NEURAL EXCELLENCE"
        performance_color = "bright_yellow"
        status_icon = "✨"
    elif avg_percentage >= 40:
        performance_level = "💪 DIGITAL COMPETENCE"
        performance_color = "yellow"
        status_icon = "⚙️"
    else:
        performance_level = "🤖 BASIC PROCESSING"
        performance_color = "bright_red"
        status_icon = "🔧"

    # Create enhanced summary with animations
    console.print()
    console.print("[bold bright_red]" + "▼" * 80 + "[/bold bright_red]")
    console.print(
        "[bold bright_yellow on bright_blue]"
        + f"⚡ NEURAL SCORING MATRIX ANALYSIS COMPLETE ⚡".center(80)
        + "[/bold bright_yellow on bright_blue]"
    )
    console.print("[bold bright_red]" + "▲" * 80 + "[/bold bright_red]")
    console.print()

    # Main stats with visual bars
    console.print(
        f"[bold bright_cyan]╔══════════════════════ QUANTUM ANALYSIS RESULTS ══════════════════════╗[/bold bright_cyan]"
    )
    console.print(
        f"[bold bright_cyan]║[/bold bright_cyan]                                                                        [bold bright_cyan]║[/bold bright_cyan]"
    )
    console.print(
        f"[bold bright_cyan]║[/bold bright_cyan] [bright_yellow]📋 TOTAL TASKS PROCESSED:[/bright_yellow] [bright_white]{total_tasks:>8}[/bright_white] {status_icon} [bold bright_cyan]║[/bold bright_cyan]"
    )
    console.print(
        f"[bold bright_cyan]║[/bold bright_cyan] [bright_green]🎯 VALID SCORES GENERATED:[/bright_green] [bright_white]{total_scores:>7}[/bright_white] 💎 [bold bright_cyan]║[/bold bright_cyan]"
    )
    console.print(
        f"[bold bright_cyan]║[/bold bright_cyan] [bright_magenta]🧠 AVERAGE AI SCORE:[/bright_magenta] [bright_white]{avg_score:>11.6f}[/bright_white] 🌟 [bold bright_cyan]║[/bold bright_cyan]"
    )
    console.print(
        f"[bold bright_cyan]║[/bold bright_cyan] [bright_red]🔥 PROCESSING EFFICIENCY:[/bright_red] [bright_white]{efficiency:>6.1f}%[/bright_white] ⚡ [bold bright_cyan]║[/bold bright_cyan]"
    )
    console.print(
        f"[bold bright_cyan]║[/bold bright_cyan]                                                                        [bold bright_cyan]║[/bold bright_cyan]"
    )

    # Performance level display
    console.print(
        f"[bold bright_cyan]║[/bold bright_cyan] [bright_yellow]🏆 PERFORMANCE LEVEL:[/bright_yellow] [{performance_color}]{performance_level}[/{performance_color}] [bold bright_cyan]║[/bold bright_cyan]"
    )
    console.print(
        f"[bold bright_cyan]║[/bold bright_cyan]                                                                        [bold bright_cyan]║[/bold bright_cyan]"
    )

    # Visual progress bar for average score
    bar_length = 50
    filled_length = int(bar_length * avg_score)
    bar = "█" * filled_length + "░" * (bar_length - filled_length)
    console.print(
        f"[bold bright_cyan]║[/bold bright_cyan] [bright_cyan]SCORE VISUALIZATION:[/bright_cyan] [{performance_color}]{bar}[/{performance_color}] [bold bright_cyan]║[/bold bright_cyan]"
    )
    console.print(
        f"[bold bright_cyan]║[/bold bright_cyan] [bright_white]                    0%[/bright_white]                    [bright_white]100%[/bright_white] [bold bright_cyan]║[/bold bright_cyan]"
    )
    console.print(
        f"[bold bright_cyan]║[/bold bright_cyan]                                                                        [bold bright_cyan]║[/bold bright_cyan]"
    )
    console.print(
        f"[bold bright_cyan]╚════════════════════════════════════════════════════════════════════════╝[/bold bright_cyan]"
    )

    # Final status
    console.print()
    console.print(
        f"[bold {performance_color}]🤖 QUANTUM NEURAL NETWORK STATUS: {performance_level} 🤖[/bold {performance_color}]"
    )
    console.print("[bold bright_green]" + "░▒▓█" * 20 + "[/bold bright_green]")
    console.print()


def print_cyberpunk_clip_scoring(prompt: str, clip_score: float, task_id: str):
    """Print CLIP scoring process with cyberpunk effects"""
    console = create_cyberpunk_console()

    # CLIP scoring header
    console.print()
    console.print(
        "[bold bright_magenta]"
        + "◄" * 40
        + " CLIP AI ANALYSIS "
        + "►" * 40
        + "[/bold bright_magenta]"
    )

    # Task info
    console.print(
        f"[bright_cyan]🎯 TASK:[/bright_cyan] [bright_white]{task_id[:20]}...[/bright_white]"
    )
    console.print(
        f"[bright_yellow]📝 PROMPT:[/bright_yellow] [bright_white]'{prompt[:50]}...'[/bright_white]"
    )

    # Simulate AI processing animation
    console.print(
        f"[bright_green]🧠 NEURAL PROCESSING:[/bright_green] [blink bright_white]● ● ●[/blink bright_white] [bright_cyan]ANALYZING IMAGE...[/bright_cyan]"
    )

    # CLIP score with enhanced visualization
    percentage = clip_score * 100
    if percentage >= 80:
        score_color = "bright_green"
        rating = "🔥 EXCEPTIONAL"
        icon = "🚀"
    elif percentage >= 60:
        score_color = "bright_yellow"
        rating = "⚡ EXCELLENT"
        icon = "✨"
    elif percentage >= 40:
        score_color = "yellow"
        rating = "💪 GOOD"
        icon = "⭐"
    else:
        score_color = "bright_red"
        rating = "🤖 AVERAGE"
        icon = "🔧"

    # Visual score display
    bar_length = 25
    filled_length = int(bar_length * clip_score)
    bar = "█" * filled_length + "░" * (bar_length - filled_length)

    console.print(
        f"[bright_cyan]🎨 CLIP SCORE:[/bright_cyan] [{score_color}]{clip_score:.4f}[/{score_color}] [{score_color}]{bar}[/{score_color}] [{score_color}]{percentage:.1f}%[/{score_color}]"
    )
    console.print(
        f"[bright_cyan]🏆 AI RATING:[/bright_cyan] [{score_color}]{rating}[/{score_color}] {icon}"
    )

    console.print("[bold bright_magenta]" + "◄" * 97 + "[/bold bright_magenta]")
    console.print()


def print_cyberpunk_metagraph_header(validator_uid: str, slot: int):
    """Print cyberpunk-style metagraph update header"""
    console = create_cyberpunk_console()

    # Create animated-looking header
    frame = "╔" + "═" * 78 + "╗\n"
    frame += "║" + " " * 78 + "║\n"
    frame += f"║{'🌐 QUANTUM METAGRAPH SYNCHRONIZATION 🌐':^78}║\n"
    frame += "║" + " " * 78 + "║\n"
    frame += f"║{'Validator Node: ' + validator_uid[:15] + '...':^78}║\n"
    frame += f"║{'Slot: ' + str(slot) + ' | Blockchain Update In Progress':^78}║\n"
    frame += "║" + " " * 78 + "║\n"
    frame += "╚" + "═" * 78 + "╝"

    console.print(f"[bold bright_cyan]{frame}[/bold bright_cyan]")


def print_cyberpunk_metagraph_scores(scores: dict, slot: int):
    """Print metagraph scores in cyberpunk table format"""
    console = create_cyberpunk_console()

    if not scores:
        console.print(
            "[bright_yellow]⚠️ No consensus scores found for metagraph update[/bright_yellow]"
        )
        return

    scores_table = Table(
        title=f"🔥 [bold bright_cyan]CONSENSUS SCORES - SLOT {slot}[/bold bright_cyan] 🔥",
        show_header=True,
        header_style="bold bright_yellow",
        border_style="bright_magenta",
        title_style="bold bright_red",
    )

    scores_table.add_column("Miner UID", style="bright_cyan", width=20)
    scores_table.add_column("Performance Score", style="bright_green", width=20)
    scores_table.add_column("Rating", style="bright_white", width=15)
    scores_table.add_column("Status", style="bright_yellow", width=15)

    for miner_uid, score in scores.items():
        # Determine rating and status
        if score >= 0.8:
            rating = "🔥 ELITE"
            status = "🟢 OPTIMAL"
            score_color = "bright_green"
        elif score >= 0.6:
            rating = "⚡ STRONG"
            status = "🟡 GOOD"
            score_color = "bright_yellow"
        elif score >= 0.4:
            rating = "💪 DECENT"
            status = "🟠 FAIR"
            score_color = "yellow"
        else:
            rating = "🤖 BASIC"
            status = "🔴 WEAK"
            score_color = "bright_red"

        scores_table.add_row(
            f"{miner_uid[:18]}...",
            f"[{score_color}]{score:.6f}[/{score_color}]",
            rating,
            status,
        )

    console.print(scores_table)


def print_cyberpunk_metagraph_submission(slot: int, num_scores: int, success: bool):
    """Print cyberpunk-style blockchain submission result"""
    console = create_cyberpunk_console()

    if success:
        result_panel = Panel(
            f"[bold bright_green]✅ BLOCKCHAIN SYNCHRONIZATION COMPLETE ✅[/bold bright_green]\n\n"
            f"[bright_cyan]🌐 Slot:[/bright_cyan] [bright_white]{slot}[/bright_white]\n"
            f"[bright_cyan]📊 Scores Submitted:[/bright_cyan] [bright_white]{num_scores}[/bright_white]\n"
            f"[bright_cyan]⚡ Transaction Status:[/bright_cyan] [bright_green]CONFIRMED[/bright_green]\n"
            f"[bright_cyan]🔗 Network State:[/bright_cyan] [bright_green]SYNCHRONIZED[/bright_green]",
            title="🚀 [bold bright_green]QUANTUM UPLOAD SUCCESS[/bold bright_green] 🚀",
            border_style="bright_green",
            padding=(1, 2),
        )
    else:
        result_panel = Panel(
            f"[bold bright_red]❌ BLOCKCHAIN SYNCHRONIZATION FAILED ❌[/bold bright_red]\n\n"
            f"[bright_cyan]🌐 Slot:[/bright_cyan] [bright_white]{slot}[/bright_white]\n"
            f"[bright_cyan]📊 Scores Attempted:[/bright_cyan] [bright_white]{num_scores}[/bright_white]\n"
            f"[bright_cyan]⚡ Transaction Status:[/bright_cyan] [bright_red]REJECTED[/bright_red]\n"
            f"[bright_cyan]🔗 Network State:[/bright_cyan] [bright_red]DESYNCHRONIZED[/bright_red]",
            title="🚨 [bold bright_red]QUANTUM UPLOAD ERROR[/bold bright_red] 🚨",
            border_style="bright_red",
            padding=(1, 2),
        )

    console.print(result_panel)


def print_cyberpunk_phase_transition(from_phase: str, to_phase: str, slot: int):
    """Print cyberpunk-style phase transition"""
    console = create_cyberpunk_console()

    phase_icons = {
        "task_assignment": "📋",
        "consensus_scoring": "🧠",
        "metagraph_update": "🌐",
        "cycle_transition": "🔄",
    }

    from_icon = phase_icons.get(from_phase, "⚡")
    to_icon = phase_icons.get(to_phase, "⚡")

    console.print(
        f"[bright_cyan]🔄 PHASE TRANSITION:[/bright_cyan] "
        f"[bright_yellow]{from_icon} {from_phase.upper()}[/bright_yellow] "
        f"[bright_white]→[/bright_white] "
        f"[bright_green]{to_icon} {to_phase.upper()}[/bright_green] "
        f"[bright_cyan]| SLOT:[/bright_cyan] [bright_white]{slot}[/bright_white]"
    )

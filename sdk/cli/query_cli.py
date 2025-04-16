# sdk/cli/query_cli.py
import click
from rich.console import Console
from rich.table import Table
from pycardano import Address, Network, UTxO, PlutusData
from typing import Optional, Any

from sdk.config.settings import settings, logger
from sdk.service.context import get_chain_context
from sdk.service.query_service import get_address_info
from sdk.service.stake_service import Wallet  # For balance/utxo query
from sdk.service.utxos import get_utxo_from_str, get_utxo_with_lowest_performance
from sdk.metagraph.metagraph_datum import (
    MinerDatum,
)  # Assuming this is the default datum for contract queries


# ------------------------------------------------------------------------------
# QUERY COMMAND GROUP
# ------------------------------------------------------------------------------
@click.group()
def query_cli():
    """
    🔍 Commands for querying blockchain information. 🔍
    """
    pass


# ------------------------------------------------------------------------------
# QUERY ADDRESS INFO
# ------------------------------------------------------------------------------
@query_cli.command("address")
@click.argument("address_str", type=str)
@click.option(
    "--network",
    default=lambda: (
        "mainnet" if settings.CARDANO_NETWORK == Network.MAINNET else "testnet"
    ),
    type=click.Choice(["testnet", "mainnet"]),
    help="Select Cardano network.",
)
def address_cmd(address_str, network):
    """
    ℹ️  Show detailed balance (ADA, Tokens) and UTxO count for an ADDRESS.
    """
    console = Console()
    net = Network.TESTNET if network == "testnet" else Network.MAINNET

    console.print(
        f"🔍 Querying information for address: [cyan]{address_str}[/cyan] on [yellow]{network.upper()}[/yellow]..."
    )

    try:
        context = get_chain_context()
        if not context:
            console.print(
                "[bold red]Error:[/bold red] Could not initialize Cardano chain context."
            )
            return

        info = get_address_info(address_str, context)

        table = Table(
            title=f"Address Information: {address_str}",
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("Item", style="dim")
        table.add_column("Value")

        table.add_row("Address", info["address"])
        table.add_row("ADA (Lovelace)", f"{info['lovelace']:,}")
        table.add_row("ADA", f"{info['lovelace'] / 1_000_000:.6f}")
        table.add_row("UTxO Count", str(info["utxo_count"]))

        console.print(table)

        if info["tokens"]:
            token_table = Table(
                title="Native Tokens", show_header=True, header_style="bold blue"
            )
            token_table.add_column("Policy ID")
            token_table.add_column("Asset Name (Hex)")
            token_table.add_column("Asset Name (Decoded)")
            token_table.add_column("Amount")

            for (policy, asset_name), amount in info["tokens"].items():
                try:
                    an_hex = (
                        asset_name.payload.hex()
                        if hasattr(asset_name, "payload")
                        else asset_name.hex()
                    )
                    decoded_name = (
                        asset_name.payload.decode("utf-8")
                        if hasattr(asset_name, "payload")
                        else bytes.fromhex(asset_name.hex()).decode(
                            "utf-8", errors="replace"
                        )
                    )
                except Exception:
                    an_hex = (
                        asset_name.hex()
                        if hasattr(asset_name, "hex")
                        else str(asset_name)
                    )
                    decoded_name = "[dim](Cannot decode)[/dim]"

                token_table.add_row(str(policy), an_hex, decoded_name, f"{amount:,}")
            console.print(token_table)
        else:
            console.print("  No native tokens found at this address.")

    except Exception as e:
        console.print(f":cross_mark: [bold red]Error querying address:[/bold red] {e}")
        logger.exception("Address query failed")


# ------------------------------------------------------------------------------
# QUERY HOTKEY BALANCE
# ------------------------------------------------------------------------------
@query_cli.command("balance")
@click.option("--coldkey", required=True, help="Coldkey name.")
@click.option("--hotkey", required=True, help="Hotkey name.")
@click.option(
    "--password",
    prompt=True,
    hide_input=True,
    help="Coldkey password.",
)
@click.option(
    "--network",
    default=lambda: (
        "mainnet" if settings.CARDANO_NETWORK == Network.MAINNET else "testnet"
    ),
    type=click.Choice(["testnet", "mainnet"]),
    help="Select Cardano network.",
)
def balance_cmd(coldkey, hotkey, password, network):
    """
    💰 Show detailed balance (ADA, Tokens) for a specific Hotkey.
    """
    console = Console()
    net = Network.TESTNET if network == "testnet" else Network.MAINNET

    console.print(
        f"💰 Querying balance for: [magenta]{coldkey}[/magenta] / [cyan]{hotkey}[/cyan] on [yellow]{network.upper()}[/yellow]..."
    )
    try:
        wallet = Wallet(coldkey_name=coldkey, hotkey_name=hotkey, password=password)
        console.print(f"  Address: [blue]{wallet.main_address}[/blue]")
        wallet.get_balances()

    except Exception as e:
        console.print(f":cross_mark: [bold red]Error querying balance:[/bold red] {e}")
        logger.exception("Hotkey balance query failed")


# ------------------------------------------------------------------------------
# QUERY HOTKEY UTXOS
# ------------------------------------------------------------------------------
@query_cli.command("utxos")
@click.option("--coldkey", required=True, help="Coldkey name.")
@click.option("--hotkey", required=True, help="Hotkey name.")
@click.option(
    "--password",
    prompt=True,
    hide_input=True,
    help="Coldkey password.",
)
@click.option(
    "--network",
    default=lambda: (
        "mainnet" if settings.CARDANO_NETWORK == Network.MAINNET else "testnet"
    ),
    type=click.Choice(["testnet", "mainnet"]),
    help="Select Cardano network.",
)
def utxos_cmd(coldkey, hotkey, password, network):
    """
    📄 List UTxOs held by a specific Hotkey address.
    """
    console = Console()
    net = Network.TESTNET if network == "testnet" else Network.MAINNET

    console.print(
        f"📄 Querying UTxOs for: [magenta]{coldkey}[/magenta] / [cyan]{hotkey}[/cyan] on [yellow]{network.upper()}[/yellow]..."
    )

    try:
        wallet = Wallet(coldkey_name=coldkey, hotkey_name=hotkey, password=password)
        console.print(f"  Address: [blue]{wallet.main_address}[/blue]")
        bf_utxos = wallet.get_utxos()

        if not bf_utxos:
            console.print("  No UTxOs found at this address.")
            return

        table = Table(
            title=f"UTxOs at {wallet.main_address}",
            show_header=True,
            header_style="bold green",
        )
        table.add_column("Tx Hash")
        table.add_column("Index", style="dim")
        table.add_column("ADA")
        table.add_column("Other Tokens")

        for item in bf_utxos:
            utxo_data: Any = item
            try:
                tx_hash = getattr(utxo_data, "tx_hash", utxo_data["tx_hash"])
                tx_index = getattr(utxo_data, "output_index", utxo_data["output_index"])
                amount_list = getattr(utxo_data, "amount", utxo_data["amount"])
            except (AttributeError, KeyError, TypeError) as access_err:
                logger.warning(
                    f"Could not access expected UTxO attributes: {access_err} for data: {utxo_data}"
                )
                continue

            ada_amt = 0
            tokens_str_list = []
            if isinstance(amount_list, list):
                for token_item in amount_list:
                    token_data: Any = token_item
                    try:
                        unit = getattr(token_data, "unit", token_data["unit"])
                        quantity = getattr(
                            token_data, "quantity", token_data["quantity"]
                        )
                        if unit == "lovelace":
                            ada_amt = int(quantity)
                        else:
                            policy_id = unit[:56] if len(unit) > 56 else unit
                            asset_hex = unit[56:] if len(unit) > 56 else ""
                            try:
                                asset_name = bytes.fromhex(asset_hex).decode(
                                    "utf-8", errors="replace"
                                )
                            except ValueError:
                                asset_name = f"(hex: {asset_hex})"
                            tokens_str_list.append(
                                f"{quantity} {policy_id[:6]}...{asset_name}"
                            )
                    except (AttributeError, KeyError, TypeError) as token_err:
                        logger.warning(
                            f"Could not process token data: {token_err} for token: {token_data}"
                        )
                        tokens_str_list.append("[Error processing token]")
            else:
                logger.warning(
                    f"Unexpected amount format for UTxO {tx_hash}#{tx_index}: {amount_list}"
                )

            tokens_display = ", ".join(tokens_str_list) if tokens_str_list else "-"
            table.add_row(
                str(tx_hash),
                str(tx_index),
                f"{ada_amt / 1_000_000:.6f}",
                tokens_display,
            )
        console.print(table)

    except Exception as e:
        console.print(f":cross_mark: [bold red]Error querying UTxOs:[/bold red] {e}")
        logger.exception("Hotkey UTxO query failed")


# ------------------------------------------------------------------------------
# QUERY CONTRACT UTXO BY UID (Advanced/Debug)
# ------------------------------------------------------------------------------
@query_cli.command("contract-utxo")
@click.option("--contract-address", required=True, help="Smart contract address.")
@click.option("--uid", required=True, help="UID (hex string) to search for in datum.")
@click.option(
    "--network",
    default=lambda: (
        "mainnet" if str(settings.CARDANO_NETWORK).lower() == "mainnet" else "testnet"
    ),
    type=click.Choice(["testnet", "mainnet"]),
    help="Select Cardano network.",
)
def contract_utxo_cmd(contract_address, uid, network):
    """
    🔧 Find a contract UTxO by UID in its datum (assumes MinerDatum).
    """
    console = Console()
    net = Network.TESTNET if network == "testnet" else Network.MAINNET

    console.print(
        f"🔧 Searching for UTxO with UID [yellow]{uid}[/yellow] at contract [cyan]{contract_address}[/cyan] on [yellow]{network.upper()}[/yellow]..."
    )
    console.print("[dim](Assuming datum type: MinerDatum)[/dim]")

    try:
        context = get_chain_context()
        if not context:
            console.print(
                "[bold red]Error:[/bold red] Could not initialize Cardano chain context."
            )
            return

        address_obj = Address.from_primitive(contract_address)
        uid_bytes = bytes.fromhex(uid)

        found_utxo: Optional[UTxO] = get_utxo_from_str(
            contract_address=address_obj,
            datumclass=MinerDatum,
            context=context,
            search_uid=uid_bytes,
        )

        if found_utxo:
            console.print(f"✅ Found UTxO:")
            console.print(f"  Input: [green]{found_utxo.input}[/green]")
            console.print(f"  Output Address: {found_utxo.output.address}")
            console.print(f"  Amount: {found_utxo.output.amount}")

            output = found_utxo.output
            datum = output.datum
            datum_hash = output.datum_hash
            script = output.script

            if isinstance(datum, PlutusData):
                console.print(f"  Decoded Datum: {datum}")
                try:
                    datum_cbor_bytes = datum.to_cbor()
                    console.print(f"  Datum CBOR: {datum_cbor_bytes.hex()}")
                except Exception as cbor_err:
                    logger.warning(f"Could not get CBOR from decoded datum: {cbor_err}")
            elif datum_hash:
                console.print(f"  Datum Hash: {bytes(datum_hash).hex()}")
            if script:
                console.print(f"  Script: {script}")
        else:
            console.print(
                f"❌ No UTxO found with UID {uid} at the specified contract address."
            )

    except Exception as e:
        console.print(
            f":cross_mark: [bold red]Error querying contract UTxO:[/bold red] {e}"
        )
        logger.exception("Contract UTxO query failed")


# ------------------------------------------------------------------------------
# QUERY LOWEST PERFORMANCE UTXO (Advanced/Debug)
# ------------------------------------------------------------------------------
@query_cli.command("lowest-performance")
@click.option("--contract-address", required=True, help="Smart contract address.")
@click.option(
    "--network",
    default=lambda: (
        "mainnet" if str(settings.CARDANO_NETWORK).lower() == "mainnet" else "testnet"
    ),
    type=click.Choice(["testnet", "mainnet"]),
    help="Select Cardano network.",
)
def lowest_perf_cmd(contract_address, network):
    """
    📉 Find the contract UTxO with the lowest scaled_last_performance (assumes MinerDatum).
    """
    console = Console()
    net = Network.TESTNET if network == "testnet" else Network.MAINNET

    console.print(
        f"📉 Searching for lowest performance UTxO at contract [cyan]{contract_address}[/cyan] on [yellow]{network.upper()}[/yellow]..."
    )
    console.print("[dim](Assuming datum type: MinerDatum)[/dim]")

    try:
        context = get_chain_context()
        if not context:
            console.print(
                "[bold red]Error:[/bold red] Could not initialize Cardano chain context."
            )
            return

        address_obj = Address.from_primitive(contract_address)

        lowest_utxo: Optional[UTxO] = get_utxo_with_lowest_performance(
            contract_address=address_obj,
            datumclass=MinerDatum,
            context=context,
        )

        if lowest_utxo:
            console.print(f"✅ Found UTxO with lowest performance:")
            console.print(f"  Input: [green]{lowest_utxo.input}[/green]")
            console.print(f"  Output Address: {lowest_utxo.output.address}")
            console.print(f"  Amount: {lowest_utxo.output.amount}")

            output = lowest_utxo.output
            datum = output.datum
            datum_hash = output.datum_hash
            script = output.script

            if isinstance(datum, PlutusData):
                console.print(f"  Decoded Datum: {datum}")
                if hasattr(datum, "scaled_last_performance"):
                    perf = getattr(datum, "scaled_last_performance")
                    console.print(f"  Scaled Performance: [yellow]{perf}[/yellow]")
                try:
                    datum_cbor_bytes = datum.to_cbor()
                    console.print(f"  Datum CBOR: {datum_cbor_bytes.hex()}")
                except Exception as cbor_err:
                    logger.warning(f"Could not get CBOR from decoded datum: {cbor_err}")
            elif datum_hash:
                console.print(f"  Datum Hash: {bytes(datum_hash).hex()}")
            if script:
                console.print(f"  Script: {script}")
        else:
            console.print(
                f"❌ No suitable UTXO found with MinerDatum at the specified contract address."
            )

    except Exception as e:
        console.print(
            f":cross_mark: [bold red]Error querying lowest performance UTxO:[/bold red] {e}"
        )
        logger.exception("Lowest performance UTxO query failed")

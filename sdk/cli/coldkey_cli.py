# sdk/cli/coldkey_cli.py

import click
from pycardano import Network
from sdk.keymanager.wallet_manager import WalletManager


@click.group()
def coldkey_cli():
    """
    Group of CLI commands for ColdKey: create, load, ...
    """
    pass


@coldkey_cli.command("create")
@click.option("--name", required=True, help="Coldkey name.")
@click.option(
    "--password",
    prompt=True,
    hide_input=True,
    confirmation_prompt=True,
    help="mnemonic encryption password.",
)
@click.option(
    "--base-dir", default="moderntensor", help="The base directory stores coldkeys."
)
@click.option(
    "--network",
    default="testnet",
    type=click.Choice(["testnet", "mainnet"]),
    help="Select Cardano network.",
)
def create_coldkey_cmd(name, password, base_dir, network):
    """
    Generate coldkey (mnemonic), encrypt and save to folder.
    """
    net = Network.TESTNET if network == "testnet" else Network.MAINNET
    wm = WalletManager(network=net, base_dir=base_dir)
    wm.create_coldkey(name, password)
    click.echo(f"Coldkey '{name}' has been created in directory '{base_dir}'.")


@coldkey_cli.command("load")
@click.option("--name", required=True, help="Coldkey name.")
@click.option("--password", prompt=True, hide_input=True, help="Password.")
@click.option("--base-dir", default="moderntensor", help="Base directory.")
@click.option(
    "--network",
    default="testnet",
    type=click.Choice(["testnet", "mainnet"]),
    help="Network.",
)
def load_coldkey_cmd(name, password, base_dir, network):
    """
    Load coldkey into memory.
    """
    net = Network.TESTNET if network == "testnet" else Network.MAINNET
    wm = WalletManager(network=net, base_dir=base_dir)
    wm.load_coldkey(name, password)
    click.echo(f"Coldkey '{name}' has been loaded from the directory '{base_dir}'.")

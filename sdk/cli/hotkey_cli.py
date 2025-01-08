# sdk/cli/hotkey_cli.py

import click
from pycardano import Network
from sdk.keymanager.wallet_manager import WalletManager


@click.group()
def hotkey_cli():
    """
    CLI command group for HotKey: generate, import, ...
    """
    pass


@hotkey_cli.command("generate")
@click.option("--coldkey", required=True, help="Coldkey name.")
@click.option("--hotkey-name", required=True, help="Hotkey name.")
@click.option("--base-dir", default="moderntensor", help="Base directory.")
@click.option(
    "--network",
    default="testnet",
    type=click.Choice(["testnet", "mainnet"]),
    help="Network.",
)
def generate_hotkey_cmd(coldkey, hotkey_name, base_dir, network):
    """
    Create hotkey (public key) and save it to hotkeys.json
    """
    net = Network.TESTNET if network == "testnet" else Network.MAINNET
    wm = WalletManager(network=net, base_dir=base_dir)

    password = click.prompt("Enter the coldkey password", hide_input=True)
    wm.load_coldkey(coldkey, password)
    encrypted_data = wm.generate_hotkey(coldkey, hotkey_name)
    click.echo(f"Hotkey '{hotkey_name}' created => {encrypted_data}")


@hotkey_cli.command("import")
@click.option("--coldkey", required=True, help="Coldkey name.")
@click.option("--encrypted-hotkey", required=True, help="Encrypted hotkey string.")
@click.option("--hotkey-name", required=True, help="Hotkey name.")
@click.option(
    "--overwrite",
    is_flag=True,
    default=False,
    help="Overwrite the old hotkey if the name is the same.",
)
@click.option("--base-dir", default="moderntensor", help="Base directory.")
@click.option(
    "--network",
    default="testnet",
    type=click.Choice(["testnet", "mainnet"]),
    help="Network.",
)
def import_hotkey_cmd(
    coldkey, encrypted_hotkey, hotkey_name, overwrite, base_dir, network
):
    """
    Import 1 encryption hotkey.
    """
    net = Network.TESTNET if network == "testnet" else Network.MAINNET
    wm = WalletManager(network=net, base_dir=base_dir)

    password = click.prompt("Enter the coldkey password", hide_input=True)
    wm.load_coldkey(coldkey, password)

    wm.import_hotkey(coldkey, encrypted_hotkey, hotkey_name, overwrite=overwrite)
    click.echo(f"Hotkey '{hotkey_name}' has been imported.")

# file: sdk/cli/wallet_cli.py

import click
from rich.tree import Tree
from rich.console import Console
from pycardano import Network
from sdk.keymanager.wallet_manager import WalletManager

@click.group()
def wallet_cli():
    """
    CLI command group for Wallet Management (Coldkey & Hotkey).
    """
    pass

#------------------------------------------------------------------------------
# 1) CREATE COLDKEY
#------------------------------------------------------------------------------
@wallet_cli.command("create-coldkey")
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
    click.echo(f"[OK] Coldkey '{name}' has been created in directory '{base_dir}'.")


#------------------------------------------------------------------------------
# 2) LOAD COLDKEY
#------------------------------------------------------------------------------
@wallet_cli.command("load-coldkey")
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
    click.echo(f"[OK] Coldkey '{name}' has been loaded from '{base_dir}'.")


#------------------------------------------------------------------------------
# 3) GENERATE HOTKEY
#------------------------------------------------------------------------------
@wallet_cli.command("generate-hotkey")
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
    click.echo(f"[OK] Hotkey '{hotkey_name}' created => {encrypted_data}")


#------------------------------------------------------------------------------
# 4) IMPORT HOTKEY
#------------------------------------------------------------------------------
@wallet_cli.command("import-hotkey")
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
    Import an encrypted hotkey from a string.
    """
    net = Network.TESTNET if network == "testnet" else Network.MAINNET
    wm = WalletManager(network=net, base_dir=base_dir)

    password = click.prompt("Enter the coldkey password", hide_input=True)
    wm.load_coldkey(coldkey, password)

    wm.import_hotkey(coldkey, encrypted_hotkey, hotkey_name, overwrite=overwrite)
    click.echo(f"[OK] Hotkey '{hotkey_name}' has been imported.")


#------------------------------------------------------------------------------
# 5) LIST KEY
#------------------------------------------------------------------------------

@wallet_cli.command(name='list')
def list_coldkeys():
    """
    List all Coldkeys and their Hotkeys in tree structure (using Rich).
    """
    manager = WalletManager()  
    wallets = manager.load_all_wallets()

    console = Console()

    if not wallets:
        console.print("[bold red]No coldkeys found.[/bold red]")
        return

    root_tree = Tree("[bold cyan]Wallets[/bold cyan]")

    for w in wallets:
        ck_address = w["address"] or "unknown"
        # Tạo node con cho Coldkey
        coldkey_node = root_tree.add(
            f"[bold yellow]Coldkey[/bold yellow] [magenta]{w['name']}[/magenta] (address={ck_address})"
        )

        # hotkeys
        if w.get("hotkeys"):
            for hk in w["hotkeys"]:
                hk_addr = hk["address"] or "unknown"
                coldkey_node.add(
                    f"Hotkey [green]{hk['name']}[/green] (addr={hk_addr})"
                )
    
    console.print(root_tree)

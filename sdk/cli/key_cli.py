# file: sdk/cli/key_cli.py

import click
from sdk.keymanager.wallet_manager import WalletManager

@click.group()
def key_cli():
    """List of all keys available in the device"""
    pass

@key_cli.command(name='list')
def list_coldkeys():
    """
    List all Coldkeys and their Hotkeys in tree structure.
    """
    manager = WalletManager()  
    wallets = manager.load_all_wallets()

    if not wallets:
        click.echo("No coldkeys found.")
        return

    click.echo("Wallets")
    for i, cold in enumerate(wallets):
        prefix = "└── " if i == len(wallets)-1 else "├── "
        line = f"{prefix}Coldkey {cold['name']}  ss58_address {cold['address']}"
        click.echo(line)
        
        if 'hotkeys' in cold and cold['hotkeys']:
            for j, hot in enumerate(cold['hotkeys']):
                sub_prefix = "    └── " if (j == len(cold['hotkeys'])-1 and i == len(wallets)-1) else "    ├── "
                hk_line = f"{sub_prefix}Hotkey {hot['name']}  ss58_address {hot['address']}"
                click.echo(hk_line)

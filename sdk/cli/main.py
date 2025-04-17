# sdk/cli/main.py

import click
import logging
from .wallet_cli import wallet_cli
from .tx_cli import tx_cli
from .query_cli import query_cli
from .stake_cli import stake_cli

# from .metagraph_cli import metagraph_cli  # If you have

logging.basicConfig(level=logging.INFO)


@click.group()
def cli():
    """CLI SDK, grouping coldkey, hotkey, metagraph commands, etc..."""
    pass


# Thêm group con:
cli.add_command(wallet_cli, name="w")
cli.add_command(tx_cli, name="tx")
cli.add_command(query_cli, name="query")
cli.add_command(stake_cli, name="stake")
# cli.add_command(metagraph_cli, name="metagraph")


# If you want, you can place the original command here:
@cli.command("version")
def version_cmd():
    click.echo("SDK version 0.1.0")

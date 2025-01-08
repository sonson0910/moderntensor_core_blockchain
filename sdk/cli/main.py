# sdk/cli/main.py

import click
import logging
from .coldkey_cli import coldkey_cli
from .hotkey_cli import hotkey_cli

# from .metagraph_cli import metagraph_cli  # If you have

logging.basicConfig(level=logging.INFO)


@click.group()
def cli():
    """CLI SDK, grouping coldkey, hotkey, metagraph commands, etc..."""
    pass


# Thêm group con:
cli.add_command(coldkey_cli, name="coldkey")
cli.add_command(hotkey_cli, name="hotkey")
# cli.add_command(metagraph_cli, name="metagraph")

# If you want, you can place the original command here:
@cli.command("version")
def version_cmd():
    click.echo("SDK version 0.1.0")

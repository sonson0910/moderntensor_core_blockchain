#!/usr/bin/env python3

import click
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from sdk.keymanager.account_manager import AccountManager
from sdk.keymanager.encryption_utils import get_or_create_salt, generate_encryption_key

@click.group()
def cli():
    """Aptos Control Tool (aptosctl) - A command line interface for managing Aptos accounts and operations."""
    pass

@cli.group()
def wallet():
    """Wallet management commands."""
    pass

@wallet.command()
@click.option('--name', required=True, help='Name of the coldkey')
@click.option('--base-dir', default='moderntensor', help='Base directory for storing keys')
def create_coldkey(name, base_dir):
    """Create a new coldkey."""
    try:
        manager = AccountManager(base_dir)
        manager.create_coldkey(name)
        click.echo(f"Successfully created coldkey: {name}")
    except Exception as e:
        click.echo(f"Error creating coldkey: {str(e)}", err=True)

@wallet.command()
@click.option('--coldkey', required=True, help='Name of the coldkey')
@click.option('--hotkey-name', required=True, help='Name for the new hotkey')
@click.option('--base-dir', default='moderntensor', help='Base directory for storing keys')
def generate_hotkey(coldkey, hotkey_name, base_dir):
    """Generate a new hotkey for a coldkey."""
    try:
        manager = AccountManager(base_dir)
        manager.generate_hotkey(coldkey, hotkey_name)
        click.echo(f"Successfully generated hotkey {hotkey_name} for coldkey {coldkey}")
    except Exception as e:
        click.echo(f"Error generating hotkey: {str(e)}", err=True)

@wallet.command()
@click.option('--name', required=True, help='Name of the coldkey')
@click.option('--base-dir', default='moderntensor', help='Base directory for storing keys')
def info(name, base_dir):
    """Display information about a coldkey."""
    try:
        manager = AccountManager(base_dir)
        info = manager.get_coldkey_info(name)
        click.echo(f"Coldkey Information for {name}:")
        click.echo(f"Address: {info['address']}")
        click.echo(f"Public Key: {info['public_key']}")
    except Exception as e:
        click.echo(f"Error getting coldkey info: {str(e)}", err=True)

@cli.group()
def validator():
    """Validator management commands."""
    pass

@validator.command()
@click.option('--name', required=True, help='Name of the validator')
@click.option('--coldkey', required=True, help='Name of the coldkey to use')
@click.option('--base-dir', default='moderntensor', help='Base directory for storing keys')
def register(name, coldkey, base_dir):
    """Register a new validator."""
    try:
        manager = AccountManager(base_dir)
        manager.register_validator(name, coldkey)
        click.echo(f"Successfully registered validator: {name}")
    except Exception as e:
        click.echo(f"Error registering validator: {str(e)}", err=True)

@cli.group()
def subnet():
    """Subnet management commands."""
    pass

@subnet.command()
@click.option('--name', required=True, help='Name of the subnet')
@click.option('--validator', required=True, help='Name of the validator to use')
@click.option('--base-dir', default='moderntensor', help='Base directory for storing keys')
def create(name, validator, base_dir):
    """Create a new subnet."""
    try:
        manager = AccountManager(base_dir)
        manager.create_subnet(name, validator)
        click.echo(f"Successfully created subnet: {name}")
    except Exception as e:
        click.echo(f"Error creating subnet: {str(e)}", err=True)

if __name__ == '__main__':
    cli() 
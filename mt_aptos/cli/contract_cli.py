#!/usr/bin/env python3
"""
Contract CLI cho ModernTensor SDK
Quản lý smart contracts: compile, test, deploy
"""

import click
import json
from pathlib import Path
from moderntensor.mt_aptos.smartcontract.contract_manager import (
    get_default_contract_manager, 
    get_sdk_contract_info,
    compile_sdk_contracts
)


@click.group()
def contract():
    """Smart contract management commands."""
    pass


@contract.command()
def info():
    """Display information about SDK contracts."""
    try:
        contract_info = get_sdk_contract_info()
        
        click.echo("📋 MODERNTENSOR SDK CONTRACTS INFO")
        click.echo("=" * 50)
        click.echo(f"📁 Base Directory: {contract_info['base_dir']}")
        click.echo(f"📄 Move.toml: {contract_info['move_toml']}")
        click.echo(f"📂 Sources Directory: {contract_info['sources_dir']}")
        click.echo(f"🔧 Compiled: {'✅ Yes' if contract_info['compiled'] else '❌ No'}")
        
        if contract_info['compiled']:
            click.echo(f"🏗️ Build Directory: {contract_info['build_dir']}")
        
        click.echo()
        click.echo("📜 Available Contracts:")
        if contract_info['contracts']:
            for contract in contract_info['contracts']:
                size_kb = contract['size'] / 1024
                click.echo(f"   • {contract['name']}.move ({size_kb:.1f} KB)")
        else:
            click.echo("   No contracts found")
            
    except Exception as e:
        click.echo(f"❌ Error getting contract info: {str(e)}", err=True)


@contract.command()
@click.option('--network', default='testnet', help='Target network (testnet, mainnet, devnet)')
def compile(network):
    """Compile SDK contracts."""
    try:
        click.echo(f"🔧 Compiling ModernTensor contracts for {network}...")
        
        manager = get_default_contract_manager()
        success = manager.compile_contracts(network)
        
        if success:
            click.echo("✅ Contract compilation successful!")
            
            # Display contract info after compilation
            contract_info = get_sdk_contract_info()
            click.echo(f"🏗️ Build artifacts created in: {contract_info.get('build_dir', 'N/A')}")
        else:
            click.echo("❌ Contract compilation failed!", err=True)
            
    except Exception as e:
        click.echo(f"❌ Error during compilation: {str(e)}", err=True)


@contract.command()
def test():
    """Run tests for SDK contracts."""
    try:
        click.echo("🧪 Running ModernTensor contract tests...")
        
        manager = get_default_contract_manager()
        success = manager.test_contracts()
        
        if success:
            click.echo("✅ All contract tests passed!")
        else:
            click.echo("❌ Contract tests failed!", err=True)
            
    except Exception as e:
        click.echo(f"❌ Error during testing: {str(e)}", err=True)


@contract.command()
@click.option('--network', default='testnet', help='Target network (testnet, mainnet, devnet)')
@click.option('--private-key', help='Private key for signing transactions')
@click.confirmation_option(prompt='Are you sure you want to publish contracts?')
def publish(network, private_key):
    """Publish SDK contracts to blockchain."""
    try:
        click.echo(f"🚀 Publishing ModernTensor contracts to {network}...")
        
        manager = get_default_contract_manager()
        success = manager.publish_contracts(network, private_key)
        
        if success:
            click.echo("✅ Contract publication successful!")
            click.echo("🎉 Contracts are now live on the blockchain!")
        else:
            click.echo("❌ Contract publication failed!", err=True)
            
    except Exception as e:
        click.echo(f"❌ Error during publication: {str(e)}", err=True)


@contract.command()
@click.option('--contract', default='full_moderntensor', help='Contract name to get ABI for')
def abi(contract):
    """Get ABI for a compiled contract."""
    try:
        manager = get_default_contract_manager()
        contract_abi = manager.get_contract_abi(contract)
        
        if contract_abi:
            click.echo(f"📋 ABI for contract '{contract}':")
            click.echo(json.dumps(contract_abi, indent=2))
        else:
            click.echo(f"❌ ABI not found for contract '{contract}'", err=True)
            click.echo("💡 Try compiling the contracts first with: contract compile")
            
    except Exception as e:
        click.echo(f"❌ Error getting contract ABI: {str(e)}", err=True)


@contract.command()
@click.confirmation_option(prompt='Are you sure you want to clean build artifacts?')
def clean():
    """Clean build artifacts."""
    try:
        click.echo("🧹 Cleaning build artifacts...")
        
        manager = get_default_contract_manager()
        success = manager.clean_build()
        
        if success:
            click.echo("✅ Build artifacts cleaned!")
        else:
            click.echo("❌ Failed to clean build artifacts!", err=True)
            
    except Exception as e:
        click.echo(f"❌ Error during cleanup: {str(e)}", err=True)


@contract.command()
def structure():
    """Display SDK contract structure."""
    try:
        manager = get_default_contract_manager()
        base_dir = manager.base_dir
        
        click.echo("📁 MODERNTENSOR SDK CONTRACT STRUCTURE")
        click.echo("=" * 50)
        click.echo(f"📂 {base_dir}/")
        click.echo(f"├── 📄 Move.toml                    # Move package configuration")
        click.echo(f"├── 📂 sources/                     # Contract source files")
        click.echo(f"│   └── 📜 moderntensor.move        # Main ModernTensor contract")
        click.echo(f"└── 📂 build/                       # Compiled artifacts (auto-generated)")
        click.echo()
        click.echo("🎯 MAIN CONTRACT MODULES:")
        click.echo("├── 🏦 ValidatorInfo struct         # Complete validator data")
        click.echo("├── ⛏️  MinerInfo struct            # Complete miner data") 
        click.echo("├── 📝 register_validator()         # Validator registration")
        click.echo("├── 📝 register_miner()             # Miner registration")
        click.echo("├── 🔄 update_*_performance()       # Performance updates")
        click.echo("└── 👀 view functions               # Query functions")
        
    except Exception as e:
        click.echo(f"❌ Error displaying structure: {str(e)}", err=True)


if __name__ == '__main__':
    contract() 
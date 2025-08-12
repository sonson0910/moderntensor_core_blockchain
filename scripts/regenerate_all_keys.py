#!/usr/bin/env python3
"""
REGENERATE ALL KEYS FOR MODERNTENSOR PROJECT
Tạo lại tất cả keys và register lên blockchain
"""""
import os
import sys
from pathlib import Path
from eth_account import Account
from web3 import Web3
import time

# Add paths
project_root  =  Path(__file__).parent
sys.path.insert(0, str(project_root))

def generate_new_entities():
    """Generate brand new keys for all entities"""""
    print("🔥 REGENERATING ALL KEYS FOR MODERNTENSOR PROJECT")
    print(" = " * 60)
    
    entities  =  {}
    
    # Generate 2 miners
    for i in range(1, 3):
        account  =  Account.create()
        entities[f"miner_{i}"]  =  {
            "name": f"miner_{i}_localhost",
            "type": "miner",
            "address": account.address,
            "private_key": account.key.hex()[2:],  # Remove 0x prefix
            "port": 8100 + i,
            "api_endpoint": f"http://localhost:{8100 + i}",
            "stake": "0.05"
        }
        print(f"✅ Generated Miner {i}: {account.address}")
    
    # Generate 2 validators
    for i in range(1, 3):
        account  =  Account.create()
        entities[f"validator_{i}"]  =  {
            "name": f"validator_{i}_localhost",
            "type": "validator", 
            "address": account.address,
            "private_key": account.key.hex()[2:],  # Remove 0x prefix
            "port": 8000 + i,
            "api_endpoint": f"http://localhost:{8000 + i}",
            "stake": "0.08"
        }
        print(f"✅ Generated Validator {i}: {account.address}")
    
    return entities

def update_env_file(entities):
    """Update .env file with new entities"""""
    print("\n📝 UPDATING .ENV FILE...")
    print("-" * 30)
    
    env_file  =  project_root.parent / "subnet1_aptos" / ".env"
    
    # Read existing .env
    existing_lines  =  []
    if env_file.exists():
        with open(env_file, 'r') as f:
            existing_lines  =  f.readlines()
    
    # Create new .env content
    new_env_content = f"""# ============================================================================="""
# ModernTensor Core DAO Configuration - REGENERATED {time.strftime('%Y-%m-%d %H:%M:%S')}
# Environment variables for Subnet1 Miner and Validator Scripts:
# =============================================================================

# --- CORE BLOCKCHAIN CONFIGURATION ---
CORE_NODE_URL = https://rpc.test.btcs.network
CORE_CONTRACT_ADDRESS = 0x6C1f1e9B1196AA11c0A0C799e62Ab2248695276d
CORE_TOKEN_ADDRESS = 0x7B74e4868c8C500D6143CEa53a5d2F94e94c7637
BTC_TOKEN_ADDRESS = 0x44Ed1441D79FfCb76b7D6644dBa930309E0E6F31

# --- LOGGING CONFIGURATION ---
LOG_LEVEL = INFO

# =============================================================================
# MINER CONFIGURATION - NEW KEYS
# =============================================================================

# --- MINER SELECTION ---
MINER_ID = 1

# --- MINER 1 CONFIGURATION (NEW) ---
MINER_1_PRIVATE_KEY = {entities['miner_1']['private_key']}
MINER_1_ADDRESS = {entities['miner_1']['address']}
MINER_1_API_ENDPOINT = {entities['miner_1']['api_endpoint']}
MINER_1_PORT = {entities['miner_1']['port']}

# --- MINER 2 CONFIGURATION (NEW) ---
MINER_2_PRIVATE_KEY = {entities['miner_2']['private_key']}
MINER_2_ADDRESS = {entities['miner_2']['address']}
MINER_2_API_ENDPOINT = {entities['miner_2']['api_endpoint']}
MINER_2_PORT = {entities['miner_2']['port']}

# --- MINER GENERAL SETTINGS ---
SUBNET1_MINER_HOST = 0.0.0.0
MINER_AGENT_CHECK_INTERVAL = 300

# =============================================================================
# VALIDATOR CONFIGURATION - NEW KEYS
# =============================================================================

# --- PRIMARY VALIDATOR (VALIDATOR 1) (NEW) ---
SUBNET1_VALIDATOR_ID = subnet1_validator_001
CORE_PRIVATE_KEY = {entities['validator_1']['private_key']}
VALIDATOR_API_ENDPOINT = {entities['validator_1']['api_endpoint']}
SUBNET1_VALIDATOR_HOST = 0.0.0.0
SUBNET1_VALIDATOR_PORT = {entities['validator_1']['port']}

# --- VALIDATOR 1 DETAILS (NEW) ---
VALIDATOR_1_API_ENDPOINT = {entities['validator_1']['api_endpoint']}
VALIDATOR_1_ADDRESS = {entities['validator_1']['address']}
VALIDATOR_1_PRIVATE_KEY = {entities['validator_1']['private_key']}

# --- VALIDATOR 2 DETAILS (NEW) ---
VALIDATOR_2_API_ENDPOINT = {entities['validator_2']['api_endpoint']}
VALIDATOR_2_ADDRESS = {entities['validator_2']['address']}
VALIDATOR_2_PRIVATE_KEY = {entities['validator_2']['private_key']}

# =============================================================================
# VALIDATOR V2 SCRIPT COMPATIBILITY
# =============================================================================

# Default to Validator 2 for run_validator_core_v2.py:
VALIDATOR_ID = 2

# Validator 2 mapping for script compatibility:
VALIDATOR_2_ID = validator_2_localhost
VALIDATOR_2_HOST = 0.0.0.0
VALIDATOR_2_PORT = {entities['validator_2']['port']}

# Validator 1 mapping for script compatibility  :
VALIDATOR_1_ID = validator_1_localhost
VALIDATOR_1_HOST = 0.0.0.0
VALIDATOR_1_PORT = {entities['validator_1']['port']}

# =============================================================================
# NETWORK AND API CONFIGURATION
# =============================================================================

# --- SUBNET CONFIGURATION ---
SUBNET_ID = 1
SUBNET_NAME = subnet1

# --- DEPLOYMENT WALLET (for reference) ---:
DEPLOYER_ADDRESS = 0x2F7E209E0F7B8F0C2B7e8D8C5D5A5B5C5D5E5F5A
DEPLOYER_PRIVATE_KEY = a07b6e0db803f9a21ffd1001c76b0aa0b313aaba8faab8c771af47301c4452b4

# =============================================================================
# STAKING CONFIGURATION
# =============================================================================

# --- MINIMUM STAKES (Ultra-Low for Testnet) ---:
MIN_MINER_STAKE = 0.05
MIN_VALIDATOR_STAKE = 0.08

# --- GAS RESERVES ---
MINER_GAS_RESERVE = 0.95
VALIDATOR_GAS_RESERVE = 0.92

# =============================================================================
# DEVELOPMENT/DEBUG SETTINGS
# =============================================================================

# --- DEVELOPMENT FLAGS ---
DEBUG_MODE = false
VERBOSE_LOGGING = false
TEST_MODE = false

# --- TIMING SETTINGS ---
CONSENSUS_INTERVAL = 60
TASK_TIMEOUT = 300
VALIDATION_TIMEOUT = 180

# =============================================================================
# BACKUP CONFIGURATION (Optional)
# =============================================================================

# --- BACKUP RPC URLS ---
CORE_NODE_URL_BACKUP = https://rpc.coredao.org
CORE_NODE_URL_LOCAL = http://localhost:8545

# --- MONITORING ---
HEALTH_CHECK_INTERVAL = 30
METRICS_PORT = 9090

# =============================================================================
# END OF CONFIGURATION
# =============================================================================
"""
    
    # Write new .env
    with open(env_file, 'w') as f:
        f.write(new_env_content)
    
    print(f"""✅ Updated .env file: {env_file}")
    
    # Display summary
    print("\n📋 NEW ENTITY SUMMARY:")
    print("-" * 30)
    for entity_name, data in entities.items():
        print(f"🔑 {entity_name.upper()}:")
        print(f"   Address: {data['address']}")
        print(f"   Endpoint: {data['api_endpoint']}")
        print(f"   Private Key: {data['private_key'][:16]}...")
        print()

def create_registration_script(entities):
    """Create registration script for new entities"""""
    print("\n🚀 CREATING REGISTRATION SCRIPT...")
    print("-" * 30)
    
    script_content  =  f'''#!/usr/bin/env python3
"""
AUTO-GENERATED REGISTRATION SCRIPT FOR NEW ENTITIES
Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}
"""""
import os
import sys
from pathlib import Path
from web3 import Web3
from eth_account import Account
import json

# Add paths
project_root  =  Path(__file__).parent
sys.path.insert(0, str(project_root))

def register_all_entities():
    """Register all new entities on blockchain"""""
    print("🚀 REGISTERING ALL NEW ENTITIES ON CORE BLOCKCHAIN")
    print(" = " * 60)
    
    # Core blockchain configuration
    rpc_url  =  "https://rpc.test.btcs.network"
    contract_address  =  "0x6C1f1e9B1196AA11c0A0C799e62Ab2248695276d"
    deployer_private_key  =  "a07b6e0db803f9a21ffd1001c76b0aa0b313aaba8faab8c771af47301c4452b4"
    
    # Connect to Core blockchain
    w3  =  Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        print("❌ Failed to connect to Core blockchain")
        return False
    
    print(f"✅ Connected to Core blockchain: {{w3.eth.chain_id}}")
    
    # Load contract ABI
    abi_path  =  project_root / "mt_core" / "smartcontract" / "artifacts" / "contracts" / "ModernTensorAI_v2_Bittensor.sol" / "ModernTensorAI_v2_Bittensor.json"
    with open(abi_path, 'r') as f:
        contract_data  =  json.load(f)
        contract_abi  =  contract_data['abi']
    
    contract = w3.eth.contract(address=contract_address, abi = contract_abi)
    deployer_account  =  w3.eth.account.from_key(deployer_private_key)
    
    # New entities to register
    entities  =  [
        # Miners
        {{"name": "miner_1", "address": "{entities['miner_1']['address']}", "private_key": "{entities['miner_1']['private_key']}", "type": "miner", "stake": "0.05", "endpoint": "{entities['miner_1']['api_endpoint']}"}},
        {{"name": "miner_2", "address": "{entities['miner_2']['address']}", "private_key": "{entities['miner_2']['private_key']}", "type": "miner", "stake": "0.05", "endpoint": "{entities['miner_2']['api_endpoint']}"}},
        
        # Validators
        {{"name": "validator_1", "address": "{entities['validator_1']['address']}", "private_key": "{entities['validator_1']['private_key']}", "type": "validator", "stake": "0.08", "endpoint": "{entities['validator_1']['api_endpoint']}"}},
        {{"name": "validator_2", "address": "{entities['validator_2']['address']}", "private_key": "{entities['validator_2']['private_key']}", "type": "validator", "stake": "0.08", "endpoint": "{entities['validator_2']['api_endpoint']}"}},
    ]
    
    # Step 1: Transfer gas to all entities
    print("\\n💰 TRANSFERRING GAS TO ALL ENTITIES...")
    for entity in entities:
        try:
            balance  =  w3.eth.get_balance(entity["address"])
            balance_eth  =  w3.from_wei(balance, 'ether')
            
            if balance_eth < 1.0:  # If less than 1 CORE:
                gas_amount  =  w3.to_wei(1.5, 'ether')  # Send 1.5 CORE for gas:
                
                transfer_txn  =  {{
                    'to': entity["address"],
                    'value': gas_amount,
                    'gas': 21000,
                    'gasPrice': w3.to_wei(20, 'gwei'),
                    'nonce': w3.eth.get_transaction_count(deployer_account.address),
                }}
                
                signed_txn  =  w3.eth.account.sign_transaction(transfer_txn, deployer_private_key)
                tx_hash  =  w3.eth.send_raw_transaction(signed_txn.rawTransaction)
                print(f"   ✅ {{entity['name']}}: Sent 1.5 CORE for gas - {{tx_hash.hex()}}"):
                
                # Wait for confirmation:
                receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout = 120)
                if receipt.status == 1:
                    print(f"      ✅ Gas transfer confirmed for {{entity['name']}}"):
                else:
                    print(f"      ❌ Gas transfer failed for {{entity['name']}}"):
            else:
                print(f"   ✅ {{entity['name']}}: Already has {{balance_eth:.4f}} CORE")
                
        except Exception as e:
            print(f"   ❌ {{entity['name']}}: Gas transfer error - {{e}}")
    
    # Step 2: Register all entities
    print("\\n📝 REGISTERING ENTITIES ON BLOCKCHAIN...")
    for entity in entities:
        try:
            account  =  w3.eth.account.from_key(entity["private_key"])
            
            # Check if already registered:
            if entity["type"] == "miner":
                try:
                    existing  =  contract.functions.getMinerInfo(entity["address"]).call()
                    if existing[9] > 0:  # status > 0 means registered:
                        print(f"   ⚠️  {{entity['name']}}: Already registered")
                        continue
                except:
                    pass  # Not registered, continue
            else:  # validator:
                try:
                    existing  =  contract.functions.getValidatorInfo(entity["address"]).call()
                    if existing[9] > 0:  # status > 0 means registered:
                        print(f"   ⚠️  {{entity['name']}}: Already registered")
                        continue
                except:
                    pass  # Not registered, continue
            
            # Register entity
            if entity["type"] == "miner":
                register_txn  =  contract.functions.registerMiner
                ).build_transaction
                    'gasPrice': w3.to_wei(20, 'gwei'),
                    'nonce': w3.eth.get_transaction_count(entity["address"]),
                }})
            else:  # validator:
                register_txn  =  contract.functions.registerValidator
                ).build_transaction
                    'gasPrice': w3.to_wei(20, 'gwei'),
                    'nonce': w3.eth.get_transaction_count(entity["address"]),
                }})
            
            # Sign and send
            signed_register  =  w3.eth.account.sign_transaction(register_txn, entity["private_key"])
            tx_hash  =  w3.eth.send_raw_transaction(signed_register.rawTransaction)
            print(f"   🚀 {{entity['name']}}: Registration sent - {{tx_hash.hex()}}")
            
            # Wait for confirmation:
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout = 120)
            if receipt.status == 1:
                print(f"      ✅ {{entity['name']}}: Registration confirmed!")
            else:
                print(f"      ❌ {{entity['name']}}: Registration failed!")
                
        except Exception as e:
            print(f"   ❌ {{entity['name']}}: Registration error - {{e}}")
    
    print("\\n🎉 REGISTRATION COMPLETE!")
    print(" = " * 60)
    return True

if __name__ == "__main__":
    register_all_entities()
'''
    
    # Write registration script
    script_path  =  project_root.parent / "subnet1_aptos" / "register_new_entities.py"
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    print(f"✅ Created registration script: {script_path}")
    return script_path

def main():
    """Main regeneration process"""""
    try:
        # Step 1: Generate new entities
        entities  =  generate_new_entities()
        
        # Step 2: Update .env file
        update_env_file(entities)
        
        # Step 3: Create registration script
        script_path  =  create_registration_script(entities)
        
        print("\n" + " = " * 60)
        print("🎉 REGENERATION COMPLETE!")
        print(" = " * 60)
        print("\n📋 NEXT STEPS:")
        print("1. ✅ New keys generated")
        print("2. ✅ .env file updated")
        print("3. ✅ Registration script created")
        print(f"4. 🚀 Run registration: python {script_path.name}")
        print("\n💡 All old keys are replaced with brand new ones!")
        print("💡 Ports are correctly configured:")
        print("   - Miner 1: Port 8101")
        print("   - Miner 2: Port 8102") 
        print("   - Validator 1: Port 8001")
        print("   - Validator 2: Port 8002")
        
        return True
        
    except Exception as e:
        print(f"\n💥 ERROR DURING REGENERATION: {e}")
        return False

if __name__ == "__main__":
    success  =  main()
    if success:
        print("\n✅ SUCCESS: Project regenerated successfully!")
    else:
        print("\n❌ FAILED: Project regeneration failed!")
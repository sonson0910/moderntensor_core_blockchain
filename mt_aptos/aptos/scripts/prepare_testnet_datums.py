# File: sdk/aptos/scripts/prepare_aptos_testnet.py
# Chuẩn bị và gửi các dữ liệu ban đầu cho Miners và Validators lên Aptos Testnet.

import os
import sys
import logging
import asyncio
import hashlib
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional, List, Dict, Any
from rich.logging import RichHandler
from rich.console import Console

# Import Aptos SDK
from mt_aptos.account import Account, AccountAddress
from mt_aptos.async_client import RestClient
from mt_aptos.bcs import Serializer
from mt_aptos.transactions import EntryFunction, TransactionArgument

# --- Thêm đường dẫn gốc của project vào sys.path ---
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))
# -------------------------------------------------

# Import các thành phần cần thiết từ SDK ModernTensor
try:
    from mt_aptos.metagraph.metagraph_datum import STATUS_ACTIVE
    from mt_aptos.core.datatypes import MinerInfo, ValidatorInfo
    from mt_aptos.aptos import ModernTensorClient
    from mt_aptos.keymanager.wallet_manager import WalletManager
    from mt_aptos.config.settings import settings as sdk_settings
except ImportError as e:
    print(f"❌ FATAL: Import Error in prepare_aptos_testnet.py: {e}")
    sys.exit(1)

# --- Tải biến môi trường ---
env_path = project_root / ".env"

# --- Cấu hình Logging với RichHandler ---
log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
log_level = getattr(logging, log_level_str, logging.INFO)
rich_handler = RichHandler(
    show_time=True,
    show_level=True,
    show_path=False,
    markup=True,
    rich_tracebacks=True,
    log_time_format="[%Y-%m-%d %H:%M:%S]",
)
logging.basicConfig(
    level=log_level, format="%(message)s", datefmt="[%X]", handlers=[rich_handler]
)
logger = logging.getLogger(__name__)
console = Console()

# ------------------------

# --- Tải biến môi trường (sau khi logger được cấu hình) ---
if env_path.exists():
    logger.info(f"📄 Loading environment variables from: {env_path}")
    load_dotenv(dotenv_path=env_path, override=True)
else:
    logger.warning(f"📄 Environment file (.env) not found at {env_path}.")
# --------------------------

# --- Lấy cấu hình ví Funding ---
FUNDING_COLDKEY_NAME = os.getenv("FUNDING_COLDKEY_NAME", "kickoff")
FUNDING_HOTKEY_NAME = os.getenv("FUNDING_HOTKEY_NAME", "hk1")
FUNDING_PASSWORD = os.getenv("FUNDING_PASSWORD")
HOTKEY_BASE_DIR = os.getenv(
    "HOTKEY_BASE_DIR", getattr(sdk_settings, "HOTKEY_BASE_DIR", "moderntensor")
)

# Aptos configuration
APTOS_NODE_URL = os.getenv("APTOS_NODE_URL", sdk_settings.APTOS_NODE_URL)
APTOS_CONTRACT_ADDRESS = os.getenv("APTOS_CONTRACT_ADDRESS", sdk_settings.APTOS_CONTRACT_ADDRESS)
APTOS_NETWORK = os.getenv("APTOS_NETWORK", sdk_settings.APTOS_NETWORK)

# --- Kiểm tra các biến môi trường bắt buộc ---
required_env_vars = {
    "SUBNET1_MINER_ID": os.getenv("SUBNET1_MINER_ID"),
    "SUBNET1_VALIDATOR_UID": os.getenv("SUBNET1_VALIDATOR_UID"),
    "FUNDING_COLDKEY_NAME": FUNDING_COLDKEY_NAME,
    "FUNDING_HOTKEY_NAME": FUNDING_HOTKEY_NAME,
    "FUNDING_PASSWORD": FUNDING_PASSWORD,
    "APTOS_CONTRACT_ADDRESS": APTOS_CONTRACT_ADDRESS,
}
missing_vars = [k for k, v in required_env_vars.items() if not v]
if missing_vars:
    logger.error(
        f"FATAL: Missing required environment variables: {', '.join(missing_vars)}"
    )
    sys.exit(1)
# --------------------------------------------------

# === Constants ===
SUBNET_ID_TO_USE = 1


# === Helper Functions ===
def load_funding_account(
    base_dir: str, coldkey_name: str, hotkey_name: str, password: str
) -> Account:
    """Loads funding account from wallet."""
    logger.info(
        f"🔑 Loading funding account (Cold: '{coldkey_name}', Hot: '{hotkey_name}')..."
    )
    try:
        wm = WalletManager(network=APTOS_NETWORK, base_dir=base_dir)
        key_info = wm.get_hotkey_info(coldkey_name, hotkey_name)
        
        if not key_info or "encrypted_data" not in key_info:
            raise ValueError(f"Could not find hotkey data for {hotkey_name}")
        
        # Load the coldkey to decrypt the hotkey
        coldkey_data = wm.load_coldkey(coldkey_name, password)
        if not coldkey_data:
            raise ValueError(f"Failed to load coldkey {coldkey_name}")
        
        # Get the private key from the encrypted data
        from mt_aptos.keymanager.decryption_utils import decode_hotkey_data
        private_key = decode_hotkey_data(key_info["encrypted_data"], password)
        
        # Create Account from private key
        account = Account.load_key(private_key)
        
        logger.info(f"✅ Funding account loaded. Address: [cyan]{account.address().hex()}[/]")
        return account
    except Exception as e:
        logger.exception(f"💥 Failed to load funding account: {e}")
        raise


# === Main Async Function ===
async def prepare_datums():
    """Main async function to prepare and submit initial datums to Aptos."""
    logger.info(
        "✨ --- Starting Aptos Datum Preparation Script --- ✨"
    )

    # --- Load Funding Account ---
    try:
        hotkey_base_dir = os.getenv(
            "HOTKEY_BASE_DIR", getattr(sdk_settings, "HOTKEY_BASE_DIR", "moderntensor")
        )
        funding_coldkey = os.getenv("FUNDING_COLDKEY_NAME", "kickoff")
        funding_hotkey = os.getenv("FUNDING_HOTKEY_NAME", "hk1")
        funding_password = os.getenv("FUNDING_PASSWORD")

        if not funding_coldkey:
            raise ValueError(
                "FUNDING_COLDKEY_NAME is missing or empty in .env and no default specified."
            )
        if not funding_hotkey:
            raise ValueError(
                "FUNDING_HOTKEY_NAME is missing or empty in .env and no default specified."
            )
        if not funding_password:
            raise ValueError("FUNDING_PASSWORD environment variable is not set.")
        if not hotkey_base_dir:
            raise ValueError(
                "Could not determine HOTKEY_BASE_DIR (checked .env and sdk_settings)."
            )

        funding_account = load_funding_account(
            hotkey_base_dir, funding_coldkey, funding_hotkey, funding_password
        )
    except Exception as fund_err:
        logger.exception(f"💥 Error loading funding account: {fund_err}")
        sys.exit(1)

    # --- Create Aptos Client ---
    try:
        logger.info(f"🌐 Connecting to Aptos node at {APTOS_NODE_URL}...")
        rest_client = RestClient(APTOS_NODE_URL)
        
        # Check if the node is reachable
        ledger_info = await rest_client.ledger_information()
        logger.info(f"✅ Connected to Aptos node. Chain ID: {ledger_info.get('chain_id')}")
        
        # Create ModernTensor client
        client = ModernTensorClient(
            account=funding_account,
            node_url=APTOS_NODE_URL,
            contract_address=APTOS_CONTRACT_ADDRESS
        )
    except Exception as client_err:
        logger.exception(f"💥 Error creating Aptos client: {client_err}")
        sys.exit(1)

    # --- Load Initial Validators and Miners Info from .env ---
    logger.info("👥 Loading initial validator and miner configurations from .env...")
    validators_info: List[ValidatorInfo] = []
    miners_info: List[MinerInfo] = []

    try:
        # -- Validators --
        subnet1_validator_uid = os.getenv("SUBNET1_VALIDATOR_UID")
        if subnet1_validator_uid:
            # Generate a validator address - this would typically be a wallet address
            validator_address = os.getenv("SUBNET1_VALIDATOR_ADDRESS", funding_account.address().hex())
            validator_api = os.getenv("SUBNET1_VALIDATOR_API", "http://localhost:8001")
            
            validator_info = ValidatorInfo(
                uid=subnet1_validator_uid,
                address=validator_address,
                api_endpoint=validator_api,
                trust_score=0.5,  # Initial trust score
                weight=1.0,       # Initial weight
                stake=1000 * 10**8,  # 1000 APT in octas
                subnet_uid=SUBNET_ID_TO_USE,
                status=STATUS_ACTIVE,
                registration_time=int(ledger_info.get('ledger_timestamp', '0')) // 1_000_000  # Convert to seconds
            )
            validators_info.append(validator_info)
            logger.info(f"✅ Added validator: {validator_info.uid} at {validator_info.api_endpoint}")
        
        # -- Miners --
        subnet1_miner_id = os.getenv("SUBNET1_MINER_ID")
        if subnet1_miner_id:
            # Generate a miner address - this would typically be a wallet address
            miner_address = os.getenv("SUBNET1_MINER_ADDRESS", "0x" + os.urandom(32).hex()[:40])
            miner_api = os.getenv("SUBNET1_MINER_API", "http://localhost:8002")
            
            miner_info = MinerInfo(
                uid=subnet1_miner_id,
                address=miner_address,
                api_endpoint=miner_api,
                trust_score=0.5,  # Initial trust score
                weight=1.0,       # Initial weight
                stake=500 * 10**8,  # 500 APT in octas
                subnet_uid=SUBNET_ID_TO_USE,
                status=STATUS_ACTIVE,
                registration_time=int(ledger_info.get('ledger_timestamp', '0')) // 1_000_000  # Convert to seconds
            )
            miners_info.append(miner_info)
            logger.info(f"✅ Added miner: {miner_info.uid} at {miner_info.api_endpoint}")
    except Exception as info_err:
        logger.exception(f"💥 Error creating validator/miner info: {info_err}")
        sys.exit(1)

    # --- Check Funding Account Balance ---
    try:
        resources = await rest_client.account_resources(funding_account.address().hex())
        apt_balance = None
        for resource in resources:
            if resource["type"] == "0x1::coin::CoinStore<0x1::aptos_coin::AptosCoin>":
                apt_balance = int(resource["data"]["coin"]["value"]) / 10**8
                break
        
        if apt_balance is not None:
            logger.info(f"💰 Funding Account Balance: {apt_balance} APT")
            if apt_balance < 10:
                logger.warning(f"⚠️ Low balance! Only {apt_balance} APT available. Consider getting more tokens.")
        else:
            logger.warning("⚠️ Could not determine funding account balance.")
    except Exception as balance_err:
        logger.exception(f"💥 Error checking account balance: {balance_err}")
        # Continue even if balance check fails

    # --- Create Subnet if needed ---
    try:
        # Check if subnet exists
        subnet_exists = await client.subnet_exists(SUBNET_ID_TO_USE)
        
        if not subnet_exists:
            logger.info(f"🌐 Creating subnet with ID {SUBNET_ID_TO_USE}...")
            
            # Create subnet transaction
            result = await client.create_subnet(
                subnet_id=SUBNET_ID_TO_USE,
                name="TestSubnet",
                description="Test subnet for ModernTensor on Aptos",
                owner=funding_account.address().hex(),
                min_stake_validator=1000 * 10**8,  # 1000 APT in octas
                min_stake_miner=500 * 10**8,      # 500 APT in octas
                max_validators=100,
                max_miners=1000,
                registration_open=True
            )
            
            if result and "hash" in result:
                logger.info(f"✅ Subnet created. Transaction hash: {result['hash']}")
                # Wait a bit for transaction to be processed
                logger.info("⏳ Waiting for transaction to be processed...")
                await asyncio.sleep(5)
            else:
                logger.error(f"❌ Failed to create subnet: {result}")
                sys.exit(1)
        else:
            logger.info(f"✅ Subnet {SUBNET_ID_TO_USE} already exists.")
    except Exception as subnet_err:
        logger.exception(f"💥 Error creating subnet: {subnet_err}")
        sys.exit(1)

    # --- Register Validators ---
    for validator in validators_info:
        try:
            logger.info(f"🔍 Checking if validator {validator.uid} is already registered...")
            validator_exists = await client.validator_exists(validator.uid)
            
            if not validator_exists:
                logger.info(f"🔄 Registering validator {validator.uid}...")
                result = await client.register_validator(
                    subnet_id=validator.subnet_uid,
                    validator_uid=validator.uid,
                    address=validator.address,
                    api_endpoint=validator.api_endpoint or "",
                    stake_amount=validator.stake
                )
                
                if result and "hash" in result:
                    logger.info(f"✅ Validator registered. Transaction hash: {result['hash']}")
                    # Wait a bit for transaction to be processed
                    await asyncio.sleep(5)
                else:
                    logger.error(f"❌ Failed to register validator: {result}")
            else:
                logger.info(f"✅ Validator {validator.uid} already registered.")
        except Exception as val_err:
            logger.exception(f"💥 Error registering validator {validator.uid}: {val_err}")

    # --- Register Miners ---
    for miner in miners_info:
        try:
            logger.info(f"🔍 Checking if miner {miner.uid} is already registered...")
            miner_exists = await client.miner_exists(miner.uid)
            
            if not miner_exists:
                logger.info(f"🔄 Registering miner {miner.uid}...")
                result = await client.register_miner(
                    subnet_id=miner.subnet_uid,
                    miner_uid=miner.uid,
                    address=miner.address,
                    api_endpoint=miner.api_endpoint or "",
                    stake_amount=miner.stake
                )
                
                if result and "hash" in result:
                    logger.info(f"✅ Miner registered. Transaction hash: {result['hash']}")
                    # Wait a bit for transaction to be processed
                    await asyncio.sleep(5)
                else:
                    logger.error(f"❌ Failed to register miner: {result}")
            else:
                logger.info(f"✅ Miner {miner.uid} already registered.")
        except Exception as miner_err:
            logger.exception(f"💥 Error registering miner {miner.uid}: {miner_err}")

    # --- Show Summary ---
    logger.info("📋 Summary of operations:")
    logger.info(f"  - Subnet created/confirmed: ID {SUBNET_ID_TO_USE}")
    logger.info(f"  - Validators registered: {len(validators_info)}")
    logger.info(f"  - Miners registered: {len(miners_info)}")
    
    # Link to explorer
    explorer_url = f"https://explorer.aptoslabs.com/account/{APTOS_CONTRACT_ADDRESS}?network={APTOS_NETWORK}"
    logger.info(f"🔗 View contract on explorer: {explorer_url}")
    
    logger.info("✨ Datum preparation completed! ✨")


if __name__ == "__main__":
    try:
        asyncio.run(prepare_datums())
    except KeyboardInterrupt:
        logger.info("🛑 Script interrupted by user.")
    except Exception as e:
        logger.exception(f"💥 Unhandled error: {e}")
        sys.exit(1)

#!/usr/bin/env python3
"""
Create .env file for subnet1_aptos with correct configuration
"""


def create_env_file():
    print("📝 CREATING .ENV FILE FOR SUBNET1_APTOS")
    print("=" * 50)

    env_content = """# ==========================================
# ModernTensor Subnet1 Configuration
# ==========================================

# Core Blockchain Configuration
CORE_NODE_URL=https://rpc.test.btcs.network
CORE_CHAIN_ID=1115
CORE_CONTRACT_ADDRESS=0x594fc12B3e3AB824537b947765dd9409DAAAa143

# Token Addresses
CORE_TOKEN_ADDRESS=0x7B74e4868c8C500D6143CEa53a5d2F94e94c7637
BTC_TOKEN_ADDRESS=0x44Ed1441D79FfCb76b7D6644dBa930309E0E6F31

# Network Configuration
SUBNET_ID=1

# Validator Configuration
SUBNET1_VALIDATOR_ID=subnet1_validator_001
VALIDATOR_API_ENDPOINT=http://localhost:8001
SUBNET1_VALIDATOR_HOST=0.0.0.0
SUBNET1_VALIDATOR_PORT=8001

# Miner Configuration
SUBNET1_MINER_ID=subnet1_miner_001
SUBNET1_MINER_HOST=0.0.0.0
SUBNET1_MINER_PORT=9001

# Entity Private Keys (from entities/ directory)
# WARNING: These are test keys only - keep secure in production!
MINER_1_PRIVATE_KEY=e9c03148c011d553d43b485d73b1407d24f1498a664f782dc0204e524855be4e
MINER_2_PRIVATE_KEY=3ace434e2cd05cd0e614eb5d423cf04e4b925c17db9869e9c598851f88f52840
VALIDATOR_1_PRIVATE_KEY=3ac6e82cf34e51d376395af0338d0b1162c1d39b9d34614ed40186fd2367b33d
VALIDATOR_2_PRIVATE_KEY=df51093c674459eb0a5cc8a273418061fe4d7ca189bd84b74f478271714e0920
VALIDATOR_3_PRIVATE_KEY=7e2c40ab431ddf141322ed93531e8e4b2cda01bb25aa947d297b680b635b715c

# Entity Addresses
MINER_1_ADDRESS=0xd89fBAbb72190ed22F012ADFC693ad974bAD3005
MINER_2_ADDRESS=0x16102CA8BEF74fb6214AF352989b664BF0e50498
VALIDATOR_1_ADDRESS=0x25F3D6316017FDF7A4f4e54003b29212a198768f
VALIDATOR_2_ADDRESS=0x352516F491DFB3E6a55bFa9c58C551Ef10267dbB
VALIDATOR_3_ADDRESS=0x0469C6644c07F6e860Af368Af8104F8D8829a78e

# API Endpoints
MINER_1_ENDPOINT=http://localhost:8101
MINER_2_ENDPOINT=http://localhost:8102
VALIDATOR_1_ENDPOINT=http://localhost:8001
VALIDATOR_2_ENDPOINT=http://localhost:8002
VALIDATOR_3_ENDPOINT=http://localhost:8003

# Agent Configuration
MINER_AGENT_CHECK_INTERVAL=300
VALIDATOR_CHECK_INTERVAL=60

# Logging Configuration
LOG_LEVEL=INFO
PYTHONPATH=..:../moderntensor_aptos

# Development flags
DEBUG=false
DEVELOPMENT_MODE=true
"""

    try:
        with open(".env", "w") as f:
            f.write(env_content)

        print("✅ .env file created successfully!")
        print("\n📋 Configuration includes:")
        print("  - ✅ Updated contract address")
        print("  - ✅ All entity keys and addresses")
        print("  - ✅ API endpoints")
        print("  - ✅ Network configuration")
        print("  - ✅ Token addresses")

        print("\n🔐 Security Note:")
        print("  ⚠️ This .env contains test private keys")
        print("  ⚠️ DO NOT use in production")
        print("  ⚠️ Keep .env file secure and never commit to git")

        return True

    except Exception as e:
        print(f"❌ Error creating .env file: {e}")
        return False


if __name__ == "__main__":
    create_env_file()

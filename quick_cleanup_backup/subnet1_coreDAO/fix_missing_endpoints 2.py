#!/usr/bin/env python3
"""
Fix missing API endpoints in .env file
"""


def fix_missing_endpoints():
    print("🔧 FIXING MISSING API ENDPOINTS")
    print("=" * 50)

    # Read current .env file
    try:
        with open(".env", "r") as f:
            content = f.read()

        print("✅ Current .env file read successfully")

        # Missing endpoint variables
        missing_endpoints = """
# Individual API Endpoints (for scripts)
VALIDATOR_1_API_ENDPOINT=http://localhost:8001
VALIDATOR_2_API_ENDPOINT=http://localhost:8002
VALIDATOR_3_API_ENDPOINT=http://localhost:8003
MINER_1_API_ENDPOINT=http://localhost:8101
MINER_2_API_ENDPOINT=http://localhost:8102

# Port configurations
VALIDATOR_1_PORT=8001
VALIDATOR_2_PORT=8002
VALIDATOR_3_PORT=8003
MINER_1_PORT=8101
MINER_2_PORT=8102
"""

        # Check if these variables already exist
        if "VALIDATOR_1_API_ENDPOINT=" in content:
            print("⚠️ Endpoint variables already exist in .env file")
            return True

        # Find where to insert (before Entity Private Keys)
        insertion_point = content.find("# Entity Private Keys")
        if insertion_point == -1:
            # If not found, append at the end
            updated_content = content + missing_endpoints
        else:
            # Insert before the Entity Private Keys section
            updated_content = (
                content[:insertion_point]
                + missing_endpoints
                + "\n"
                + content[insertion_point:]
            )

        # Write updated content back
        with open(".env", "w") as f:
            f.write(updated_content)

        print("✅ .env file updated successfully!")
        print("\n📋 Added endpoints:")
        print(
            "  - VALIDATOR_1_API_ENDPOINT, VALIDATOR_2_API_ENDPOINT, VALIDATOR_3_API_ENDPOINT"
        )
        print("  - MINER_1_API_ENDPOINT, MINER_2_API_ENDPOINT")
        print("  - Port configurations for all entities")

        return True

    except Exception as e:
        print(f"❌ Error updating .env file: {e}")
        return False


def verify_all_variables():
    """Verify all required variables exist"""
    print("\n🔍 VERIFYING ALL ENVIRONMENT VARIABLES")
    print("=" * 50)

    # Load environment
    from dotenv import load_dotenv
    import os

    load_dotenv()

    # All required variables
    required_vars = {
        "Core Configuration": [
            "CORE_NODE_URL",
            "CORE_CONTRACT_ADDRESS",
            "CORE_TOKEN_ADDRESS",
            "SUBNET_ID",
        ],
        "Validator IDs": ["VALIDATOR_1_ID", "VALIDATOR_2_ID", "VALIDATOR_3_ID"],
        "Miner IDs": ["MINER_1_ID", "MINER_2_ID"],
        "Validator Keys": [
            "VALIDATOR_1_PRIVATE_KEY",
            "VALIDATOR_2_PRIVATE_KEY",
            "VALIDATOR_3_PRIVATE_KEY",
        ],
        "Miner Keys": ["MINER_1_PRIVATE_KEY", "MINER_2_PRIVATE_KEY"],
        "Validator Endpoints": [
            "VALIDATOR_1_API_ENDPOINT",
            "VALIDATOR_2_API_ENDPOINT",
            "VALIDATOR_3_API_ENDPOINT",
        ],
        "Miner Endpoints": ["MINER_1_API_ENDPOINT", "MINER_2_API_ENDPOINT"],
        "Entity Addresses": [
            "VALIDATOR_1_ADDRESS",
            "VALIDATOR_2_ADDRESS",
            "VALIDATOR_3_ADDRESS",
            "MINER_1_ADDRESS",
            "MINER_2_ADDRESS",
        ],
    }

    all_ok = True

    for category, vars_list in required_vars.items():
        print(f"\n📋 {category}:")
        category_ok = True

        for var in vars_list:
            value = os.getenv(var)
            if value:
                if "PRIVATE_KEY" in var:
                    print(f"  ✅ {var}: {'*' * 10}...{value[-4:]}")
                else:
                    print(f"  ✅ {var}: {value}")
            else:
                print(f"  ❌ {var}: Missing")
                category_ok = False
                all_ok = False

        if category_ok:
            print(f"  🎉 {category}: ALL CONFIGURED")

    print("\n" + "=" * 50)
    if all_ok:
        print("🎉 ALL REQUIRED VARIABLES PRESENT!")
        print("✅ Scripts should work correctly now")
    else:
        print("⚠️ Some variables still missing")

    return all_ok


if __name__ == "__main__":
    success = fix_missing_endpoints()
    if success:
        verify_all_variables()
    else:
        print("❌ Failed to update .env file")

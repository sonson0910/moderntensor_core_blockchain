#!/usr/bin/env python3
"""
Update .env file to add missing ID variables that scripts expect
"""


def update_env_file():
    print("🔧 UPDATING .ENV FILE WITH MISSING ID VARIABLES")
    print("=" * 50)

    # Read current .env file
    try:
        with open(".env", "r") as f:
            content = f.read()

        print("✅ Current .env file read successfully")

        # Define the ID variables that scripts expect
        additional_ids = """
# Individual Validator IDs (for scripts)
VALIDATOR_1_ID=subnet1_validator_001
VALIDATOR_2_ID=subnet1_validator_002
VALIDATOR_3_ID=subnet1_validator_003

# Individual Miner IDs (for scripts)  
MINER_1_ID=subnet1_miner_001
MINER_2_ID=subnet1_miner_002
"""

        # Check if these variables already exist
        if "VALIDATOR_1_ID=" in content:
            print("⚠️ ID variables already exist in .env file")
            return True

        # Find where to insert (after the miner configuration section)
        insertion_point = content.find("# Entity Private Keys")
        if insertion_point == -1:
            # If not found, append at the end
            updated_content = content + additional_ids
        else:
            # Insert before the Entity Private Keys section
            updated_content = (
                content[:insertion_point]
                + additional_ids
                + "\n"
                + content[insertion_point:]
            )

        # Write updated content back
        with open(".env", "w") as f:
            f.write(updated_content)

        print("✅ .env file updated successfully!")
        print("\n📋 Added variables:")
        print("  - VALIDATOR_1_ID, VALIDATOR_2_ID, VALIDATOR_3_ID")
        print("  - MINER_1_ID, MINER_2_ID")

        return True

    except Exception as e:
        print(f"❌ Error updating .env file: {e}")
        return False


def verify_env_variables():
    """Verify all required variables exist"""
    print("\n🔍 VERIFYING ENVIRONMENT VARIABLES")
    print("=" * 40)

    required_vars = [
        "CORE_CONTRACT_ADDRESS",
        "VALIDATOR_1_ID",
        "VALIDATOR_2_ID",
        "VALIDATOR_3_ID",
        "MINER_1_ID",
        "MINER_2_ID",
        "VALIDATOR_1_PRIVATE_KEY",
        "VALIDATOR_2_PRIVATE_KEY",
        "VALIDATOR_3_PRIVATE_KEY",
        "MINER_1_PRIVATE_KEY",
        "MINER_2_PRIVATE_KEY",
    ]

    # Load environment
    from dotenv import load_dotenv
    import os

    load_dotenv()

    all_ok = True
    for var in required_vars:
        value = os.getenv(var)
        if value:
            if "PRIVATE_KEY" in var:
                print(f"  ✅ {var}: {'*' * 10}...{value[-4:]}")
            else:
                print(f"  ✅ {var}: {value}")
        else:
            print(f"  ❌ {var}: Missing")
            all_ok = False

    if all_ok:
        print("\n🎉 ALL REQUIRED VARIABLES PRESENT!")
        print("✅ Scripts should work correctly now")
    else:
        print("\n⚠️ Some variables still missing")

    return all_ok


if __name__ == "__main__":
    success = update_env_file()
    if success:
        verify_env_variables()
    else:
        print("❌ Failed to update .env file")

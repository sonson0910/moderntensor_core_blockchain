#!/usr/bin/env python3
"""
Test compatibility of subnet1_aptos with the modernized system
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv


def test_compatibility():
    print("🧪 TESTING SUBNET1_APTOS COMPATIBILITY")
    print("=" * 50)

    # Load environment variables
    load_dotenv()

    # Test 1: Environment variables
    print("\n📋 1. TESTING ENVIRONMENT VARIABLES:")
    required_env_vars = [
        "CORE_NODE_URL",
        "CORE_CONTRACT_ADDRESS",
        "CORE_TOKEN_ADDRESS",
        "MINER_1_ADDRESS",
        "VALIDATOR_1_ADDRESS",
    ]

    env_ok = True
    for var in required_env_vars:
        value = os.getenv(var)
        if value:
            print(f"  ✅ {var}: {value}")
        else:
            print(f"  ❌ {var}: Missing")
            env_ok = False

    # Test 2: Import paths
    print("\n📋 2. TESTING IMPORT PATHS:")

    # Add paths
    project_root = Path(__file__).parent
    sys.path.insert(0, str(project_root))
    moderntensor_path = project_root.parent / "moderntensor_aptos"
    sys.path.insert(0, str(moderntensor_path))

    print(f"  📁 Project root: {project_root}")
    print(f"  📁 ModernTensor path: {moderntensor_path}")
    print(f"  📁 ModernTensor exists: {moderntensor_path.exists()}")

    # Test 3: Critical imports
    print("\n📋 3. TESTING CRITICAL IMPORTS:")

    import_tests = [
        ("subnet1.validator", "Subnet1Validator"),
        ("subnet1.miner", "Subnet1Miner"),
        ("mt_core.config.settings", "settings"),
        ("mt_core.account", "Account"),
        ("mt_core.metagraph.core_metagraph_adapter", "CoreMetagraphAdapter"),
    ]

    imports_ok = True
    for module_name, class_name in import_tests:
        try:
            module = __import__(module_name, fromlist=[class_name])
            class_obj = getattr(module, class_name)
            print(f"  ✅ {module_name}.{class_name}: {class_obj}")
        except ImportError as e:
            print(f"  ❌ {module_name}.{class_name}: {e}")
            imports_ok = False
        except AttributeError as e:
            print(f"  ⚠️ {module_name}.{class_name}: {e}")

    # Test 4: Check key scripts exist
    print("\n📋 4. TESTING KEY SCRIPTS:")

    key_scripts = [
        "scripts/run_validator_core.py",
        "scripts/run_miner_core.py",
        "scripts/launcher.py",
        "start_network.py",
    ]

    scripts_ok = True
    for script in key_scripts:
        script_path = project_root / script
        if script_path.exists():
            print(f"  ✅ {script}: Available")
        else:
            print(f"  ❌ {script}: Missing")
            scripts_ok = False

    # Test 5: Check entities directory
    print("\n📋 5. TESTING ENTITIES DIRECTORY:")

    entities_dir = project_root / "entities"
    if entities_dir.exists():
        entities = list(entities_dir.glob("*.json"))
        print(f"  ✅ Entities directory: {len(entities)} entities found")
        for entity in entities:
            print(f"    - {entity.name}")
    else:
        print(f"  ❌ Entities directory: Missing")
        scripts_ok = False

    # Summary
    print("\n" + "=" * 50)
    print("🎯 COMPATIBILITY TEST SUMMARY")
    print("=" * 50)

    all_ok = env_ok and imports_ok and scripts_ok

    if all_ok:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Environment variables configured")
        print("✅ Import paths working")
        print("✅ Critical imports successful")
        print("✅ Key scripts available")
        print("✅ Entities directory ready")

        print("\n🚀 READY TO START NETWORK:")
        print("  1. python start_network.py")
        print("  2. python scripts/run_validator_core.py")
        print("  3. python scripts/run_miner_core.py")

    else:
        print("⚠️ SOME ISSUES FOUND:")
        if not env_ok:
            print("  - Environment variables need attention")
        if not imports_ok:
            print("  - Import issues need fixing")
        if not scripts_ok:
            print("  - Missing scripts or entities")

    return all_ok


if __name__ == "__main__":
    test_compatibility()

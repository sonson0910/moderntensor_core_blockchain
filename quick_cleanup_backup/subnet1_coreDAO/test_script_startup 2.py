#!/usr/bin/env python3
"""
Test script startup to see if they work properly now
"""

import subprocess
import sys
import os
import time


def test_script(script_path, script_name, env_vars=None, args=None):
    """Test a single script startup"""
    print(f"\n🔍 Testing: {script_name}")
    print("-" * 40)

    try:
        # Prepare command
        cmd = [sys.executable, script_path]
        if args:
            cmd.extend(args)

        # Prepare environment
        env = os.environ.copy()
        if env_vars:
            env.update(env_vars)
            print(f"🌍 Environment: {env_vars}")

        print(f"📄 Command: {' '.join(cmd)}")

        # Start process
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env
        )

        # Wait for initial output (3 seconds should be enough for initialization)
        try:
            stdout, stderr = process.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            # Kill the process after timeout (it's expected to keep running)
            process.kill()
            stdout, stderr = process.communicate()

        # Analyze output
        output_lines = stdout.splitlines() if stdout else []
        error_lines = stderr.splitlines() if stderr else []

        print(f"\n📄 Output ({len(output_lines)} lines):")
        for i, line in enumerate(output_lines[-10:]):  # Show last 10 lines
            print(f"  {i+1:2d}→ {line}")

        if error_lines:
            print(f"\n❌ Errors ({len(error_lines)} lines):")
            for i, line in enumerate(error_lines[-5:]):  # Show last 5 error lines
                print(f"  {i+1:2d}→ {line}")

        # Check for success indicators
        success_indicators = [
            "Loading environment variables",
            "Using Validator",
            "Using Miner",
            "Validator Readable ID",
            "Miner Readable ID",
            "Configuration",
            "Core blockchain account loaded",
        ]

        fatal_errors = [
            "FATAL:",
            "ImportError:",
            "ModuleNotFoundError:",
            "not set",
            "is not set",
        ]

        has_success = any(
            indicator in line
            for line in output_lines
            for indicator in success_indicators
        )
        has_fatal = any(
            error in line
            for line in output_lines + error_lines
            for error in fatal_errors
        )

        if has_success and not has_fatal:
            print(f"✅ {script_name}: INITIALIZATION SUCCESS")
            return True
        elif has_fatal:
            print(f"❌ {script_name}: FATAL ERROR DETECTED")
            return False
        else:
            print(f"⚠️ {script_name}: UNCLEAR RESULT")
            return None

    except Exception as e:
        print(f"❌ {script_name}: EXCEPTION - {e}")
        return False


def main():
    print("🧪 TESTING SCRIPT STARTUP AFTER FIX")
    print("=" * 50)

    # Test cases
    tests = [
        {
            "script": "scripts/run_miner_core.py",
            "name": "Miner Core (Miner 1)",
            "env": {},
        },
        {
            "script": "scripts/run_miner_core.py",
            "name": "Miner Core (Miner 2)",
            "env": {"MINER_ID": "2"},
        },
        {
            "script": "scripts/run_validator_core.py",
            "name": "Validator Core (Validator 1)",
            "env": {},
        },
        {
            "script": "scripts/run_validator_core.py",
            "name": "Validator Core (Validator 2)",
            "env": {"VALIDATOR_ID": "2"},
        },
        {
            "script": "scripts/run_validator_core_v2.py",
            "name": "Validator Core V2 (Validator 1)",
            "args": ["--validator", "1"],
        },
        {
            "script": "scripts/run_validator_core_v2.py",
            "name": "Validator Core V2 (Validator 2)",
            "args": ["--validator", "2"],
        },
    ]

    results = []

    for test in tests:
        result = test_script(
            test["script"], test["name"], test.get("env"), test.get("args")
        )
        results.append((test["name"], result))

    # Summary
    print("\n" + "=" * 50)
    print("🎯 SCRIPT STARTUP TEST SUMMARY")
    print("=" * 50)

    success_count = sum(1 for _, result in results if result is True)
    total_count = len(results)

    for name, result in results:
        if result is True:
            print(f"  ✅ {name}: PASS")
        elif result is False:
            print(f"  ❌ {name}: FAIL")
        else:
            print(f"  ⚠️ {name}: UNCLEAR")

    print(f"\n📊 Results: {success_count}/{total_count} scripts working")

    if success_count == total_count:
        print("🎉 ALL SCRIPTS ARE WORKING!")
        print("✅ Environment configuration is complete")
        print("✅ Ready to start the network")
    elif success_count > 0:
        print("⚠️ Some scripts still have issues")
    else:
        print("❌ Scripts still not working properly")

    return success_count == total_count


if __name__ == "__main__":
    main()

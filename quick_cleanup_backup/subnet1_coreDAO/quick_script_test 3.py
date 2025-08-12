#!/usr/bin/env python3
"""
Quick test to verify the scripts can initialize properly
"""

import subprocess
import sys
import os
import signal
import time
from pathlib import Path


def test_script_initialization():
    print("🧪 TESTING SCRIPT INITIALIZATION")
    print("=" * 50)

    # Test scripts with their initialization only (not full startup)
    scripts_to_test = [
        {
            "name": "Validator Core",
            "script": "scripts/run_validator_core.py",
            "timeout": 10,
            "env": {},
        },
        {
            "name": "Miner Core",
            "script": "scripts/run_miner_core.py",
            "timeout": 10,
            "env": {},
        },
        {
            "name": "Validator Core V2 (Validator 1)",
            "script": "scripts/run_validator_core_v2.py",
            "args": ["--validator", "1"],
            "timeout": 10,
            "env": {},
        },
        {
            "name": "Validator Core V2 (Validator 2)",
            "script": "scripts/run_validator_core_v2.py",
            "args": ["--validator", "2"],
            "timeout": 10,
            "env": {},
        },
        {
            "name": "Miner Core (Miner 2)",
            "script": "scripts/run_miner_core.py",
            "timeout": 10,
            "env": {"MINER_ID": "2"},
        },
    ]

    results = []

    for test_config in scripts_to_test:
        print(f"\n🔍 Testing: {test_config['name']}")
        print("-" * 40)

        try:
            # Prepare command
            cmd = [sys.executable, test_config["script"]]
            if "args" in test_config:
                cmd.extend(test_config["args"])

            # Prepare environment
            env = os.environ.copy()
            env.update(test_config["env"])

            print(f"📄 Command: {' '.join(cmd)}")
            if test_config["env"]:
                print(f"🌍 Environment: {test_config['env']}")

            # Start process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                preexec_fn=os.setsid,  # Create new process group
            )

            # Wait for initial output or timeout
            start_time = time.time()
            output_lines = []
            error_lines = []

            while time.time() - start_time < test_config["timeout"]:
                # Check if process has output
                try:
                    process.wait(timeout=0.1)
                    # Process finished
                    stdout, stderr = process.communicate()
                    output_lines.extend(stdout.splitlines())
                    error_lines.extend(stderr.splitlines())
                    break
                except subprocess.TimeoutExpired:
                    # Process still running, that's expected for these scripts
                    pass

            # Kill the process (it's expected to keep running)
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                process.wait(timeout=2)
            except:
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                except:
                    pass

            # Read any remaining output
            try:
                stdout, stderr = process.communicate(timeout=1)
                if stdout:
                    output_lines.extend(stdout.splitlines())
                if stderr:
                    error_lines.extend(stderr.splitlines())
            except:
                pass

            # Analyze results
            success_indicators = [
                "Loading environment variables",
                "Using Validator",
                "Using Miner",
                "Starting Enhanced Core",
                "Starting Core Blockchain",
                "Configuration",
            ]

            fatal_errors = [
                "FATAL:",
                "ImportError:",
                "ModuleNotFoundError:",
                "missing",
                "not set",
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
                print(f"✅ {test_config['name']}: INITIALIZATION SUCCESS")
                results.append((test_config["name"], True, "Successful initialization"))
            elif has_fatal:
                print(f"❌ {test_config['name']}: FATAL ERROR DETECTED")
                # Show first few lines of output for debugging
                for line in (output_lines + error_lines)[:5]:
                    if any(error in line for error in fatal_errors):
                        print(f"   💥 {line}")
                results.append((test_config["name"], False, "Fatal error"))
            else:
                print(f"⚠️ {test_config['name']}: UNCLEAR RESULT")
                results.append((test_config["name"], None, "Unclear result"))

        except Exception as e:
            print(f"❌ {test_config['name']}: EXCEPTION - {e}")
            results.append((test_config["name"], False, f"Exception: {e}"))

    # Summary
    print("\n" + "=" * 50)
    print("🎯 SCRIPT INITIALIZATION SUMMARY")
    print("=" * 50)

    success_count = sum(1 for _, success, _ in results if success is True)
    total_count = len(results)

    for name, success, details in results:
        status = (
            "✅ PASS"
            if success is True
            else "❌ FAIL" if success is False else "⚠️ UNCLEAR"
        )
        print(f"  {status} {name}: {details}")

    print(
        f"\n📊 Results: {success_count}/{total_count} scripts initialized successfully"
    )

    if success_count == total_count:
        print("🎉 ALL SCRIPTS CAN INITIALIZE PROPERLY!")
        print("✅ Scripts are compatible with the environment")
        print("✅ Ready for network operation")
    elif success_count > 0:
        print("⚠️ Some scripts have issues - check the errors above")
    else:
        print("❌ No scripts can initialize - environment issues need fixing")

    return success_count == total_count


if __name__ == "__main__":
    test_script_initialization()

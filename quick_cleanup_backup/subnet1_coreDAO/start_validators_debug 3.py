#!/usr/bin/env python3
"""
Start validators and monitor their behavior to debug consensus issues
"""

import os
import sys
import time
import subprocess
import threading
from pathlib import Path
from dotenv import load_dotenv


def start_validator(validator_id, port):
    """Start a single validator in background"""
    print(f"🚀 Starting Validator {validator_id} on port {port}...")

    # Set environment variables
    env = os.environ.copy()
    env["VALIDATOR_ID"] = str(validator_id)
    env["LOG_LEVEL"] = "DEBUG"  # Enable debug logging

    # Start validator process
    try:
        if validator_id == 3:
            # Use V2 script for validator 3
            cmd = [
                sys.executable,
                "scripts/run_validator_core_v2.py",
                "--validator",
                "3",
            ]
        else:
            cmd = [sys.executable, "scripts/run_validator_core.py"]
            env["VALIDATOR_ID"] = str(validator_id)

        process = subprocess.Popen(
            cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        print(f"✅ Validator {validator_id} started (PID: {process.pid})")
        return process

    except Exception as e:
        print(f"❌ Failed to start Validator {validator_id}: {e}")
        return None


def monitor_validator(validator_id, process, log_file):
    """Monitor validator output and save to log file"""
    print(f"📊 Monitoring Validator {validator_id}...")

    with open(log_file, "w") as f:
        f.write(f"=== Validator {validator_id} Log ===\n")

        while process.poll() is None:
            # Read output
            output = process.stdout.readline()
            if output:
                f.write(output)
                f.flush()

                # Check for key events
                if "Application startup complete" in output:
                    print(f"✅ Validator {validator_id}: API server started")
                elif "Sequential round" in output:
                    print(f"🔄 Validator {validator_id}: Consensus round detected")
                elif "Transaction successful" in output:
                    print(f"💰 Validator {validator_id}: Transaction submitted")
                elif "ERROR" in output or "FATAL" in output:
                    print(f"❌ Validator {validator_id}: Error detected")

        # Read remaining output
        remaining_output, remaining_error = process.communicate()
        if remaining_output:
            f.write(remaining_output)
        if remaining_error:
            f.write(f"ERRORS:\n{remaining_error}")

    print(f"📄 Validator {validator_id} log saved to: {log_file}")


def main():
    print("🚀 STARTING VALIDATORS FOR DEBUG")
    print("=" * 50)

    # Load environment
    load_dotenv()

    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Start validators
    validators = [
        {"id": 1, "port": 8001},
        {"id": 2, "port": 8002},
        {"id": 3, "port": 8003},
    ]

    processes = []
    monitor_threads = []

    print("📋 Starting validators...")

    for validator in validators:
        process = start_validator(validator["id"], validator["port"])
        if process:
            processes.append((validator["id"], process))

            # Start monitoring thread
            log_file = logs_dir / f"validator_{validator['id']}.log"
            monitor_thread = threading.Thread(
                target=monitor_validator, args=(validator["id"], process, log_file)
            )
            monitor_thread.daemon = True
            monitor_thread.start()
            monitor_threads.append(monitor_thread)

        time.sleep(2)  # Stagger startup

    print(f"\n✅ Started {len(processes)} validators")

    # Monitor for a period
    print("\n📊 MONITORING VALIDATORS (30 seconds)...")
    print("Press Ctrl+C to stop")

    try:
        start_time = time.time()
        while time.time() - start_time < 30:
            # Check if all processes are still running
            running_count = sum(1 for _, p in processes if p.poll() is None)
            print(
                f"\r⏱️  {running_count}/{len(processes)} validators running...",
                end="",
                flush=True,
            )
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\n🛑 Stopping validators...")

    # Stop all validators
    print("\n🛑 Stopping validators...")
    for validator_id, process in processes:
        try:
            process.terminate()
            process.wait(timeout=5)
            print(f"✅ Validator {validator_id} stopped")
        except:
            try:
                process.kill()
                print(f"💀 Validator {validator_id} force killed")
            except:
                print(f"❌ Could not stop Validator {validator_id}")

    # Summary
    print("\n📋 SUMMARY:")
    for validator_id, process in processes:
        log_file = logs_dir / f"validator_{validator_id}.log"
        if log_file.exists():
            with open(log_file, "r") as f:
                content = f.read()
                consensus_rounds = content.count("Sequential round")
                transactions = content.count("Transaction successful")
                errors = content.count("ERROR") + content.count("FATAL")

                print(f"  Validator {validator_id}:")
                print(f"    📄 Log: {log_file}")
                print(f"    🔄 Consensus rounds: {consensus_rounds}")
                print(f"    💰 Transactions: {transactions}")
                print(f"    ❌ Errors: {errors}")

    print("\n🔍 NEXT STEPS:")
    print("1. Check individual validator logs in logs/ directory")
    print("2. Look for consensus timing issues")
    print("3. Check for transaction submission problems")
    print("4. Verify metagraph update intervals")


if __name__ == "__main__":
    main()

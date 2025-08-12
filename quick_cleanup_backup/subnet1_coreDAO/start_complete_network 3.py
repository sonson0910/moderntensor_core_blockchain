#!/usr/bin/env python3
"""
Start complete network with 2 validators and 2 miners to fix consensus issues
"""

import os
import sys
import time
import subprocess
import threading
import requests
from pathlib import Path
from dotenv import load_dotenv


def start_validator(validator_id, port):
    """Start a single validator in background"""
    print(f"🚀 Starting Validator {validator_id} on port {port}...")

    # Set environment variables
    env = os.environ.copy()
    env["VALIDATOR_ID"] = str(validator_id)
    env["LOG_LEVEL"] = "INFO"  # Use INFO level for cleaner logs

    # Start validator process
    try:
        cmd = [sys.executable, "scripts/run_validator_core.py"]

        process = subprocess.Popen(
            cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        print(f"✅ Validator {validator_id} started (PID: {process.pid})")
        return process

    except Exception as e:
        print(f"❌ Failed to start Validator {validator_id}: {e}")
        return None


def start_miner(miner_id, port):
    """Start a single miner in background"""
    print(f"🚀 Starting Miner {miner_id} on port {port}...")

    # Set environment variables
    env = os.environ.copy()
    env["MINER_ID"] = str(miner_id)
    env["LOG_LEVEL"] = "INFO"  # Use INFO level for cleaner logs

    # Start miner process
    try:
        cmd = [sys.executable, "scripts/run_miner_core.py"]

        process = subprocess.Popen(
            cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        print(f"✅ Miner {miner_id} started (PID: {process.pid})")
        return process

    except Exception as e:
        print(f"❌ Failed to start Miner {miner_id}: {e}")
        return None


def monitor_process(process_type, process_id, process, log_file):
    """Monitor process output and save to log file"""
    print(f"📊 Monitoring {process_type} {process_id}...")

    with open(log_file, "w") as f:
        f.write(f"=== {process_type} {process_id} Log ===\n")

        while process.poll() is None:
            # Read output
            output = process.stdout.readline()
            if output:
                f.write(output)
                f.flush()

                # Check for key events
                if "Application startup complete" in output:
                    print(f"✅ {process_type} {process_id}: API server started")
                elif "Sequential round" in output:
                    print(f"🔄 {process_type} {process_id}: Consensus round")
                elif "Transaction successful" in output:
                    print(f"💰 {process_type} {process_id}: Transaction submitted")
                elif "Task received" in output:
                    print(f"📋 {process_type} {process_id}: Task received")
                elif "Result submitted" in output:
                    print(f"📤 {process_type} {process_id}: Result submitted")
                elif "ERROR" in output or "FATAL" in output:
                    print(f"❌ {process_type} {process_id}: Error detected")

        # Read remaining output
        remaining_output, remaining_error = process.communicate()
        if remaining_output:
            f.write(remaining_output)
        if remaining_error:
            f.write(f"ERRORS:\n{remaining_error}")

    print(f"📄 {process_type} {process_id} log saved to: {log_file}")


def check_network_health():
    """Check if network components are healthy"""
    print("\n🔍 CHECKING NETWORK HEALTH:")

    # Check validators
    validators = [
        {"id": 1, "endpoint": "http://localhost:8001"},
        {"id": 2, "endpoint": "http://localhost:8002"},
    ]

    healthy_validators = []
    for validator in validators:
        try:
            response = requests.get(f"{validator['endpoint']}/health", timeout=5)
            if response.status_code == 200:
                print(f"✅ Validator {validator['id']}: Healthy")
                healthy_validators.append(validator)
            else:
                print(f"❌ Validator {validator['id']}: Not responding")
        except:
            print(f"❌ Validator {validator['id']}: Connection failed")

    # Check miners
    miners = [
        {"id": 1, "endpoint": "http://localhost:8101"},
        {"id": 2, "endpoint": "http://localhost:8102"},
    ]

    healthy_miners = []
    for miner in miners:
        try:
            response = requests.get(f"{miner['endpoint']}/health", timeout=5)
            if response.status_code == 200:
                print(f"✅ Miner {miner['id']}: Healthy")
                healthy_miners.append(miner)
            else:
                print(f"❌ Miner {miner['id']}: Not responding")
        except:
            print(f"❌ Miner {miner['id']}: Connection failed")

    return len(healthy_validators) >= 2 and len(healthy_miners) >= 2


def main():
    print("🚀 STARTING COMPLETE NETWORK")
    print("=" * 50)

    # Load environment
    load_dotenv()

    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Start validators first
    print("\n📋 Starting Validators...")
    validators = [
        {"id": 1, "port": 8001},
        {"id": 2, "port": 8002},
    ]

    validator_processes = []
    validator_threads = []

    for validator in validators:
        process = start_validator(validator["id"], validator["port"])
        if process:
            validator_processes.append((validator["id"], process))

            # Start monitoring thread
            log_file = logs_dir / f"validator_{validator['id']}.log"
            monitor_thread = threading.Thread(
                target=monitor_process,
                args=("Validator", validator["id"], process, log_file),
            )
            monitor_thread.daemon = True
            monitor_thread.start()
            validator_threads.append(monitor_thread)

        time.sleep(3)  # Wait for validator to start

    print(f"✅ Started {len(validator_processes)} validators")

    # Wait for validators to be ready
    print("\n⏳ Waiting for validators to be ready...")
    time.sleep(10)

    # Start miners
    print("\n📋 Starting Miners...")
    miners = [
        {"id": 1, "port": 8101},
        {"id": 2, "port": 8102},
    ]

    miner_processes = []
    miner_threads = []

    for miner in miners:
        process = start_miner(miner["id"], miner["port"])
        if process:
            miner_processes.append((miner["id"], process))

            # Start monitoring thread
            log_file = logs_dir / f"miner_{miner['id']}.log"
            monitor_thread = threading.Thread(
                target=monitor_process, args=("Miner", miner["id"], process, log_file)
            )
            monitor_thread.daemon = True
            monitor_thread.start()
            miner_threads.append(monitor_thread)

        time.sleep(3)  # Wait for miner to start

    print(f"✅ Started {len(miner_processes)} miners")

    # Monitor network
    print(f"\n📊 MONITORING COMPLETE NETWORK (120 seconds)...")
    print("Press Ctrl+C to stop")

    try:
        start_time = time.time()
        while time.time() - start_time < 120:
            # Check if all processes are still running
            validator_running = sum(
                1 for _, p in validator_processes if p.poll() is None
            )
            miner_running = sum(1 for _, p in miner_processes if p.poll() is None)

            print(
                f"\r⏱️  {validator_running}/2 validators, {miner_running}/2 miners running...",
                end="",
                flush=True,
            )
            time.sleep(2)

            # Check network health every 30 seconds
            if int(time.time() - start_time) % 30 == 0:
                print(
                    f"\n🔍 Network health check at {int(time.time() - start_time)}s..."
                )
                if check_network_health():
                    print("✅ Network healthy!")
                else:
                    print("⚠️ Network issues detected")

    except KeyboardInterrupt:
        print("\n\n🛑 Stopping network...")

    # Stop all processes
    print("\n🛑 Stopping all processes...")

    # Stop miners first
    for miner_id, process in miner_processes:
        try:
            process.terminate()
            process.wait(timeout=5)
            print(f"✅ Miner {miner_id} stopped")
        except:
            try:
                process.kill()
                print(f"💀 Miner {miner_id} force killed")
            except:
                print(f"❌ Could not stop Miner {miner_id}")

    # Stop validators
    for validator_id, process in validator_processes:
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

    # Final summary
    print("\n📋 FINAL SUMMARY:")
    print("=" * 30)

    # Check logs for activity
    for validator_id, _ in validator_processes:
        log_file = logs_dir / f"validator_{validator_id}.log"
        if log_file.exists():
            with open(log_file, "r") as f:
                content = f.read()
                consensus_rounds = content.count("Sequential round")
                transactions = content.count("Transaction successful")
                errors = content.count("ERROR") + content.count("FATAL")

                print(f"  Validator {validator_id}:")
                print(f"    🔄 Consensus rounds: {consensus_rounds}")
                print(f"    💰 Transactions: {transactions}")
                print(f"    ❌ Errors: {errors}")

    for miner_id, _ in miner_processes:
        log_file = logs_dir / f"miner_{miner_id}.log"
        if log_file.exists():
            with open(log_file, "r") as f:
                content = f.read()
                tasks_received = content.count("Task received")
                results_submitted = content.count("Result submitted")
                errors = content.count("ERROR") + content.count("FATAL")

                print(f"  Miner {miner_id}:")
                print(f"    📋 Tasks received: {tasks_received}")
                print(f"    📤 Results submitted: {results_submitted}")
                print(f"    ❌ Errors: {errors}")

    print("\n🔍 NEXT STEPS:")
    print("1. Check logs in logs/ directory for detailed activity")
    print("2. Look for consensus rounds and transactions")
    print("3. Verify miners are receiving tasks")
    print("4. Monitor blockchain for new transactions")


if __name__ == "__main__":
    main()

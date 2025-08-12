#!/usr/bin/env python3
"""
Start miners and monitor their behavior to complete the network
"""

import os
import sys
import time
import subprocess
import threading
import requests
from pathlib import Path
from dotenv import load_dotenv


def start_miner(miner_id, port):
    """Start a single miner in background"""
    print(f"🚀 Starting Miner {miner_id} on port {port}...")

    # Set environment variables
    env = os.environ.copy()
    env["MINER_ID"] = str(miner_id)
    env["LOG_LEVEL"] = "DEBUG"  # Enable debug logging

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


def monitor_miner(miner_id, process, log_file):
    """Monitor miner output and save to log file"""
    print(f"📊 Monitoring Miner {miner_id}...")

    with open(log_file, "w") as f:
        f.write(f"=== Miner {miner_id} Log ===\n")

        while process.poll() is None:
            # Read output
            output = process.stdout.readline()
            if output:
                f.write(output)
                f.flush()

                # Check for key events
                if "Application startup complete" in output:
                    print(f"✅ Miner {miner_id}: API server started")
                elif "Task received" in output:
                    print(f"📋 Miner {miner_id}: Task received")
                elif "Result submitted" in output:
                    print(f"📤 Miner {miner_id}: Result submitted")
                elif "ERROR" in output or "FATAL" in output:
                    print(f"❌ Miner {miner_id}: Error detected")

        # Read remaining output
        remaining_output, remaining_error = process.communicate()
        if remaining_output:
            f.write(remaining_output)
        if remaining_error:
            f.write(f"ERRORS:\n{remaining_error}")

    print(f"📄 Miner {miner_id} log saved to: {log_file}")


def check_validator_health():
    """Check if validators are healthy"""
    print("\n🔍 CHECKING VALIDATOR HEALTH:")

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

    return len(healthy_validators) >= 2


def main():
    print("🚀 STARTING MINERS FOR DEBUG")
    print("=" * 50)

    # Load environment
    load_dotenv()

    # Check if validators are running first
    if not check_validator_health():
        print("❌ Validators not healthy - please start validators first")
        print("Run: python start_validators_debug.py")
        return

    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Start miners
    miners = [{"id": 1, "port": 8101}, {"id": 2, "port": 8102}]

    processes = []
    monitor_threads = []

    print("\n📋 Starting miners...")

    for miner in miners:
        process = start_miner(miner["id"], miner["port"])
        if process:
            processes.append((miner["id"], process))

            # Start monitoring thread
            log_file = logs_dir / f"miner_{miner['id']}.log"
            monitor_thread = threading.Thread(
                target=monitor_miner, args=(miner["id"], process, log_file)
            )
            monitor_thread.daemon = True
            monitor_thread.start()
            monitor_threads.append(monitor_thread)

        time.sleep(2)  # Stagger startup

    print(f"\n✅ Started {len(processes)} miners")

    # Monitor for a period
    print("\n📊 MONITORING MINERS (60 seconds)...")
    print("Press Ctrl+C to stop")

    try:
        start_time = time.time()
        while time.time() - start_time < 60:
            # Check if all processes are still running
            running_count = sum(1 for _, p in processes if p.poll() is None)
            print(
                f"\r⏱️  {running_count}/{len(processes)} miners running...",
                end="",
                flush=True,
            )
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\n🛑 Stopping miners...")

    # Stop all miners
    print("\n🛑 Stopping miners...")
    for miner_id, process in processes:
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

    # Summary
    print("\n📋 SUMMARY:")
    for miner_id, process in processes:
        log_file = logs_dir / f"miner_{miner_id}.log"
        if log_file.exists():
            with open(log_file, "r") as f:
                content = f.read()
                tasks_received = content.count("Task received")
                results_submitted = content.count("Result submitted")
                errors = content.count("ERROR") + content.count("FATAL")

                print(f"  Miner {miner_id}:")
                print(f"    📄 Log: {log_file}")
                print(f"    📋 Tasks received: {tasks_received}")
                print(f"    📤 Results submitted: {results_submitted}")
                print(f"    ❌ Errors: {errors}")

    print("\n🔍 NEXT STEPS:")
    print("1. Check miner logs for task processing")
    print("2. Verify miners can connect to validators")
    print("3. Check if tasks are being assigned")
    print("4. Monitor consensus with miners active")


if __name__ == "__main__":
    main()

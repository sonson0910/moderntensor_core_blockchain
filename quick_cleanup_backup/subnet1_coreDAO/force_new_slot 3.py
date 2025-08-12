#!/usr/bin/env python3
"""
Force network into new slot by clearing all coordination and state
"""

import os
import sys
import time
import json
import shutil
from pathlib import Path
from dotenv import load_dotenv


def force_new_slot():
    """Force network into new slot"""
    print("🔧 FORCING NETWORK INTO NEW SLOT")
    print("=" * 50)

    # Load environment
    load_dotenv()

    # 1. Clear slot coordination directory
    coordination_dir = Path("slot_coordination")
    if coordination_dir.exists():
        # Backup
        backup_dir = Path("slot_coordination_backup_force")
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
        shutil.copytree(coordination_dir, backup_dir)
        print(f"✅ Backed up to: {backup_dir}")

        # Remove all files
        for file in coordination_dir.glob("*"):
            if file.is_file():
                file.unlink()
                print(f"🗑️  Removed: {file.name}")

        print("✅ Cleared slot coordination directory")
    else:
        print("⚠️ No slot coordination directory found")

    # 2. Reset validator state
    state_file = Path("validator_state.json")
    if state_file.exists():
        # Backup
        backup_file = Path("validator_state_backup_force.json")
        shutil.copy2(state_file, backup_file)
        print(f"✅ Backed up to: {backup_file}")

        # Reset to force new cycle
        new_state = {
            "last_completed_cycle": -1,
            "next_cycle": 0,
            "last_slot": None,
            "force_reset": True,
            "reset_timestamp": time.time(),
        }

        with open(state_file, "w") as f:
            json.dump(new_state, f, indent=2)

        print("✅ Reset validator state")
    else:
        print("⚠️ No validator state file found")

    # 3. Clear any other state files
    state_files = ["validator_state_backup.json", "validator_state_backup_force.json"]

    for state_file in state_files:
        if Path(state_file).exists():
            Path(state_file).unlink()
            print(f"🗑️  Removed backup: {state_file}")

    # 4. Clear logs directory
    logs_dir = Path("logs")
    if logs_dir.exists():
        for log_file in logs_dir.glob("*.log"):
            log_file.unlink()
            print(f"🗑️  Removed log: {log_file.name}")
        print("✅ Cleared logs directory")

    print("\n✅ FORCE RESET COMPLETE")
    print("=" * 30)
    print("Next steps:")
    print("1. Restart network with clean state")
    print("2. Network should start with new slot")
    print("3. Monitor slot progression")

    print("\n🚀 To restart network:")
    print("   python start_complete_network.py")


if __name__ == "__main__":
    force_new_slot()

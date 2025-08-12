#!/usr/bin/env python3
"""
Fix slot progression issue - network stuck in slot 17.0
"""

import os
import sys
import time
import json
import shutil
from pathlib import Path
from dotenv import load_dotenv


def check_slot_coordination():
    """Check current slot coordination state"""
    print("🔍 CHECKING SLOT COORDINATION STATE")
    print("=" * 50)

    # Load environment
    load_dotenv()

    # Check slot coordination directory
    coordination_dir = Path("slot_coordination")
    if not coordination_dir.exists():
        print("❌ Slot coordination directory not found")
        return False

    print(f"📁 Coordination directory: {coordination_dir}")

    # List all slot files
    slot_files = list(coordination_dir.glob("slot_*.json"))
    print(f"📋 Found {len(slot_files)} slot coordination files")

    # Analyze slot progression
    slots = {}
    for file in slot_files:
        try:
            with open(file, "r") as f:
                data = json.load(f)
                slot_name = data.get("slot", "unknown")
                phase = data.get("phase", "unknown")
                timestamp = data.get("timestamp", 0)

                if slot_name not in slots:
                    slots[slot_name] = []
                slots[slot_name].append(
                    {"file": file.name, "phase": phase, "timestamp": timestamp}
                )
        except Exception as e:
            print(f"❌ Error reading {file}: {e}")

    # Show slot analysis
    print("\n📊 SLOT ANALYSIS:")
    for slot_name in sorted(slots.keys()):
        phases = slots[slot_name]
        print(f"\n  🎯 {slot_name}:")
        for phase_info in phases:
            print(f"    📄 {phase_info['file']}")
            print(f"       Phase: {phase_info['phase']}")
            print(f"       Time: {time.ctime(phase_info['timestamp'])}")

    # Check for stuck slot
    if len(slots) == 1 and "17.0" in slots:
        print("\n❌ ISSUE DETECTED: Network stuck in slot 17.0!")
        print("   - Only one slot found")
        print("   - No progression to new slots")
        return True

    return False


def reset_slot_coordination():
    """Reset slot coordination to force new slot"""
    print("\n🔄 RESETTING SLOT COORDINATION")
    print("=" * 50)

    coordination_dir = Path("slot_coordination")
    if not coordination_dir.exists():
        print("❌ Coordination directory not found")
        return False

    # Backup current state
    backup_dir = Path("slot_coordination_backup")
    if backup_dir.exists():
        shutil.rmtree(backup_dir)

    shutil.copytree(coordination_dir, backup_dir)
    print(f"✅ Backed up to: {backup_dir}")

    # Remove all slot files
    slot_files = list(coordination_dir.glob("slot_*.json"))
    for file in slot_files:
        try:
            file.unlink()
            print(f"🗑️  Removed: {file.name}")
        except Exception as e:
            print(f"❌ Error removing {file}: {e}")

    print(f"✅ Removed {len(slot_files)} slot coordination files")
    return True


def check_validator_state():
    """Check validator state files"""
    print("\n🔍 CHECKING VALIDATOR STATE")
    print("=" * 50)

    state_file = Path("validator_state.json")
    if state_file.exists():
        try:
            with open(state_file, "r") as f:
                state = json.load(f)
                print(f"📄 Current state:")
                print(
                    f"   Last completed cycle: {state.get('last_completed_cycle', 'unknown')}"
                )
                print(f"   Next cycle: {state.get('next_cycle', 'unknown')}")
                print(f"   Last slot: {state.get('last_slot', 'unknown')}")

                # Check if stuck
                if state.get("last_completed_cycle", -1) == -1:
                    print("❌ Validator state shows no completed cycles")
                    return True

        except Exception as e:
            print(f"❌ Error reading state file: {e}")
    else:
        print("⚠️ No validator state file found")

    return False


def reset_validator_state():
    """Reset validator state to force new cycle"""
    print("\n🔄 RESETTING VALIDATOR STATE")
    print("=" * 50)

    state_file = Path("validator_state.json")
    if state_file.exists():
        # Backup
        backup_file = Path("validator_state_backup.json")
        shutil.copy2(state_file, backup_file)
        print(f"✅ Backed up to: {backup_file}")

        # Reset state
        new_state = {
            "last_completed_cycle": -1,
            "next_cycle": 0,
            "last_slot": None,
            "reset_timestamp": time.time(),
        }

        with open(state_file, "w") as f:
            json.dump(new_state, f, indent=2)

        print("✅ Reset validator state")
        return True
    else:
        print("⚠️ No validator state file to reset")
        return False


def main():
    print("🔧 FIXING SLOT PROGRESSION ISSUE")
    print("=" * 50)

    # Check current state
    is_stuck = check_slot_coordination()
    state_issue = check_validator_state()

    if not is_stuck and not state_issue:
        print("\n✅ No slot progression issues detected")
        return

    print("\n❌ SLOT PROGRESSION ISSUES FOUND")
    print("=" * 30)

    if is_stuck:
        print("🔧 Fixing stuck slot coordination...")
        reset_slot_coordination()

    if state_issue:
        print("🔧 Fixing validator state...")
        reset_validator_state()

    print("\n✅ SLOT PROGRESSION RESET COMPLETE")
    print("=" * 30)
    print("Next steps:")
    print("1. Restart validators to pick up new state")
    print("2. Network should progress to new slots")
    print("3. Monitor slot progression in logs")

    print("\n🚀 To restart network:")
    print("   python start_complete_network.py")


if __name__ == "__main__":
    main()

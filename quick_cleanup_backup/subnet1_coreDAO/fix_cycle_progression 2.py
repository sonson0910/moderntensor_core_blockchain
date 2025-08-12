#!/usr/bin/env python3
"""
Fix cycle progression issue - network stuck in metagraph loop
"""

import os
import sys
import time
import json
import shutil
from pathlib import Path
from dotenv import load_dotenv


def check_cycle_progression():
    """Check cycle progression state"""
    print("🔍 CHECKING CYCLE PROGRESSION")
    print("=" * 50)

    # Load environment
    load_dotenv()

    # Check validator state
    state_file = Path("validator_state.json")
    if state_file.exists():
        try:
            with open(state_file, "r") as f:
                state = json.load(f)
                print(f"📄 Current validator state:")
                print(
                    f"   Last completed cycle: {state.get('last_completed_cycle', 'unknown')}"
                )
                print(f"   Next cycle: {state.get('next_cycle', 'unknown')}")
                print(f"   Last slot: {state.get('last_slot', 'unknown')}")

                # Check if cycles are progressing
                if state.get("last_completed_cycle", -1) == -1:
                    print("❌ No cycles completed yet")
                    return False
                else:
                    print(
                        f"✅ Last cycle completed: {state.get('last_completed_cycle')}"
                    )
                    return True

        except Exception as e:
            print(f"❌ Error reading state file: {e}")
    else:
        print("⚠️ No validator state file found")

    return False


def check_slot_coordination_cycle():
    """Check if slot coordination shows cycle progression"""
    print("\n🔍 CHECKING SLOT COORDINATION CYCLE")
    print("=" * 50)

    coordination_dir = Path("slot_coordination")
    if not coordination_dir.exists():
        print("❌ Slot coordination directory not found")
        return False

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

    # Check for cycle progression
    if len(slots) == 1 and "17.0" in slots:
        print("\n❌ ISSUE: Only one slot found - no cycle progression!")
        print("   - Network stuck in slot 17.0")
        print("   - No progression to new cycles")
        return False
    elif len(slots) > 1:
        print(f"\n✅ Multiple slots found: {list(slots.keys())}")
        print("   - Cycle progression appears to be working")
        return True

    return False


def check_consensus_config():
    """Check consensus configuration for cycle progression"""
    print("\n🔍 CHECKING CONSENSUS CONFIGURATION")
    print("=" * 50)

    # Check if consensus config exists
    config_path = Path("../moderntensor_aptos/mt_core/config/consensus.yaml")
    if config_path.exists():
        try:
            import yaml

            with open(config_path, "r") as f:
                config = yaml.safe_load(f)

            print("📄 Consensus configuration:")
            print(
                f"   Slot duration: {config.get('slot_duration_minutes', 'unknown')} minutes"
            )
            print(
                f"   Task assignment: {config.get('task_assignment_minutes', 'unknown')} minutes"
            )
            print(f"   Consensus: {config.get('consensus_minutes', 'unknown')} minutes")
            print(
                f"   Metagraph update: {config.get('metagraph_update_seconds', 'unknown')} seconds"
            )
            print(
                f"   Min validators: {config.get('min_validators_for_consensus', 'unknown')}"
            )

            # Check for cycle progression settings
            if "cycle_progression" in config:
                print(f"   Cycle progression: {config['cycle_progression']}")
            else:
                print("   ⚠️ No cycle progression settings found")

        except Exception as e:
            print(f"❌ Error reading config: {e}")
    else:
        print("❌ Consensus config not found")

    return True


def force_cycle_progression():
    """Force cycle progression by resetting state"""
    print("\n🔄 FORCING CYCLE PROGRESSION")
    print("=" * 50)

    # 1. Clear slot coordination
    coordination_dir = Path("slot_coordination")
    if coordination_dir.exists():
        # Backup
        backup_dir = Path("slot_coordination_backup_cycle")
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

    # 2. Reset validator state to force new cycle
    state_file = Path("validator_state.json")
    if state_file.exists():
        # Backup
        backup_file = Path("validator_state_backup_cycle.json")
        shutil.copy2(state_file, backup_file)
        print(f"✅ Backed up to: {backup_file}")

        # Read current state
        with open(state_file, "r") as f:
            current_state = json.load(f)

        # Force cycle progression
        new_state = {
            "last_completed_cycle": current_state.get("last_completed_cycle", -1) + 1,
            "next_cycle": current_state.get("next_cycle", 0) + 1,
            "last_slot": None,
            "force_cycle_progression": True,
            "reset_timestamp": time.time(),
        }

        with open(state_file, "w") as f:
            json.dump(new_state, f, indent=2)

        print(
            f"✅ Forced cycle progression: {new_state['last_completed_cycle']} → {new_state['next_cycle']}"
        )

    # 3. Clear logs
    logs_dir = Path("logs")
    if logs_dir.exists():
        for log_file in logs_dir.glob("*.log"):
            log_file.unlink()
            print(f"🗑️  Removed log: {log_file.name}")
        print("✅ Cleared logs directory")

    print("\n✅ CYCLE PROGRESSION FORCE RESET COMPLETE")
    print("=" * 40)
    print("Next steps:")
    print("1. Restart network with forced cycle progression")
    print("2. Network should start with new cycle")
    print("3. Monitor cycle progression in logs")

    print("\n🚀 To restart network:")
    print("   python start_complete_network.py")


def main():
    print("🔧 FIXING CYCLE PROGRESSION ISSUE")
    print("=" * 50)

    # Check current state
    cycle_ok = check_cycle_progression()
    slot_ok = check_slot_coordination_cycle()
    config_ok = check_consensus_config()

    if cycle_ok and slot_ok:
        print("\n✅ Cycle progression appears to be working")
        return

    print("\n❌ CYCLE PROGRESSION ISSUES FOUND")
    print("=" * 35)

    if not cycle_ok:
        print("🔧 Forcing cycle progression...")
        force_cycle_progression()

    print("\n🔍 DIAGNOSIS:")
    print("   - Network stuck in metagraph update loop")
    print("   - No progression to new cycles")
    print("   - Consensus cycle not completing properly")
    print("   - Need to force cycle progression")


if __name__ == "__main__":
    main()

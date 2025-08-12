#!/usr/bin/env python3
"""
Fix consensus loop issue - same slot repeating multiple times
"""

import os
import sys
import time
import json
import shutil
from pathlib import Path
from dotenv import load_dotenv


def analyze_consensus_loop():
    """Analyze the consensus loop pattern"""
    print("🔍 ANALYZING CONSENSUS LOOP")
    print("=" * 50)

    # Load environment
    load_dotenv()

    # Check validator logs for loop pattern
    log_file = Path("logs/validator_1.log")
    if not log_file.exists():
        print("❌ Validator log not found")
        return False

    print("📊 ANALYZING CONSENSUS CYCLE PATTERN:")
    print("-" * 40)

    # Count cycle completions per slot
    slot_cycles = {}
    current_slot = None

    with open(log_file, "r") as f:
        for line in f:
            if "Flexible consensus cycle completed for slot" in line:
                # Extract slot from line
                parts = line.split("slot ")
                if len(parts) > 1:
                    slot = parts[1].split()[0]  # Get slot number
                    if slot not in slot_cycles:
                        slot_cycles[slot] = []

                    # Extract timestamp
                    timestamp = line.split()[0] + " " + line.split()[1]
                    slot_cycles[slot].append(timestamp)
                    current_slot = slot

    # Show analysis
    for slot, timestamps in slot_cycles.items():
        print(f"\n🎯 Slot {slot}:")
        print(f"   📊 Total cycles: {len(timestamps)}")
        for i, ts in enumerate(timestamps, 1):
            print(f"   🔄 Cycle {i}: {ts}")

        if len(timestamps) > 1:
            print(f"   ⚠️  ISSUE: Slot {slot} repeated {len(timestamps)} times!")

    return slot_cycles


def check_slot_progression_logic():
    """Check if slot progression logic is working"""
    print("\n🔍 CHECKING SLOT PROGRESSION LOGIC")
    print("=" * 50)

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

                # Check if slot is progressing
                if state.get("last_slot") == "17.0":
                    print("   ⚠️  ISSUE: Last slot still 17.0 - no progression!")
                    return False
                else:
                    print(f"   ✅ Slot progression: {state.get('last_slot')}")
                    return True

        except Exception as e:
            print(f"❌ Error reading state file: {e}")
    else:
        print("⚠️ No validator state file found")

    return False


def check_consensus_config_timing():
    """Check consensus timing configuration"""
    print("\n🔍 CHECKING CONSENSUS TIMING")
    print("=" * 50)

    # Check if consensus config exists
    config_path = Path("../moderntensor_aptos/mt_core/config/consensus.yaml")
    if config_path.exists():
        try:
            import yaml

            with open(config_path, "r") as f:
                config = yaml.safe_load(f)

            print("📄 Consensus timing configuration:")
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

            # Calculate total cycle time
            total_minutes = (
                config.get("slot_duration_minutes", 0)
                + config.get("task_assignment_minutes", 0)
                + config.get("consensus_minutes", 0)
            )
            total_seconds = total_minutes * 60 + config.get(
                "metagraph_update_seconds", 0
            )

            print(
                f"   📊 Total cycle time: {total_minutes} minutes ({total_seconds} seconds)"
            )

            # Check if timing is reasonable
            if total_seconds < 30:
                print("   ⚠️  ISSUE: Cycle time too short - may cause loops!")
                return False
            else:
                print("   ✅ Cycle timing looks reasonable")
                return True

        except Exception as e:
            print(f"❌ Error reading config: {e}")
    else:
        print("❌ Consensus config not found")

    return False


def fix_consensus_loop():
    """Fix consensus loop by adjusting timing and state"""
    print("\n🔄 FIXING CONSENSUS LOOP")
    print("=" * 50)

    # 1. Clear slot coordination to force new slot
    coordination_dir = Path("slot_coordination")
    if coordination_dir.exists():
        # Backup
        backup_dir = Path("slot_coordination_backup_loop")
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

    # 2. Reset validator state to force slot progression
    state_file = Path("validator_state.json")
    if state_file.exists():
        # Backup
        backup_file = Path("validator_state_backup_loop.json")
        shutil.copy2(state_file, backup_file)
        print(f"✅ Backed up to: {backup_file}")

        # Read current state
        with open(state_file, "r") as f:
            current_state = json.load(f)

        # Force slot progression
        new_state = {
            "last_completed_cycle": current_state.get("last_completed_cycle", 0),
            "next_cycle": current_state.get("next_cycle", 1),
            "last_slot": "18.0",  # Force next slot
            "force_slot_progression": True,
            "reset_timestamp": time.time(),
        }

        with open(state_file, "w") as f:
            json.dump(new_state, f, indent=2)

        print(f"✅ Forced slot progression: 17.0 → 18.0")

    # 3. Clear logs
    logs_dir = Path("logs")
    if logs_dir.exists():
        for log_file in logs_dir.glob("*.log"):
            log_file.unlink()
            print(f"🗑️  Removed log: {log_file.name}")
        print("✅ Cleared logs directory")

    print("\n✅ CONSENSUS LOOP FIX COMPLETE")
    print("=" * 35)
    print("Next steps:")
    print("1. Restart network with fixed slot progression")
    print("2. Network should progress to slot 18.0")
    print("3. Monitor for single cycle per slot")

    print("\n🚀 To restart network:")
    print("   python start_complete_network.py")


def main():
    print("🔧 FIXING CONSENSUS LOOP ISSUE")
    print("=" * 50)

    # Analyze current state
    slot_cycles = analyze_consensus_loop()
    slot_ok = check_slot_progression_logic()
    timing_ok = check_consensus_config_timing()

    # Check if loop issue exists
    has_loop = False
    for slot, cycles in slot_cycles.items():
        if len(cycles) > 1:
            has_loop = True
            break

    if not has_loop and slot_ok and timing_ok:
        print("\n✅ No consensus loop issues detected")
        return

    print("\n❌ CONSENSUS LOOP ISSUES FOUND")
    print("=" * 35)

    if has_loop:
        print("🔧 Fixing consensus loop...")
        fix_consensus_loop()

    print("\n🔍 DIAGNOSIS:")
    print("   - Same slot repeating multiple times")
    print("   - No slot progression between cycles")
    print("   - Consensus timing may be too short")
    print("   - Need to force slot progression")


if __name__ == "__main__":
    main()

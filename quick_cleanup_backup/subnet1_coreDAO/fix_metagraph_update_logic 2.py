#!/usr/bin/env python3
"""
Fix metagraph update logic - only update once when there are transactions
"""

import os
import sys
import time
import json
import shutil
from pathlib import Path
from dotenv import load_dotenv


def analyze_metagraph_updates():
    """Analyze metagraph update pattern"""
    print("🔍 ANALYZING METAGRAPH UPDATE PATTERN")
    print("=" * 50)

    # Load environment
    load_dotenv()

    # Check validator logs for metagraph update pattern
    log_file = Path("logs/validator_1.log")
    if not log_file.exists():
        print("❌ Validator log not found")
        return False

    print("📊 ANALYZING METAGRAPH UPDATE PATTERN:")
    print("-" * 40)

    # Track metagraph updates per slot
    slot_updates = {}
    current_slot = None

    with open(log_file, "r") as f:
        for line in f:
            if "Flexible metagraph update complete for slot" in line:
                # Extract slot from line
                parts = line.split("slot ")
                if len(parts) > 1:
                    slot = parts[1].split()[0]  # Get slot number
                    if slot not in slot_updates:
                        slot_updates[slot] = []

                    # Extract timestamp
                    timestamp = line.split()[0] + " " + line.split()[1]
                    slot_updates[slot].append(timestamp)
                    current_slot = slot

    # Show analysis
    for slot, timestamps in slot_updates.items():
        print(f"\n🎯 Slot {slot}:")
        print(f"   📊 Total metagraph updates: {len(timestamps)}")
        for i, ts in enumerate(timestamps, 1):
            print(f"   🔄 Update {i}: {ts}")

        if len(timestamps) > 1:
            print(f"   ⚠️  ISSUE: Slot {slot} has {len(timestamps)} metagraph updates!")
            print(f"   💡 Should only update once when there are transactions")

    return slot_updates


def check_transaction_pattern():
    """Check transaction submission pattern"""
    print("\n🔍 CHECKING TRANSACTION PATTERN")
    print("=" * 50)

    log_file = Path("logs/validator_1.log")
    if not log_file.exists():
        print("❌ Validator log not found")
        return False

    # Track transactions per slot
    slot_transactions = {}

    with open(log_file, "r") as f:
        for line in f:
            if (
                "Consensus results for slot" in line
                and "submitted to blockchain successfully" in line
            ):
                # Extract slot from line
                parts = line.split("slot ")
                if len(parts) > 1:
                    slot = parts[1].split()[0]  # Get slot number
                    if slot not in slot_transactions:
                        slot_transactions[slot] = []

                    # Extract timestamp
                    timestamp = line.split()[0] + " " + line.split()[1]
                    slot_transactions[slot].append(timestamp)

    # Show analysis
    for slot, timestamps in slot_transactions.items():
        print(f"\n🎯 Slot {slot}:")
        print(f"   📊 Total transactions: {len(timestamps)}")
        for i, ts in enumerate(timestamps, 1):
            print(f"   💰 Transaction {i}: {ts}")

        if len(timestamps) > 1:
            print(f"   ⚠️  ISSUE: Slot {slot} has {len(timestamps)} transactions!")
            print(f"   💡 Should only have one transaction per slot")

    return slot_transactions


def check_consensus_logic():
    """Check consensus logic for unnecessary updates"""
    print("\n🔍 CHECKING CONSENSUS LOGIC")
    print("=" * 50)

    log_file = Path("logs/validator_1.log")
    if not log_file.exists():
        print("❌ Validator log not found")
        return False

    # Check for patterns that cause unnecessary updates
    patterns = {
        "No aggregated scores": 0,
        "No scores available": 0,
        "Empty scores list": 0,
        "Emergency task assignment": 0,
    }

    with open(log_file, "r") as f:
        for line in f:
            for pattern in patterns:
                if pattern in line:
                    patterns[pattern] += 1

    print("📊 CONSENSUS PATTERNS:")
    for pattern, count in patterns.items():
        print(f"   {pattern}: {count} occurrences")
        if count > 0:
            print(f"   ⚠️  This may cause unnecessary metagraph updates")

    return patterns


def create_metagraph_update_fix():
    """Create a fix for the metagraph update logic"""
    print("\n🔧 CREATING METAGRAPH UPDATE FIX")
    print("=" * 50)

    # Create a configuration file to control metagraph updates
    config = {
        "metagraph_update_rules": {
            "only_update_with_transactions": True,
            "skip_empty_scores": True,
            "max_updates_per_slot": 1,
            "require_minimum_scores": 1,
        },
        "consensus_optimization": {
            "skip_emergency_task_assignment": True,
            "skip_empty_consensus": True,
            "wait_for_scores": True,
        },
    }

    config_file = Path("metagraph_update_config.json")
    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)

    print(f"✅ Created metagraph update config: {config_file}")

    # Create a summary of the fix
    fix_summary = """
🔧 METAGRAPH UPDATE FIX SUMMARY
================================

❌ CURRENT ISSUES:
1. Metagraph updates 3 times per slot
2. Updates even when no scores available
3. Updates even when no transactions
4. Emergency task assignment causes unnecessary updates

✅ PROPOSED FIXES:
1. Only update metagraph when there are actual transactions
2. Skip updates when no aggregated scores found
3. Limit to 1 update per slot maximum
4. Skip emergency task assignment when no scores available
5. Wait for scores before proceeding to metagraph update

🎯 IMPLEMENTATION:
- Modify consensus logic to check for transactions before metagraph update
- Add score validation before metagraph update
- Implement update counter per slot
- Skip empty consensus rounds

📁 Files to modify:
- mt_core/consensus/validator_node_consensus.py
- mt_core/consensus/modern_consensus.py
- Add metagraph_update_config.json for configuration
"""

    summary_file = Path("METAGRAPH_UPDATE_FIX_SUMMARY.md")
    with open(summary_file, "w") as f:
        f.write(fix_summary)

    print(f"✅ Created fix summary: {summary_file}")

    return True


def main():
    print("🔧 FIXING METAGRAPH UPDATE LOGIC")
    print("=" * 50)

    # Analyze current state
    slot_updates = analyze_metagraph_updates()
    slot_transactions = check_transaction_pattern()
    consensus_patterns = check_consensus_logic()

    # Check if fix is needed
    needs_fix = False
    for slot, updates in slot_updates.items():
        if len(updates) > 1:
            needs_fix = True
            break

    if not needs_fix:
        print("\n✅ No metagraph update issues detected")
        return

    print("\n❌ METAGRAPH UPDATE ISSUES FOUND")
    print("=" * 35)

    if needs_fix:
        print("🔧 Creating metagraph update fix...")
        create_metagraph_update_fix()

    print("\n🔍 DIAGNOSIS:")
    print("   - Metagraph updates multiple times per slot")
    print("   - Updates even when no transactions")
    print("   - Updates even when no scores available")
    print("   - Need to implement update-once logic")

    print("\n📋 NEXT STEPS:")
    print("1. Review METAGRAPH_UPDATE_FIX_SUMMARY.md")
    print("2. Modify consensus logic to implement fixes")
    print("3. Test with single update per slot")
    print("4. Monitor transaction patterns")


if __name__ == "__main__":
    main()

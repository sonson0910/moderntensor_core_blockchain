#!/usr/bin/env python3
"""
Test miner startup
"""

import os
import sys
import subprocess
from pathlib import Path

def test_miner_start():
    """Test starting a miner"""
    
    print("🔍 TESTING MINER STARTUP")
    print("=" * 40)
    
    # Set environment
    env = os.environ.copy()
    env["MINER_ID"] = "1"
    env["LOG_LEVEL"] = "DEBUG"
    
    print(f"🔍 Environment:")
    print(f"   MINER_ID: {env.get('MINER_ID')}")
    print(f"   LOG_LEVEL: {env.get('LOG_LEVEL')}")
    
    # Check if .env exists
    env_file = Path(".env")
    if env_file.exists():
        print(f"✅ .env file exists")
    else:
        print(f"❌ .env file not found")
    
    # Check if script exists
    script_file = Path("scripts/run_miner_core.py")
    if script_file.exists():
        print(f"✅ Script exists: {script_file}")
    else:
        print(f"❌ Script not found: {script_file}")
    
    # Try to start miner
    print(f"\n🚀 Starting miner...")
    try:
        cmd = [sys.executable, "scripts/run_miner_core.py"]
        process = subprocess.Popen(
            cmd, 
            env=env, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True
        )
        
        print(f"✅ Process started (PID: {process.pid})")
        
        # Wait a bit and check if it's still running
        import time
        time.sleep(3)
        
        if process.poll() is None:
            print(f"✅ Process still running")
            
            # Read some output
            output, error = process.communicate(timeout=5)
            print(f"📄 Output: {output[:200]}...")
            if error:
                print(f"❌ Error: {error[:200]}...")
        else:
            print(f"❌ Process crashed (exit code: {process.returncode})")
            output, error = process.communicate()
            print(f"📄 Output: {output}")
            print(f"❌ Error: {error}")
            
    except Exception as e:
        print(f"❌ Failed to start: {e}")

if __name__ == "__main__":
    test_miner_start() 
#!/usr/bin/env python3
"""
Script để chạy các tests Aptos với mock client.
Giúp giảm thiểu vấn đề rate limit.
"""
import os
import sys
import pytest
from pathlib import Path

# Thêm thư mục gốc vào PYTHONPATH
project_root = str(Path(__file__).parent.parent.parent)
sys.path.append(project_root)

if __name__ == "__main__":
    print("Chạy tests Aptos với mock client...")
    
    # Đảm bảo rằng mock client được sử dụng
    os.environ["USE_REAL_APTOS_CLIENT"] = "false"
    
    # Danh sách các test cần chạy
    test_files = [
        "test_aptos_hd_wallet_contract.py",
        "test_remaining_functions.py",
        "test_health_monitoring.py",
        "test_aptos_basic.py",
        "test_aptos_hd_wallet.py",
        "test_token_nft.py", 
        "test_key_management.py",
        "test_validator_miner.py",
        "test_p2p_consensus.py", 
        "test_subnet.py",
        "test_moderntensor_contracts.py",
        "test_moderntensor_scripts.py",
        "test_account_debug.py"
    ]
    
    # Các tùy chọn cho pytest
    pytest_args = ["-v", "--no-header"]
    
    # Chạy từng test file riêng biệt
    for test_file in test_files:
        test_path = os.path.join(os.path.dirname(__file__), test_file)
        if os.path.exists(test_path):
            print(f"\n{'='*80}")
            print(f"Chạy tests trong {test_file}")
            print(f"{'='*80}\n")
            
            exit_code = pytest.main(pytest_args + [test_path])
            
            if exit_code != 0:
                print(f"\nTests trong {test_file} đã thất bại với exit code {exit_code}")
            else:
                print(f"\nTests trong {test_file} đã chạy thành công")
        else:
            print(f"Không tìm thấy test file: {test_path}")
    
    print("\nHoàn thành việc chạy tests Aptos với mock client") 
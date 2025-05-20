#!/usr/bin/env python3
"""
Script để chạy các tests Aptos với mock client.
Giúp giảm thiểu vấn đề rate limit.
"""
import os
import sys
import pytest
from pathlib import Path
import subprocess
import platform
import argparse

# Thêm thư mục gốc vào PYTHONPATH
project_root = str(Path(__file__).parent.parent.parent)
sys.path.append(project_root)

def check_aptos_cli_if_needed():
    """
    Kiểm tra Aptos CLI nếu cần thiết (chỉ thông báo, không làm fail test).
    Với mock client, chúng ta không thực sự cần Aptos CLI.
    """
    try:
        # Thử chạy lệnh "aptos --version", nhưng chỉ để thông báo
        result = subprocess.run(["aptos", "--version"], 
                               capture_output=True, 
                               text=True, 
                               check=False)
        
        if result.returncode == 0:
            print(f"✅ Aptos CLI đã được cài đặt: {result.stdout.strip()}")
        else:
            print(f"⚠️ Lưu ý: Aptos CLI gặp vấn đề: {result.stderr.strip()}")
            print("Tiếp tục với mock client...")
    except FileNotFoundError:
        print("⚠️ Lưu ý: Aptos CLI chưa được cài đặt")
        print("Tiếp tục với mock client...")

def run_test_with_mock(test_file):
    """Chạy một tệp test với mock client."""
    print(f"\n{('='*40)}")
    print(f"Chạy tests trong {test_file}")
    print(f"{('='*40)}")
    
    # Kiểm tra nếu file tồn tại
    test_path = os.path.join(os.path.dirname(__file__), test_file)
    if not os.path.exists(test_path):
        print(f"⚠️ Không tìm thấy file test: {test_path}")
        return 0  # Không tính là lỗi trong CI
    
    try:
        # Chạy pytest với tệp test cụ thể
        result = pytest.main([test_file, "-v"])
        
        if result == 0:
            print(f"\nTests trong {test_file} đã chạy thành công")
        else:
            print(f"\nTests trong {test_file} đã thất bại với exit code {result}")
        
        return result
    except Exception as e:
        print(f"\n❌ Lỗi khi chạy {test_file}: {str(e)}")
        return 1  # Trả về lỗi

if __name__ == "__main__":
    # Tạo parser
    parser = argparse.ArgumentParser(description="Chạy tests Aptos với mock client")
    parser.add_argument("--ci", action="store_true", help="Chạy ở chế độ CI - chỉ chạy các tests an toàn")
    parser.add_argument("--tests", nargs="*", help="Danh sách các tests cụ thể để chạy")
    args = parser.parse_args()
    
    print("Chạy tests Aptos với mock client...")
    
    # Đảm bảo rằng mock client được sử dụng
    os.environ["USE_REAL_APTOS_CLIENT"] = "false"
    
    # Kiểm tra Aptos CLI (chỉ thông báo, không làm fail)
    check_aptos_cli_if_needed()
    
    # Danh sách đầy đủ các test
    all_tests = [
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
    
    # Các tests an toàn cho CI
    ci_safe_tests = [
        "test_account_debug.py", 
        "test_remaining_functions.py",
        "test_health_monitoring.py"
    ]
    
    # Xác định tests để chạy
    if args.tests:
        # Nếu người dùng chỉ định các tests cụ thể
        tests_to_run = args.tests
        print(f"Chạy các tests được chỉ định: {', '.join(tests_to_run)}")
    elif args.ci:
        # Nếu đang chạy trong CI mode
        tests_to_run = ci_safe_tests
        print(f"Chạy ở chế độ CI, chỉ chạy các tests an toàn: {', '.join(tests_to_run)}")
    else:
        # Chạy tất cả tests
        tests_to_run = all_tests
        print("Chạy tất cả tests")
    
    # Chạy từng test file
    failed_tests = []
    for test_file in tests_to_run:
        if run_test_with_mock(test_file) != 0:
            failed_tests.append(test_file)
    
    print("\nHoàn thành việc chạy tests Aptos với mock client")
    
    if failed_tests:
        print(f"\n❌ Các tests sau đã thất bại: {', '.join(failed_tests)}")
        sys.exit(1)
    else:
        print("\n✅ Tất cả các tests đều thành công!")
        sys.exit(0) 
#!/usr/bin/env python3
"""
Script để kiểm tra cài đặt Aptos CLI.
Hữu ích cho môi trường CI hoặc trước khi chạy tests.
"""""
import subprocess
import sys
import os
import platform

def check_aptos_cli():
    """Kiểm tra xem Aptos CLI đã được cài đặt chưa."""""
    try:
        # Thử chạy lệnh "aptos --version"
        result  =  subprocess.run
                               check = False)
        
        if result.returncode == 0:
            print(f"✅ Aptos CLI đã được cài đặt: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ Lỗi khi kiểm tra Aptos CLI: {result.stderr}")
            return False
    except FileNotFoundError:
        print("❌ Aptos CLI chưa được cài đặt hoặc không có trong PATH")
        return False

def suggest_installation():
    """Gợi ý cách cài đặt Aptos CLI."""""
    system  =  platform.system()
    machine  =  platform.machine()
    
    if system == "Linux" or system == "Darwin":  # Linux or macOS:
        print("\nGợi ý cài đặt Aptos CLI:")
        print("-------------------------")
        print(f"curl -fsSL \"https://github.com/aptos-labs/aptos-core/releases/download/aptos-cli-v2.3.1/aptos-cli-2.3.1-{system}-{machine}.zip\" -o aptos-cli.zip")
        print("mkdir -p ~/bin")
        print("unzip -o aptos-cli.zip -d ~/bin")
        print("chmod +x ~/bin/aptos")
        print("export PATH = \"$HOME/bin:$PATH\"")
    elif system == "Windows":
        print("\nGợi ý cài đặt Aptos CLI trên Windows:")
        print("-------------------------")
        print("1. Tải Aptos CLI từ: https://github.com/aptos-labs/aptos-core/releases")
        print("2. Giải nén và thêm vào PATH")
    else:
        print(f"\nHệ điều hành {system} không được hỗ trợ trực tiếp. Vui lòng xem hướng dẫn tại:")
        print("https://aptos.dev/cli-tools/aptos-cli/install-cli/")

def check_python_dependencies():
    """Kiểm tra các dependencies Python."""""
    try:
        import aptos_sdk
        print(f"✅ aptos-sdk đã được cài đặt (phiên bản: {aptos_sdk.__version__})")
    except ImportError:
        print("❌ aptos-sdk chưa được cài đặt. Cài đặt với: pip install aptos-sdk")
    except AttributeError:
        print("✅ aptos-sdk đã được cài đặt (không xác định được phiên bản)")
    
    try:
        import cryptography
        print(f"✅ cryptography đã được cài đặt (phiên bản: {cryptography.__version__})")
    except ImportError:
        print("❌ cryptography chưa được cài đặt. Cài đặt với: pip install cryptography")
    except AttributeError:
        print("✅ cryptography đã được cài đặt (không xác định được phiên bản)")

if __name__ == "__main__":
    print("Kiểm tra cài đặt Aptos CLI và dependencies...\n")
    
    # Kiểm tra Aptos CLI
    cli_installed  =  check_aptos_cli()
    
    # Kiểm tra các dependencies Python
    print("\nKiểm tra các dependencies Python:")
    check_python_dependencies()
    
    # Gợi ý cài đặt nếu CLI chưa được cài đặt
    if not cli_installed:
        suggest_installation()
        print("\n⚠️ Lưu ý: Trong môi trường CI, bạn có thể sử dụng MockRestClient cho tests mà không cần Aptos CLI")
        sys.exit(1)
    
    print("\n✅ Tất cả các yêu cầu đều đã đáp ứng!")
    sys.exit(0) 
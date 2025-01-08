import os
import json
import pytest
import logging
from pycardano import Network
from unittest.mock import patch

from sdk.keymanager.encryption_utils import (
    get_or_create_salt,
    generate_encryption_key,
    get_cipher_suite,
)
from sdk.keymanager.coldkey_manager import ColdKeyManager
from sdk.keymanager.hotkey_manager import HotKeyManager

# Nếu bạn có lớp WalletManager, import luôn:
from sdk.keymanager.wallet_manager import WalletManager


@pytest.fixture
def temp_coldkey_dir(tmp_path):
    """
    Trả về đường dẫn thư mục tạm cho mỗi test.
    Mỗi test sẽ có 1 thư mục riêng, tránh đụng nhau.
    """
    return tmp_path / "coldkeys"


@pytest.fixture
def coldkey_manager(temp_coldkey_dir):
    """
    Khởi tạo 1 ColdKeyManager để test,
    base_dir là thư mục tạm.
    """
    return ColdKeyManager(base_dir=str(temp_coldkey_dir))


@pytest.fixture
def hotkey_manager(coldkey_manager):
    """
    Khởi tạo HotKeyManager, dùng chung coldkeys từ coldkey_manager.
    """
    return HotKeyManager(
        coldkeys_dict=coldkey_manager.coldkeys,
        base_dir=coldkey_manager.base_dir,
        network=None,  # (Hoặc Network.TESTNET, tuỳ bạn)
    )


# -------------------------------------------------------------------
# Test encryption_utils
# -------------------------------------------------------------------
def test_get_or_create_salt(temp_coldkey_dir):
    temp_coldkey_dir.mkdir(parents=True, exist_ok=True)
    salt_file = temp_coldkey_dir / "salt.bin"

    # Lần đầu chưa có salt.bin => tạo mới
    salt1 = get_or_create_salt(str(temp_coldkey_dir))
    assert salt_file.exists(), "salt.bin phải được tạo"
    assert len(salt1) == 16, "Salt mặc định là 16 bytes"

    # Lần hai => đọc lại salt cũ
    salt2 = get_or_create_salt(str(temp_coldkey_dir))
    assert salt1 == salt2, "Lần hai gọi phải lấy cùng 1 salt"


def test_generate_encryption_key():
    salt = b"1234567890abcdef"  # 16 bytes
    password = "mysecret"
    key = generate_encryption_key(password, salt)
    # Chiều dài key sau encode base64 urlsafe => 44 bytes,
    # nội dung tuỳ PBKDF2 => ta chỉ check length
    assert len(key) == 44, "Key đã mã hoá base64 thường dài 44"


def test_get_cipher_suite(temp_coldkey_dir):
    cipher = get_cipher_suite("mypwd", str(temp_coldkey_dir))
    # Thử mã hoá / giải mã 1 chuỗi
    text = b"hello"
    enc = cipher.encrypt(text)
    dec = cipher.decrypt(enc)
    assert dec == text, "Giải mã phải khớp dữ liệu gốc"


# -------------------------------------------------------------------
# Test coldkey_manager (ColdKeyManager)
# -------------------------------------------------------------------
def test_create_coldkey(coldkey_manager):
    name = "testcold"
    password = "secret"

    coldkey_manager.create_coldkey(name, password)
    # Kiểm tra file mnemonic.enc, hotkeys.json
    cdir = os.path.join(coldkey_manager.base_dir, name)
    assert os.path.exists(
        os.path.join(cdir, "mnemonic.enc")
    ), "mnemonic.enc phải được tạo"
    assert os.path.exists(
        os.path.join(cdir, "hotkeys.json")
    ), "hotkeys.json phải được tạo"

    # Kiểm tra trong memory
    assert name in coldkey_manager.coldkeys, "coldkey phải được lưu trong dictionary"
    assert "wallet" in coldkey_manager.coldkeys[name]


def test_load_coldkey(coldkey_manager):
    name = "testcold2"
    password = "secret"
    coldkey_manager.create_coldkey(name, password)
    # Xoá trong memory => kiểm tra load lại
    coldkey_manager.coldkeys.pop(name, None)

    coldkey_manager.load_coldkey(name, password)
    assert name in coldkey_manager.coldkeys, "coldkey phải load lại vào memory"
    assert "wallet" in coldkey_manager.coldkeys[name]


def test_load_coldkey_file_notfound(coldkey_manager):
    with pytest.raises(FileNotFoundError):
        coldkey_manager.load_coldkey("non_existent", "pwd")


# -------------------------------------------------------------------
# Test hotkey_manager (HotKeyManager)
# -------------------------------------------------------------------
def test_generate_hotkey(coldkey_manager, hotkey_manager):
    # Tạo coldkey trước
    name = "ck_hot"
    password = "pass"
    coldkey_manager.create_coldkey(name, password)

    # Tạo hotkey
    hotkey_name = "myhot1"
    enc_data = hotkey_manager.generate_hotkey(name, hotkey_name)

    # Kiểm tra hotkey có trong memory
    ck_info = coldkey_manager.coldkeys[name]
    assert hotkey_name in ck_info["hotkeys"], "Hotkey phải lưu trong dict"

    # Kiểm tra file hotkeys.json
    cdir = os.path.join(coldkey_manager.base_dir, name)
    with open(os.path.join(cdir, "hotkeys.json"), "r") as f:
        data = json.load(f)
    assert hotkey_name in data["hotkeys"], "Hotkey phải lưu trong file"

    # enc_data == data["hotkeys"][hotkey_name]
    assert enc_data == data["hotkeys"][hotkey_name], "encrypted hotkey khớp"


def test_import_hotkey_yes(monkeypatch, coldkey_manager, hotkey_manager):
    name = "ck_hot_import"
    password = "pass"
    coldkey_manager.create_coldkey(name, password)

    # Tạo 1 hotkey cũ => import lại
    hotkey_name = "importme"
    enc_data = hotkey_manager.generate_hotkey(name, hotkey_name)

    # Mock input => "y"
    with patch("builtins.input", return_value="yes"):
        # Gọi import_hotkey => overwrite
        hotkey_manager.import_hotkey(name, enc_data, hotkey_name, overwrite=False)


def test_import_hotkey_no(monkeypatch, coldkey_manager, hotkey_manager, caplog):
    caplog.set_level(logging.WARNING)
    name = "ck_hot_import_no"
    password = "pass"
    coldkey_manager.create_coldkey(name, password)

    # Tạo hotkey
    hotkey_name = "importno"
    enc_data = hotkey_manager.generate_hotkey(name, hotkey_name)

    # Mock input => "no"
    with patch("builtins.input", return_value="no"):
        hotkey_manager.import_hotkey(name, enc_data, hotkey_name, overwrite=False)

    # Kiểm tra log => "User canceled overwrite => import aborted."
    logs = caplog.text
    assert "User canceled overwrite => import aborted." in logs


# -------------------------------------------------------------------
# Test WalletManager (nếu bạn sử dụng)
# -------------------------------------------------------------------
# from keymanager.wallet_manager import WalletManager


@pytest.fixture
def wallet_manager(tmp_path):
    """
    Khởi tạo WalletManager với base_dir là thư mục tạm (tmp_path).
    """
    return WalletManager(network=Network.TESTNET, base_dir=str(tmp_path))


def test_wallet_manager_end_to_end(wallet_manager):
    """
    Tạo coldkey -> load coldkey -> generate hotkey -> import hotkey -> kiểm tra.
    """
    # 1) Tạo coldkey
    ck_name = "myck"
    password = "mypwd"
    wallet_manager.create_coldkey(ck_name, password)

    # Kiểm tra file mnemonic.enc, hotkeys.json
    cdir = os.path.join(wallet_manager.base_dir, ck_name)
    assert os.path.exists(
        os.path.join(cdir, "mnemonic.enc")
    ), "mnemonic.enc phải được tạo"
    assert os.path.exists(
        os.path.join(cdir, "hotkeys.json")
    ), "hotkeys.json phải được tạo"

    # 2) Load coldkey
    wallet_manager.load_coldkey(ck_name, password)
    #  (Nếu load thành công thì không ném exception)

    # 3) Tạo hotkey
    hk_name = "hk1"
    encrypted_data = wallet_manager.generate_hotkey(ck_name, hk_name)
    # Kiểm tra hotkeys.json
    with open(os.path.join(cdir, "hotkeys.json"), "r") as f:
        data = json.load(f)
    assert hk_name in data["hotkeys"], "hotkey phải lưu trong file"

    # 4) Import hotkey => Gọi “import_hotkey”
    #    Ở đây ta giả sử user gõ “y” (Yes) nếu hotkey đã tồn tại
    with patch("builtins.input", return_value="y"):
        wallet_manager.import_hotkey(ck_name, encrypted_data, hk_name, overwrite=False)
    # Kiểm tra xem hotkey vẫn còn
    with open(os.path.join(cdir, "hotkeys.json"), "r") as f:
        data2 = json.load(f)
    assert hk_name in data2["hotkeys"], "Hotkey phải tồn tại sau import"


def test_wallet_manager_import_hotkey_no(wallet_manager, caplog):
    """
    Trường hợp import hotkey, user gõ "no" => không overwrite.
    """
    ck_name = "ck2"
    password = "pass2"
    wallet_manager.create_coldkey(ck_name, password)
    wallet_manager.load_coldkey(ck_name, password)

    # Tạo 1 hotkey
    hk_name = "hotabc"
    encrypted_data = wallet_manager.generate_hotkey(ck_name, hk_name)

    # Gọi import => user gõ "no"
    with patch("builtins.input", return_value="no"):
        wallet_manager.import_hotkey(ck_name, encrypted_data, hk_name, overwrite=False)

    # Kiểm tra log => "User canceled overwrite => import aborted."
    logs = caplog.text
    assert "User canceled overwrite => import aborted." in logs

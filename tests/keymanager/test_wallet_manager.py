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
from sdk.keymanager.wallet_manager import WalletManager 

# -------------------------------------------------------------------
# FIXTURES
# -------------------------------------------------------------------

@pytest.fixture
def temp_coldkey_dir(tmp_path):
    """
    Tạo thư mục tạm `coldkeys` bên trong tmp_path, tránh xung đột test.
    """
    return tmp_path / "coldkeys"

@pytest.fixture
def coldkey_manager(temp_coldkey_dir):
    """
    Khởi tạo ColdKeyManager cho test, base_dir là thư mục tạm.
    """
    return ColdKeyManager(base_dir=str(temp_coldkey_dir))

@pytest.fixture
def hotkey_manager(coldkey_manager):
    """
    Khởi tạo HotKeyManager, dùng chung dict coldkeys của coldkey_manager.
    """
    return HotKeyManager(
        coldkeys_dict=coldkey_manager.coldkeys,
        base_dir=coldkey_manager.base_dir,
        network=None,  # Hoặc Network.TESTNET
    )

@pytest.fixture
def wallet_manager(tmp_path):
    """
    WalletManager với network=TESTNET, base_dir là thư mục tạm (tmp_path).
    """
    return WalletManager(network=Network.TESTNET, base_dir=str(tmp_path))

# -------------------------------------------------------------------
# TEST encryption_utils
# -------------------------------------------------------------------

def test_get_or_create_salt(temp_coldkey_dir):
    temp_coldkey_dir.mkdir(parents=True, exist_ok=True)
    salt_file = temp_coldkey_dir / "salt.bin"

    # Lần đầu => tạo mới salt
    salt1 = get_or_create_salt(str(temp_coldkey_dir))
    assert salt_file.exists(), "salt.bin phải được tạo"
    assert len(salt1) == 16, "Salt mặc định là 16 bytes"

    # Lần hai => đọc lại salt cũ
    salt2 = get_or_create_salt(str(temp_coldkey_dir))
    assert salt1 == salt2, "Gọi lần 2 phải lấy cùng 1 salt"

def test_generate_encryption_key():
    salt = b"1234567890abcdef"  # 16 bytes
    password = "mysecret"
    key = generate_encryption_key(password, salt)
    # Key base64 urlsafe => thường 44 bytes
    assert len(key) == 44, "Key mã hoá base64 thường ~44 bytes"

def test_get_cipher_suite(temp_coldkey_dir):
    # Kiểm tra mã hoá / giải mã
    cipher = get_cipher_suite("mypwd", str(temp_coldkey_dir))
    text = b"hello"
    enc = cipher.encrypt(text)
    dec = cipher.decrypt(enc)
    assert dec == text, "Giải mã phải khớp ban đầu"

# -------------------------------------------------------------------
# TEST coldkey_manager
# -------------------------------------------------------------------

def test_create_coldkey(coldkey_manager):
    name = "testcold"
    password = "secret"

    coldkey_manager.create_coldkey(name, password)
    cdir = os.path.join(coldkey_manager.base_dir, name)

    # Kiểm tra file
    assert os.path.exists(os.path.join(cdir, "mnemonic.enc")), "mnemonic.enc phải tồn tại"
    assert os.path.exists(os.path.join(cdir, "hotkeys.json")), "hotkeys.json phải tồn tại"

    # Kiểm tra trong memory
    assert name in coldkey_manager.coldkeys, "coldkey phải được lưu trong dictionary"
    assert "wallet" in coldkey_manager.coldkeys[name]

def test_create_coldkey_duplicate(coldkey_manager):
    """
    Giả sử code 'create_coldkey' không cho tạo trùng tên => raise Exception.
    (Hoặc nếu code bạn cho phép overwrite thì thay logic test.)
    """
    name = "dupCk"
    coldkey_manager.create_coldkey(name, "pwd")

    # Tạo trùng tên => test code
    with pytest.raises(Exception) as excinfo:
        coldkey_manager.create_coldkey(name, "pwd2")
    # Kiểm tra message
    assert "already exists" in str(excinfo.value).lower() or "duplicate" in str(excinfo.value).lower()

def test_load_coldkey(coldkey_manager):
    name = "testcold2"
    password = "secret"
    coldkey_manager.create_coldkey(name, password)

    # Xoá memory => rồi load
    coldkey_manager.coldkeys.pop(name, None)
    coldkey_manager.load_coldkey(name, password)

    assert name in coldkey_manager.coldkeys, "coldkey phải load lại"
    assert "wallet" in coldkey_manager.coldkeys[name]

def test_load_coldkey_file_notfound(coldkey_manager):
    # Ko tồn tại => raise FileNotFoundError
    with pytest.raises(FileNotFoundError):
        coldkey_manager.load_coldkey("non_existent", "pwd")

def test_load_coldkey_wrong_password(coldkey_manager):
    """
    Nếu code coldkey_manager.load_coldkey(name, wrong_pwd) có check password => throw Exception?
    Nếu bạn chưa code check, test này fail => tuỳ bạn cài đặt logic.
    """
    name = "myck_wrongpwd"
    password = "okpwd"
    coldkey_manager.create_coldkey(name, password)

    with pytest.raises(Exception) as excinfo:
        coldkey_manager.load_coldkey(name, "wrongpwd")
    assert "invalid password" in str(excinfo.value).lower() or "decrypt" in str(excinfo.value).lower()

# -------------------------------------------------------------------
# TEST hotkey_manager
# -------------------------------------------------------------------

def test_generate_hotkey(coldkey_manager, hotkey_manager):
    name = "ck_hot"
    password = "pass"
    coldkey_manager.create_coldkey(name, password)

    hotkey_name = "myhot1"
    enc_data = hotkey_manager.generate_hotkey(name, hotkey_name)

    # Kiểm tra memory
    ck_info = coldkey_manager.coldkeys[name]
    assert hotkey_name in ck_info["hotkeys"], "Hotkey phải lưu trong dict"

    # Kiểm tra file
    cdir = os.path.join(coldkey_manager.base_dir, name)
    with open(os.path.join(cdir, "hotkeys.json"), "r") as f:
        data = json.load(f)

    assert hotkey_name in data["hotkeys"], "hotkey_name phải nằm trong data['hotkeys']"

    # So sánh: bây giờ data["hotkeys"][hotkey_name] là 1 dict, có 'address' & 'encrypted_data'
    # -> Kiểm tra enc_data == data["hotkeys"][hotkey_name]["encrypted_data"]
    assert enc_data == data["hotkeys"][hotkey_name]["encrypted_data"], \
        "encrypted_data phải trùng khớp"


def test_generate_hotkey_duplicate(coldkey_manager, hotkey_manager):
    """
    Trường hợp tạo hotkey trùng tên => nếu code cấm => raise Exception
    hoặc code overwrite => test logic overwrite tuỳ.
    """
    name = "ck_dup"
    coldkey_manager.create_coldkey(name, "pwd")

    hotkey_name = "hotA"
    hotkey_manager.generate_hotkey(name, hotkey_name)

    # Tạo hotkey trùng tên => tuỳ logic
    with pytest.raises(Exception) as excinfo:
        hotkey_manager.generate_hotkey(name, hotkey_name)
    assert "already exists" in str(excinfo.value).lower() or "duplicate" in str(excinfo.value).lower()

def test_import_hotkey_yes(monkeypatch, coldkey_manager, hotkey_manager):
    name = "ck_hot_import"
    password = "pass"
    coldkey_manager.create_coldkey(name, password)

    hotkey_name = "importme"
    enc_data = hotkey_manager.generate_hotkey(name, hotkey_name)

    # Mock input => "y" => chấp nhận overwrite
    with patch("builtins.input", return_value="yes"):
        hotkey_manager.import_hotkey(name, enc_data, hotkey_name, overwrite=False)

def test_import_hotkey_no(monkeypatch, coldkey_manager, hotkey_manager, caplog):
    caplog.set_level(logging.WARNING)
    name = "ck_hot_import_no"
    password = "pass"
    coldkey_manager.create_coldkey(name, password)

    hotkey_name = "importno"
    enc_data = hotkey_manager.generate_hotkey(name, hotkey_name)

    # Mock input => "no"
    with patch("builtins.input", return_value="no"):
        hotkey_manager.import_hotkey(name, enc_data, hotkey_name, overwrite=False)

    logs = caplog.text
    assert "User canceled overwrite => import aborted." in logs

# -------------------------------------------------------------------
# TEST WalletManager END-TO-END
# -------------------------------------------------------------------

def test_wallet_manager_end_to_end(wallet_manager):
    """
    Tạo coldkey -> load coldkey -> generate hotkey -> import hotkey -> kiểm tra.
    """
    ck_name = "myck"
    password = "mypwd"
    wallet_manager.create_coldkey(ck_name, password)

    cdir = os.path.join(wallet_manager.base_dir, ck_name)
    assert os.path.exists(os.path.join(cdir, "mnemonic.enc"))
    assert os.path.exists(os.path.join(cdir, "hotkeys.json"))

    # Load
    wallet_manager.load_coldkey(ck_name, password)

    # Tạo hotkey
    hk_name = "hk1"
    encrypted_data = wallet_manager.generate_hotkey(ck_name, hk_name)
    with open(os.path.join(cdir, "hotkeys.json"), "r") as f:
        data = json.load(f)
    assert hk_name in data["hotkeys"]

    # Import hotkey => Yes => overwrite
    with patch("builtins.input", return_value="y"):
        wallet_manager.import_hotkey(ck_name, encrypted_data, hk_name, overwrite=False)

    with open(os.path.join(cdir, "hotkeys.json"), "r") as f:
        data2 = json.load(f)
    assert hk_name in data2["hotkeys"]

def test_wallet_manager_import_hotkey_no(wallet_manager, caplog):
    """
    Case import hotkey, user types "no" => do not overwrite.
    """
    ck_name = "ck2"
    password = "pass2"
    wallet_manager.create_coldkey(ck_name, password)
    wallet_manager.load_coldkey(ck_name, password)

    hk_name = "hotabc"
    encrypted_data = wallet_manager.generate_hotkey(ck_name, hk_name)

    with patch("builtins.input", return_value="no"):
        wallet_manager.import_hotkey(ck_name, encrypted_data, hk_name, overwrite=False)

    logs = caplog.text
    assert "User canceled overwrite => import aborted." in logs

def test_wallet_manager_wrong_password(wallet_manager):
    """
    Test load_coldkey with wrong password => expect Exception? 
    (Depending on your code)
    """
    ck_name = "ck_wrongpwd"
    password = "secret"
    wallet_manager.create_coldkey(ck_name, password)

    with pytest.raises(Exception) as excinfo:
        wallet_manager.load_coldkey(ck_name, "wrongpwd")
    assert "invalid password" in str(excinfo.value).lower() or "failed to decrypt" in str(excinfo.value).lower()

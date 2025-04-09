# Lưu ý: KHÔNG BAO GIỜ viết mnemonic trực tiếp vào code như thế này trong môi trường production!
# Đây chỉ là ví dụ minh họa.
from pycardano import Mnemonic, HDWallet, Network, Address

mnemonic_phrase = "word1 word2 word3 ... word24" # Thay thế bằng mnemonic thật của bạn

# Tạo seed từ mnemonic
seed = Mnemonic(mnemonic_phrase.split()).to_seed()

# Tạo HDWallet từ seed
root_key = HDWallet.from_seed(seed)

# Tạo khóa cho tài khoản đầu tiên (index 0)
# Đường dẫn: m/1852'/1815'/0'
account_key = root_key.derive(f"m/1852'/1815'/0'")

# Tạo khóa thanh toán đầu tiên (role 0, index 0)
# Đường dẫn: m/1852'/1815'/0'/0/0
payment_pvk = account_key.derive("m/0/0").private_key
payment_vk = payment_pvk.to_verification_key()

# Tạo khóa staking đầu tiên (role 2, index 0)
# Đường dẫn: m/1852'/1815'/0'/2/0
stake_pvk = account_key.derive("m/2/0").private_key
stake_vk = stake_pvk.to_verification_key()

# Từ payment_vk và stake_vk, bạn có thể tạo địa chỉ Base Address cho mạng Mainnet hoặc Testnet
address = Address(payment_part=payment_vk.hash(), staking_part=stake_vk.hash(), network=Network.MAINNET)
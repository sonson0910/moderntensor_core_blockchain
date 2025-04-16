import sys
import logging
from pycardano import (
    StakeCredential,
    StakeRegistration,
    StakeDelegation,
    PoolKeyHash,
    TransactionBuilder,
    Transaction,
    TransactionWitnessSet,
    Network,
    Address,
    Withdrawals,
)
from pycardano.crypto.bech32 import bech32_decode
from blockfrost import ApiError, ApiUrls, BlockFrostApi, BlockFrostIPFS
from sdk.config.settings import settings
from sdk.keymanager.decryption_utils import decode_hotkey_skey
from sdk.service.context import get_chain_context

logger = logging.getLogger(__name__)


class Wallet:
    def __init__(self, coldkey_name, hotkey_name, password):
        """
        Khởi tạo ví bằng cách giải mã khóa hotkey.
        """
        self.api = BlockFrostApi(
            project_id="preprod06dzhzKlynuTInzvxHDH5cXbdHo524DE",
            base_url="https://cardano-preprod.blockfrost.io/api/",
        )
        self.base_dir = settings.HOTKEY_BASE_DIR
        self.chain_context = get_chain_context()
        self.network = settings.CARDANO_NETWORK
        # Giải mã hotkey từ file
        self.payment_sk, self.stake_sk = decode_hotkey_skey(
            self.base_dir, coldkey_name, hotkey_name, password
        )

        self.stake_vk = self.stake_sk.to_verification_key()
        self.payment_vk = self.payment_sk.to_verification_key()
        self.stake_key_hash = self.stake_vk.hash()
        self.payment_key_hash = self.payment_vk.hash()

        # Địa chỉ ví
        self.payment_address = Address(
            payment_part=self.payment_key_hash, network=Network.TESTNET
        )
        self.stake_address = Address(
            staking_part=self.stake_key_hash, network=Network.TESTNET
        )
        self.main_address = Address(
            payment_part=self.payment_key_hash,
            staking_part=self.stake_key_hash,
            network=Network.TESTNET,
        )
        logger.debug(f"[WalletInit] Main address: {self.main_address}")
        logger.debug(f"[WalletInit] Payment address: {self.payment_address}")
        logger.debug(f"[WalletInit] Stake address: {self.stake_address}")

    def get_utxos(self):

        try:
            utxos = self.api.address_utxos(self.main_address)
            return utxos
        except Exception as e:
            if hasattr(e, "status_code") and e.status_code == 404:
                logger.warning(
                    f"[get_utxos] No UTxOs found for address {self.main_address}."
                )
                if self.network == Network.TESTNET:
                    logger.info(
                        "Consider requesting tADA from the faucet: https://docs.cardano.org/cardano-testnets/tools/faucet/"
                    )
            else:
                logger.exception(
                    f"[get_utxos] Failed to fetch UTxOs for address {self.main_address}: {e}"
                )
            return []

    def get_balances(self):
        utxos = self.get_utxos()
        if not utxos:
            logger.info("[get_balances] No UTxOs found to calculate balance.")
            return

        logger.info("--- UTXO Balances --- ")
        total_lovelace = 0
        tokens_summary = {}
        for utxo in utxos:
            utxo_lovelace = 0
            utxo_tokens_str = ""
            for token in utxo.amount:
                if token.unit == "lovelace":
                    utxo_lovelace = token.quantity
                    total_lovelace += utxo_lovelace
                else:
                    token_key = f"{token.policy_id}.{token.asset_name}"
                    tokens_summary[token_key] = (
                        tokens_summary.get(token_key, 0) + token.quantity
                    )
                    utxo_tokens_str += f" + {token.quantity} {token.unit}"
            logger.info(
                f"UTxO: {utxo.tx_hash}#{utxo.tx_index} \t {utxo_lovelace / 1000000:.6f} ADA{utxo_tokens_str}"
            )
        logger.info(f"Total ADA: {total_lovelace / 1000000:.6f}")
        if tokens_summary:
            logger.info("Total Tokens:")
            for key, total_qty in tokens_summary.items():
                logger.info(f"  - {key}: {total_qty}")
        logger.info("---------------------")

    def sign_transaction(self, tx_body):
        """
        Ký giao dịch bằng khóa của ví.
        """
        tx = Transaction(body=tx_body, witness_set=TransactionWitnessSet())
        tx.sign([self.payment_sk, self.stake_sk])
        return tx

    def submit_transaction(self, signed_tx):
        """
        Gửi giao dịch lên blockchain.
        """
        return self.chain_context.submit_tx(signed_tx)


class StakingService:
    def __init__(self, wallet: Wallet):
        """
        Khởi tạo dịch vụ staking với ví của người dùng.
        """
        self.chain_context = get_chain_context()
        self.wallet = wallet

    def delegate_stake(self, pool_id: str):
        """
        Ủy quyền stake đến một pool cụ thể.
        """
        logger.info(f"[delegate_stake] Attempting delegation to pool: {pool_id}")
        # B1: Tạo chứng chỉ đăng ký stake
        stake_credential = StakeCredential(self.wallet.stake_key_hash)
        stake_reg = StakeRegistration(stake_credential)

        # B2: Chuyển đổi Pool ID sang PoolKeyHash
        pool_keyhash = PoolKeyHash(bytes.fromhex(pool_id))
        stake_delegate = StakeDelegation(stake_credential, pool_keyhash)

        # B3: Xây dựng giao dịch
        tx_builder = TransactionBuilder(self.chain_context)

        # Thêm địa chỉ chứa ADA để trả phí
        tx_builder.add_input_address(self.wallet.main_address)

        # Thêm chứng chỉ staking vào giao dịch
        tx_builder.certificates = [stake_reg, stake_delegate]

        # Đặt phí buffer để tránh lỗi
        # tx_builder.fee_buffer = 500000

        # Thêm người ký giao dịch
        tx_builder.required_signers = [
            self.wallet.payment_key_hash,
            self.wallet.stake_key_hash,
        ]

        # Xây dựng giao dịch đã ký
        try:
            tx = tx_builder.build_and_sign(
                [self.wallet.payment_sk, self.wallet.stake_sk],
                change_address=self.wallet.main_address,
            )
            # Gửi giao dịch lên blockchain
            self.chain_context.submit_tx(tx)
            logger.info(
                f"[delegate_stake] Delegation transaction successfully submitted: {tx.id}"
            )
            return tx.id
        except Exception as e:
            logger.exception(
                f"[delegate_stake] Failed to build, sign, or submit delegation tx: {e}"
            )
            return None

    def re_delegate_stake(self, new_pool_id: str):
        logger.info(
            f"[re_delegate_stake] Attempting re-delegation to pool: {new_pool_id}"
        )
        stake_credential = StakeCredential(self.wallet.stake_key_hash)
        # B2: Chuyển đổi Pool ID sang PoolKeyHash
        pool_keyhash = PoolKeyHash(bytes.fromhex(new_pool_id))
        stake_delegate = StakeDelegation(stake_credential, pool_keyhash)

        # B3: Xây dựng giao dịch
        tx_builder = TransactionBuilder(self.chain_context)

        # Thêm địa chỉ chứa ADA để trả phí
        tx_builder.add_input_address(self.wallet.main_address)

        # Thêm chứng chỉ staking vào giao dịch
        tx_builder.certificates = [stake_delegate]

        # Đặt phí buffer để tránh lỗi
        # tx_builder.fee_buffer = 500000

        # Thêm người ký giao dịch
        tx_builder.required_signers = [
            self.wallet.payment_key_hash,
            self.wallet.stake_key_hash,
        ]

        # Xây dựng giao dịch đã ký
        try:
            tx = tx_builder.build_and_sign(
                [self.wallet.payment_sk, self.wallet.stake_sk],
                change_address=self.wallet.main_address,
            )
            self.chain_context.submit_tx(tx)
            logger.info(
                f"[re_delegate_stake] Re-delegation transaction successfully submitted: {tx.id}"
            )
            return tx.id
        except Exception as e:
            logger.exception(
                f"[re_delegate_stake] Failed to build, sign, or submit re-delegation tx: {e}"
            )
            return None

    def withdrawal_reward(self):
        """
        Rút phần thưởng staking về ví chính.
        """
        logger.info(
            f"[withdrawal_reward] Checking rewards for stake address: {self.wallet.stake_address}"
        )
        try:
            account_info = self.wallet.api.accounts(str(self.wallet.stake_address))
            withdrawal_reward_amounts = int(account_info.withdrawable_amount)
        except Exception as e:
            logger.exception(
                f"[withdrawal_reward] Failed to fetch account info for {self.wallet.stake_address}: {e}"
            )
            return None

        if withdrawal_reward_amounts == 0:
            logger.info("[withdrawal_reward] No withdrawable rewards found.")
            return None

        logger.info(
            f"[withdrawal_reward] Withdrawing {withdrawal_reward_amounts} Lovelace."
        )

        tx_builder = TransactionBuilder(self.chain_context)
        tx_builder.add_input_address(self.wallet.main_address)
        try:
            stake_addr_bytes = bytes(
                Address.from_primitive(str(self.wallet.stake_address))
            )
            withdrawals = Withdrawals({stake_addr_bytes: withdrawal_reward_amounts})
            tx_builder.withdrawals = withdrawals
        except Exception as e:
            logger.exception(
                f"[withdrawal_reward] Failed to create Withdrawals object: {e}"
            )
            return None

        tx_builder.required_signers = [
            self.wallet.payment_key_hash,
            self.wallet.stake_key_hash,
        ]

        try:
            tx = tx_builder.build_and_sign(
                [self.wallet.payment_sk, self.wallet.stake_sk],
                change_address=self.wallet.main_address,
            )
            self.chain_context.submit_tx(tx)
            logger.info(
                f"[withdrawal_reward] Withdrawal transaction successfully submitted: {tx.id}"
            )
            return tx.id
        except Exception as e:
            logger.exception(
                f"[withdrawal_reward] Failed to build, sign, or submit withdrawal tx: {e}"
            )
            return None


wallet = Wallet(coldkey_name="kickoff", hotkey_name="hk1", password="123456")
wallet.get_utxos()
wallet.get_balances()

# # Khởi tạo dịch vụ staking
staking_service = StakingService(wallet)
# print(f"Done constructer staking service")
# Đăng ký stake một khi đăng kí rồi là không có hủy chỉ có thể đăng kí pool mới
# tx_id_delegate_stake = staking_service.delegate_stake(pool_id="429e1cf4c75799b4148402452aa0edd512111485e5e1cbe7cf93b696")


# Đăng ký pool mới
# tx_id_redelegate_stake = staking_service.re_delegate_stake(new_pool_id="998dd7a084430fb80d204b9d4700ef47cdd6d9bdad1e8eb2c87bc2ad")

# Rút phần thưởng: Nhưng để rút được phần thưởng yêu cầu phải ủy quyền vào pool( nếu không ủy quyền thì sẽ có lỗi)

# TransactionFailedException: Failed to submit transaction.
# Error code: 400. Error message: {"contents":{"contents":{"contents":{"era":"ShelleyBasedEraConway",
# "error":["ConwayWdrlNotDelegatedToDRep (KeyHash {unKeyHash = \"7e10785dc0bc5c4639863e155679f7c9c719deac3021df37453a70a3\"}
# :| [])"],"kind":"ShelleyTxValidationError"},"tag":"TxValidationErrorInCardanoMode"},"tag":"TxCmdTxSubmitValidationError"},
# "tag":"TxSubmitFail"}
tx_id_withdrawal_reward = staking_service.withdrawal_reward()

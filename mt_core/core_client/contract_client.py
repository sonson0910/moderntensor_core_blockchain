"""
Contract client for ModernTensor smart contracts on Core blockchain
"""

import json
import logging
from typing import Dict, Any, List, Optional, Union
from web3 import Web3
from web3.contract import Contract
from eth_account import Account
from eth_utils import to_checksum_address

logger = logging.getLogger(__name__)


class ModernTensorCoreClient:
    """
    Client tương tác với các smart contract ModernTensor trên Core blockchain.

    Cung cấp các phương thức để:
    - Đăng ký Miner/Validator mới
    - Cập nhật thông tin Miner/Validator
    - Truy vấn thông tin Miner/Validator/Subnet
    - Bitcoin staking integration
    - Dual staking rewards
    """

    def __init__(
        self,
        w3: Web3,
        contract_address: str,
        account: Optional[Account] = None,
        contract_abi: Optional[List[Dict]] = None,
    ):
        self._current_nonce = None
        """
        Khởi tạo client ModernTensor cho Core blockchain.

        Args:
            w3: Web3 instance kết nối với Core blockchain
            contract_address: Địa chỉ của contract ModernTensor trên Core
            account: Account để ký giao dịch (optional)
            contract_abi: ABI của contract (optional, sẽ load từ artifacts nếu None)
        """
        self.w3 = w3
        self.contract_address = to_checksum_address(contract_address)
        self.account = account

        # Load contract ABI
        if contract_abi is None:
            contract_abi = self._load_contract_abi()

        # Initialize contract
        self.contract = self.w3.eth.contract(
            address=self.contract_address, abi=contract_abi
        )

        logger.info(f"✅ ModernTensor Core client initialized: {self.contract_address}")

    def _load_contract_abi(self) -> List[Dict]:
        """Load contract ABI from artifacts"""
        try:
            import os
            from pathlib import Path

            # Try to load from artifacts file
            current_file = Path(__file__)
            artifacts_path = (
                current_file.parent.parent
                / "smartcontract"
                / "artifacts"
                / "contracts"
                / "ModernTensor.sol"
                / "ModernTensor.json"
            )

            if artifacts_path.exists():
                with open(artifacts_path, "r") as f:
                    contract_data = json.load(f)
                    abi = contract_data.get("abi", [])
                    if abi:
                        logger.info(
                            f"✅ Loaded ABI from artifacts: {len(abi)} functions"
                        )
                        return abi

            logger.warning(
                f"⚠️ Artifacts not found at {artifacts_path}, using fallback ABI"
            )

        except Exception as e:
            logger.warning(f"⚠️ Failed to load artifacts ABI: {e}, using fallback")

        # Fallback to basic ABI
        return [
            {
                "inputs": [
                    {"name": "subnetId", "type": "uint64"},
                    {"name": "coreStake", "type": "uint256"},
                    {"name": "btcStake", "type": "uint256"},
                    {"name": "apiEndpoint", "type": "string"},
                ],
                "name": "registerMiner",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function",
            },
            {
                "inputs": [
                    {"name": "subnetId", "type": "uint64"},
                    {"name": "coreStake", "type": "uint256"},
                    {"name": "btcStake", "type": "uint256"},
                    {"name": "apiEndpoint", "type": "string"},
                ],
                "name": "registerValidator",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function",
            },
            {
                "inputs": [
                    {"name": "minerAddress", "type": "address"},
                    {"name": "newPerformance", "type": "uint64"},
                    {"name": "newTrustScore", "type": "uint64"},
                ],
                "name": "updateMinerScores",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function",
            },
            {
                "inputs": [{"name": "minerAddress", "type": "address"}],
                "name": "getMinerInfo",
                "outputs": [
                    {"name": "uid", "type": "bytes32"},
                    {"name": "subnetId", "type": "uint64"},
                    {"name": "coreStake", "type": "uint256"},
                    {"name": "btcStake", "type": "uint256"},
                    {"name": "performance", "type": "uint64"},
                    {"name": "trustScore", "type": "uint64"},
                    {"name": "incentiveRatio", "type": "uint64"},
                    {"name": "lastUpdateTime", "type": "uint256"},
                    {"name": "registrationTime", "type": "uint256"},
                    {"name": "status", "type": "uint8"},
                    {"name": "uid2", "type": "bytes32"},
                    {"name": "apiEndpoint", "type": "string"},
                    {"name": "owner", "type": "address"},
                ],
                "stateMutability": "view",
                "type": "function",
            },
            {
                "inputs": [{"name": "validatorAddress", "type": "address"}],
                "name": "getValidatorInfo",
                "outputs": [
                    {"name": "uid", "type": "bytes32"},
                    {"name": "subnetId", "type": "uint64"},
                    {"name": "coreStake", "type": "uint256"},
                    {"name": "btcStake", "type": "uint256"},
                    {"name": "performance", "type": "uint64"},
                    {"name": "trustScore", "type": "uint64"},
                    {"name": "incentiveRatio", "type": "uint64"},
                    {"name": "lastUpdateTime", "type": "uint256"},
                    {"name": "registrationTime", "type": "uint256"},
                    {"name": "status", "type": "uint8"},
                    {"name": "uid2", "type": "bytes32"},
                    {"name": "apiEndpoint", "type": "string"},
                    {"name": "owner", "type": "address"},
                ],
                "stateMutability": "view",
                "type": "function",
            },
            {
                "inputs": [],
                "name": "VALIDATOR_ROLE",
                "outputs": [{"name": "", "type": "bytes32"}],
                "stateMutability": "view",
                "type": "function",
            },
            {
                "inputs": [
                    {"name": "role", "type": "bytes32"},
                    {"name": "account", "type": "address"},
                ],
                "name": "hasRole",
                "outputs": [{"name": "", "type": "bool"}],
                "stateMutability": "view",
                "type": "function",
            },
        ]

    def register_miner(
        self,
        subnet_id: int,
        core_stake: int,
        btc_stake: int,
        api_endpoint: str,
        gas_price: Optional[int] = None,
    ) -> str:
        """
        Đăng ký một miner mới.

        Args:
            subnet_id: ID của subnet
            core_stake: Số lượng CORE tokens stake
            btc_stake: Số lượng BTC tokens stake
            api_endpoint: Endpoint API của miner
            gas_price: Gas price (optional)

        Returns:
            Transaction hash
        """
        if not self.account:
            raise ValueError("Account required for transaction")

        # Get nonce
        if self._current_nonce is None:
            self._current_nonce = self.w3.eth.get_transaction_count(
                self.account.address
            )

        # Build transaction
        txn = self.contract.functions.registerMiner(
            subnet_id, core_stake, btc_stake, api_endpoint
        ).build_transaction(
            {
                "from": self.account.address,
                "gas": 500000,
                "gasPrice": gas_price or self.w3.eth.gas_price,
                "nonce": self._current_nonce,
            }
        )

        # Increment nonce for next transaction
        self._current_nonce += 1

        # Sign and send transaction
        signed_txn = self.account.sign_transaction(txn)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)

        logger.info(f"Miner registration transaction sent: {tx_hash.hex()}")
        return tx_hash.hex()

    def register_validator(
        self,
        subnet_id: int,
        core_stake: int,
        btc_stake: int,
        api_endpoint: str,
        gas_price: Optional[int] = None,
    ) -> str:
        """
        Đăng ký một validator mới.

        Args:
            subnet_id: ID của subnet
            core_stake: Số lượng CORE tokens stake
            btc_stake: Số lượng BTC tokens stake
            api_endpoint: Endpoint API của validator
            gas_price: Gas price (optional)

        Returns:
            Transaction hash
        """
        if not self.account:
            raise ValueError("Account required for transaction")

        # Get nonce
        if self._current_nonce is None:
            self._current_nonce = self.w3.eth.get_transaction_count(
                self.account.address
            )

        # Build transaction
        txn = self.contract.functions.registerValidator(
            subnet_id, core_stake, btc_stake, api_endpoint
        ).build_transaction(
            {
                "from": self.account.address,
                "gas": 500000,
                "gasPrice": gas_price or self.w3.eth.gas_price,
                "nonce": self._current_nonce,
            }
        )

        # Increment nonce for next transaction
        self._current_nonce += 1

        # Sign and send transaction
        signed_txn = self.account.sign_transaction(txn)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)

        logger.info(f"Validator registration transaction sent: {tx_hash.hex()}")
        return tx_hash.hex()

    def update_miner_scores(
        self,
        miner_scores: Union[Dict[str, float], str],
        new_performance: Optional[int] = None,
        new_trust_score: Optional[int] = None,
        gas_price: Optional[int] = None,
    ) -> str:
        """
        Cập nhật điểm số cho miner.

        Args:
            miner_scores: Dict mapping miner addresses to scores, OR single miner address (str)
            new_performance: Điểm hiệu suất mới (scaled by 1000000) - required if miner_scores is str
            new_trust_score: Điểm tin cậy mới (scaled by 1000000) - required if miner_scores is str
            gas_price: Gas price (optional)

        Returns:
            Transaction hash or error string
        """
        if not self.account:
            raise ValueError("Account required for transaction")

        # Handle both Dict and individual parameters
        if isinstance(miner_scores, dict):
            # Old style: dict of {miner_address: score}
            if len(miner_scores) != 1:
                raise ValueError("Currently only supports updating one miner at a time")

            miner_address = list(miner_scores.keys())[0]
            score = list(miner_scores.values())[0]

            # Convert normalized score (0.0-1.0) to scaled integers
            performance_scaled = int(score * 1000000)
            trust_scaled = int(score * 1000000)  # Use same score for both

        else:
            # New style: individual parameters
            if new_performance is None or new_trust_score is None:
                raise ValueError(
                    "new_performance and new_trust_score required when miner_scores is str"
                )

            miner_address = miner_scores
            performance_scaled = new_performance
            trust_scaled = new_trust_score

        miner_address = to_checksum_address(miner_address)

        # Get current gas price and add buffer for replacement
        current_gas_price = self.w3.eth.gas_price
        buffered_gas_price = int(current_gas_price * 1.2)  # 20% buffer
        final_gas_price = gas_price or buffered_gas_price

        # Get nonce - use 'pending' to include pending transactions
        nonce = self.w3.eth.get_transaction_count(self.account.address, "pending")

        # Build transaction
        txn = self.contract.functions.updateMinerScores(
            miner_address, performance_scaled, trust_scaled
        ).build_transaction(
            {
                "from": self.account.address,
                "gas": 200000,
                "gasPrice": final_gas_price,
                "nonce": nonce,
            }
        )

        # Test transaction before sending to detect failures early
        try:
            # Simulate the transaction call to check for reverts
            self.contract.functions.updateMinerScores(
                miner_address, performance_scaled, trust_scaled
            ).call({"from": self.account.address})
            logger.debug(
                f"✅ Transaction simulation successful for miner {miner_address}"
            )

        except Exception as sim_error:
            # Transaction would fail - log the reason and skip sending
            logger.warning(
                f"🚫 Transaction simulation failed for {miner_address}: {sim_error}"
            )

            # Check common failure reasons
            if (
                "miner not found" in str(sim_error).lower()
                or "not registered" in str(sim_error).lower()
            ):
                logger.warning(
                    f"⚠️ Miner {miner_address} not registered in contract - skipping score update"
                )
                return f"miner_not_registered_{nonce}_{miner_address[-8:]}"
            elif (
                "onlyvalidator" in str(sim_error).lower().replace(" ", "")
                or "unauthorized" in str(sim_error).lower()
                or "access" in str(sim_error).lower()
            ):
                logger.warning(
                    f"⚠️ Validator not authorized - validator not registered in contract"
                )
                return f"validator_not_registered_{nonce}_{miner_address[-8:]}"
            elif "execution reverted" in str(sim_error).lower():
                logger.warning(
                    f"⚠️ Contract execution reverted - likely registration issue"
                )
                # TEMPORARY: Skip simulation failures during development/testing
                logger.warning(
                    f"🔧 DEVELOPMENT MODE: Skipping transaction due to simulation failure"
                )
                return f"simulation_failed_{nonce}_{miner_address[-8:]}_{str(sim_error)[:50]}"
            else:
                logger.warning(
                    f"⚠️ Unknown simulation error for {miner_address}: {sim_error}"
                )

            # Return a simulation failure indicator instead of sending the transaction
            return (
                f"simulation_failed_{nonce}_{miner_address[-8:]}_{str(sim_error)[:50]}"
            )

        # Sign and send transaction with error handling
        signed_txn = self.account.sign_transaction(txn)

        try:
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            logger.info(f"Miner scores update transaction sent: {tx_hash.hex()}")
            return tx_hash.hex()

        except Exception as e:
            error_msg = str(e)

            # Handle "already known" error - transaction already in mempool
            if "already known" in error_msg:
                logger.warning(
                    f"Transaction already in mempool for {miner_address}, skipping duplicate"
                )
                # Return a dummy hash to indicate success (transaction will be processed)
                return f"duplicate_{nonce}_{miner_address[-8:]}"

            # Handle "replacement transaction underpriced"
            elif (
                "replacement transaction underpriced" in error_msg
                or "underpriced" in error_msg
            ):
                logger.warning(
                    f"Transaction underpriced for {miner_address}, retrying with higher gas price"
                )

                # Retry with much higher gas price
                retry_gas_price = int(current_gas_price * 1.5)  # 50% buffer
                txn_retry = self.contract.functions.updateMinerScores(
                    miner_address, new_performance, new_trust_score
                ).build_transaction(
                    {
                        "from": self.account.address,
                        "gas": 200000,
                        "gasPrice": retry_gas_price,
                        "nonce": nonce,
                    }
                )

                signed_txn_retry = self.account.sign_transaction(txn_retry)

                try:
                    tx_hash = self.w3.eth.send_raw_transaction(
                        signed_txn_retry.raw_transaction
                    )
                    logger.info(
                        f"Retry transaction sent with higher gas: {tx_hash.hex()}"
                    )
                    return tx_hash.hex()
                except Exception as retry_error:
                    logger.error(f"Retry failed for {miner_address}: {retry_error}")
                    raise retry_error
            else:
                # Re-raise other errors
                raise e

    def stake_bitcoin(
        self,
        tx_hash: bytes,
        amount: int,
        lock_time: int,
        gas_price: Optional[int] = None,
    ) -> str:
        """
        Stake Bitcoin for dual staking rewards.

        Args:
            tx_hash: Bitcoin transaction hash
            amount: Amount of Bitcoin staked (in satoshis)
            lock_time: Lock time for the Bitcoin
            gas_price: Gas price (optional)

        Returns:
            Transaction hash
        """
        if not self.account:
            raise ValueError("Account required for transaction")

        # Build transaction
        txn = self.contract.functions.stakeBitcoin(
            tx_hash, amount, lock_time
        ).build_transaction(
            {
                "from": self.account.address,
                "gas": 300000,
                "gasPrice": gas_price or self.w3.eth.gas_price,
                "nonce": self.w3.eth.get_transaction_count(self.account.address),
            }
        )

        # Sign and send transaction
        signed_txn = self.account.sign_transaction(txn)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)

        logger.info(f"Bitcoin staking transaction sent: {tx_hash.hex()}")
        return tx_hash.hex()

    def get_miner_info(self, miner_address: str) -> Dict[str, Any]:
        """
        Lấy thông tin chi tiết của miner.

        Args:
            miner_address: Địa chỉ của miner

        Returns:
            Thông tin miner
        """
        miner_address = to_checksum_address(miner_address)
        result = self.contract.functions.getMinerInfo(miner_address).call()

        return {
            "uid": result[0].hex(),
            "subnet_uid": result[1],
            "stake": result[2],
            "bitcoin_stake": result[3],
            "last_performance": result[4],
            "trust_score": result[5],
            "accumulated_rewards": result[6],
            "last_update_timestamp": result[7],
            "registration_timestamp": result[8],
            "status": result[9],
            "performance_history_hash": result[10].hex(),
            "api_endpoint": result[11],
            "owner": result[12],
        }

    def get_all_miners(self) -> List[str]:
        """
        Lấy danh sách tất cả miners.

        Returns:
            Danh sách địa chỉ miners
        """
        return self.contract.functions.getAllMiners().call()

    def get_all_validators(self, subnet_id: int = 1) -> List[str]:
        """
        Lấy danh sách tất cả validators trong subnet.

        Args:
            subnet_id: ID của subnet (default: 1)

        Returns:
            Danh sách địa chỉ validators
        """
        return self.contract.functions.getSubnetValidators(subnet_id).call()

    def calculate_staking_tier(self, user_address: str) -> int:
        """
        Tính toán tier staking cho user.

        Args:
            user_address: Địa chỉ của user

        Returns:
            Staking tier (0=Base, 1=Boost, 2=Super, 3=Satoshi)
        """
        user_address = to_checksum_address(user_address)
        return self.contract.functions.calculateStakingTier(user_address).call()

    def get_staking_tier_name(self, tier: int) -> str:
        """
        Lấy tên của staking tier.

        Args:
            tier: Tier number

        Returns:
            Tier name
        """
        tier_names = ["Base", "Boost", "Super", "Satoshi"]
        return tier_names[tier] if 0 <= tier < len(tier_names) else "Unknown"

    def get_miner_info(self, miner_address: str) -> Dict[str, Any]:
        """
        Lấy thông tin của miner.

        Args:
            miner_address: Địa chỉ của miner

        Returns:
            Thông tin miner
        """
        miner_address = to_checksum_address(miner_address)
        return self.contract.functions.getMinerInfo(miner_address).call()

    def get_validator_info(self, validator_address: str) -> Dict[str, Any]:
        """
        Lấy thông tin của validator.

        Args:
            validator_address: Địa chỉ của validator

        Returns:
            Thông tin validator
        """
        validator_address = to_checksum_address(validator_address)
        return self.contract.functions.getValidatorInfo(validator_address).call()

    def get_all_miners(self, subnet_id: int = 1) -> List[str]:
        """
        Lấy danh sách tất cả miners trong subnet.

        Args:
            subnet_id: ID của subnet (default: 1)

        Returns:
            Danh sách địa chỉ miners
        """
        return self.contract.functions.getSubnetMiners(subnet_id).call()

    def get_all_validators(self, subnet_id: int = 1) -> List[str]:
        """
        Lấy danh sách tất cả validators trong subnet.

        Args:
            subnet_id: ID của subnet (default: 1)

        Returns:
            Danh sách địa chỉ validators
        """
        return self.contract.functions.getSubnetValidators(subnet_id).call()

    def get_total_miners(self) -> int:
        """
        Lấy tổng số miners đã đăng ký.

        Returns:
            Số lượng miners
        """
        return len(self.get_all_miners())

    def get_total_validators(self) -> int:
        """
        Lấy tổng số validators đã đăng ký.

        Returns:
            Số lượng validators
        """
        return len(self.get_all_validators())

    def wait_for_transaction(self, tx_hash: str, timeout: int = 30) -> Dict[str, Any]:
        """
        Chờ transaction được confirm và check status.

        Args:
            tx_hash: Transaction hash
            timeout: Timeout in seconds

        Returns:
            Transaction receipt

        Raises:
            Exception: If transaction fails or times out
        """
        try:
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)
            receipt_dict = dict(receipt)

            # Check transaction status
            status = receipt_dict.get("status", 0)
            if status == 1:
                logger.info(f"✅ Transaction successful: {tx_hash}")
                return receipt_dict
            else:
                # Transaction failed - try to get revert reason
                error_msg = f"Transaction failed with status 0: {tx_hash}"

                try:
                    # Try to get revert reason by calling the failed transaction
                    tx_data = self.w3.eth.get_transaction(tx_hash)
                    try:
                        self.w3.eth.call(tx_data, receipt_dict["blockNumber"])
                    except Exception as call_error:
                        if "execution reverted" in str(call_error):
                            error_msg += f" - Reason: {call_error}"
                        else:
                            error_msg += f" - Call error: {call_error}"
                except Exception:
                    error_msg += " - Could not determine failure reason"

                logger.error(error_msg)
                raise Exception(error_msg)

        except Exception as e:
            if "timeout" in str(e).lower():
                logger.error(f"⏰ Transaction timeout: {tx_hash}")
            else:
                logger.error(f"❌ Transaction error: {tx_hash}, error: {e}")
            raise

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
            address=self.contract_address,
            abi=contract_abi
        )
        
        logger.info(f"✅ ModernTensor Core client initialized: {self.contract_address}")
    
    def _load_contract_abi(self) -> List[Dict]:
        """Load contract ABI from artifacts"""
        # Default ABI for ModernTensor contract
        # In production, this should be loaded from compiled artifacts
        return [
            {
                "inputs": [
                    {"name": "uid", "type": "bytes32"},
                    {"name": "subnetUid", "type": "uint64"},
                    {"name": "stakeAmount", "type": "uint256"},
                    {"name": "apiEndpoint", "type": "string"}
                ],
                "name": "registerMiner",
                "outputs": [],
                "stateMutability": "payable",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "uid", "type": "bytes32"},
                    {"name": "subnetUid", "type": "uint64"},
                    {"name": "stakeAmount", "type": "uint256"},
                    {"name": "apiEndpoint", "type": "string"}
                ],
                "name": "registerValidator",
                "outputs": [],
                "stateMutability": "payable",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "minerAddr", "type": "address"},
                    {"name": "newPerformance", "type": "uint256"},
                    {"name": "newTrustScore", "type": "uint256"}
                ],
                "name": "updateMinerScores",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "txHash", "type": "bytes32"},
                    {"name": "amount", "type": "uint256"},
                    {"name": "lockTime", "type": "uint256"}
                ],
                "name": "stakeBitcoin",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "minerAddr", "type": "address"}
                ],
                "name": "getMinerInfo",
                "outputs": [
                    {
                        "components": [
                            {"name": "uid", "type": "bytes32"},
                            {"name": "subnetUid", "type": "uint64"},
                            {"name": "stake", "type": "uint256"},
                            {"name": "bitcoinStake", "type": "uint256"},
                            {"name": "lastPerformance", "type": "uint256"},
                            {"name": "trustScore", "type": "uint256"},
                            {"name": "accumulatedRewards", "type": "uint256"},
                            {"name": "lastUpdateTimestamp", "type": "uint256"},
                            {"name": "registrationTimestamp", "type": "uint256"},
                            {"name": "status", "type": "uint8"},
                            {"name": "performanceHistoryHash", "type": "bytes32"},
                            {"name": "apiEndpoint", "type": "string"},
                            {"name": "owner", "type": "address"}
                        ],
                        "name": "",
                        "type": "tuple"
                    }
                ],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [],
                "name": "getAllMiners",
                "outputs": [{"name": "", "type": "address[]"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [],
                "name": "getAllValidators", 
                "outputs": [{"name": "", "type": "address[]"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "user", "type": "address"}
                ],
                "name": "calculateStakingTier",
                "outputs": [{"name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            }
        ]
    
    def register_miner(
        self,
        uid: bytes,
        subnet_uid: int,
        stake_amount: int,
        api_endpoint: str,
        gas_price: Optional[int] = None
    ) -> str:
        """
        Đăng ký một miner mới.
        
        Args:
            uid: UID duy nhất của miner
            subnet_uid: ID của subnet
            stake_amount: Số lượng CORE tokens stake
            api_endpoint: Endpoint API của miner
            gas_price: Gas price (optional)
            
        Returns:
            Transaction hash
        """
        if not self.account:
            raise ValueError("Account required for transaction")
        
        # Build transaction
        txn = self.contract.functions.registerMiner(
            uid,
            subnet_uid,
            stake_amount,
            api_endpoint
        ).build_transaction({
            'from': self.account.address,
            'gas': 500000,
            'gasPrice': gas_price or self.w3.eth.gas_price,
            'nonce': self.w3.eth.get_transaction_count(self.account.address),
        })
        
        # Sign and send transaction
        signed_txn = self.account.sign_transaction(txn)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        
        logger.info(f"Miner registration transaction sent: {tx_hash.hex()}")
        return tx_hash.hex()
    
    def register_validator(
        self,
        uid: bytes,
        subnet_uid: int,
        stake_amount: int,
        api_endpoint: str,
        gas_price: Optional[int] = None
    ) -> str:
        """
        Đăng ký một validator mới.
        
        Args:
            uid: UID duy nhất của validator
            subnet_uid: ID của subnet
            stake_amount: Số lượng CORE tokens stake
            api_endpoint: Endpoint API của validator
            gas_price: Gas price (optional)
            
        Returns:
            Transaction hash
        """
        if not self.account:
            raise ValueError("Account required for transaction")
        
        # Build transaction
        txn = self.contract.functions.registerValidator(
            uid,
            subnet_uid,
            stake_amount,
            api_endpoint
        ).build_transaction({
            'from': self.account.address,
            'gas': 500000,
            'gasPrice': gas_price or self.w3.eth.gas_price,
            'nonce': self.w3.eth.get_transaction_count(self.account.address),
        })
        
        # Sign and send transaction
        signed_txn = self.account.sign_transaction(txn)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        
        logger.info(f"Validator registration transaction sent: {tx_hash.hex()}")
        return tx_hash.hex()
    
    def update_miner_scores(
        self,
        miner_address: str,
        new_performance: int,
        new_trust_score: int,
        gas_price: Optional[int] = None
    ) -> str:
        """
        Cập nhật điểm số cho miner.
        
        Args:
            miner_address: Địa chỉ của miner
            new_performance: Điểm hiệu suất mới (scaled by 1000000)
            new_trust_score: Điểm tin cậy mới (scaled by 1000000)
            gas_price: Gas price (optional)
            
        Returns:
            Transaction hash
        """
        if not self.account:
            raise ValueError("Account required for transaction")
        
        miner_address = to_checksum_address(miner_address)
        
        # Build transaction
        txn = self.contract.functions.updateMinerScores(
            miner_address,
            new_performance,
            new_trust_score
        ).build_transaction({
            'from': self.account.address,
            'gas': 200000,
            'gasPrice': gas_price or self.w3.eth.gas_price,
            'nonce': self.w3.eth.get_transaction_count(self.account.address),
        })
        
        # Sign and send transaction
        signed_txn = self.account.sign_transaction(txn)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        
        logger.info(f"Miner scores update transaction sent: {tx_hash.hex()}")
        return tx_hash.hex()
    
    def stake_bitcoin(
        self,
        tx_hash: bytes,
        amount: int,
        lock_time: int,
        gas_price: Optional[int] = None
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
            tx_hash,
            amount,
            lock_time
        ).build_transaction({
            'from': self.account.address,
            'gas': 300000,
            'gasPrice': gas_price or self.w3.eth.gas_price,
            'nonce': self.w3.eth.get_transaction_count(self.account.address),
        })
        
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
            'uid': result[0].hex(),
            'subnet_uid': result[1],
            'stake': result[2],
            'bitcoin_stake': result[3],
            'last_performance': result[4],
            'trust_score': result[5],
            'accumulated_rewards': result[6],
            'last_update_timestamp': result[7],
            'registration_timestamp': result[8],
            'status': result[9],
            'performance_history_hash': result[10].hex(),
            'api_endpoint': result[11],
            'owner': result[12]
        }
    
    def get_all_miners(self) -> List[str]:
        """
        Lấy danh sách tất cả miners.
        
        Returns:
            Danh sách địa chỉ miners
        """
        return self.contract.functions.getAllMiners().call()
    
    def get_all_validators(self) -> List[str]:
        """
        Lấy danh sách tất cả validators.
        
        Returns:
            Danh sách địa chỉ validators
        """
        return self.contract.functions.getAllValidators().call()
    
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
    
    def wait_for_transaction(self, tx_hash: str, timeout: int = 120) -> Dict[str, Any]:
        """
        Chờ transaction được confirm.
        
        Args:
            tx_hash: Transaction hash
            timeout: Timeout in seconds
            
        Returns:
            Transaction receipt
        """
        try:
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)
            logger.info(f"Transaction confirmed: {tx_hash}")
            return dict(receipt)
        except Exception as e:
            logger.error(f"Transaction failed or timeout: {tx_hash}, error: {e}")
            raise

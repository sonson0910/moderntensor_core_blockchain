"""
Mock Web3 client for Core blockchain testing
Provides mock functionality to avoid hitting real blockchain during tests
"""

import asyncio
from typing import Dict, List, Optional, Any, Union
from web3 import Web3
from eth_account import Account
from datetime import datetime, timedelta
import json


class MockWeb3Client:
    """Mock Web3 client for testing Core blockchain interactions"""
    
    def __init__(self):
        self.accounts: Dict[str, Dict[str, Any]] = {}
        self.contracts: Dict[str, Dict[str, Any]] = {}
        self.transactions: List[Dict[str, Any]] = []
        self.blocks: List[Dict[str, Any]] = []
        self.current_block_number = 1000000
        self.chain_id = 1115  # Core testnet
        self.gas_price = Web3.to_wei(20, 'gwei')
        
        # Bitcoin staking data
        self.bitcoin_stakes: Dict[str, Dict[str, Any]] = {}
        
        # Staking tiers configuration
        self.staking_tiers = {
            'base': {'multiplier': 1.0, 'min_btc': 0},
            'boost': {'multiplier': 1.25, 'min_btc': 0.01},
            'super': {'multiplier': 1.5, 'min_btc': 0.1},
            'satoshi': {'multiplier': 2.0, 'min_btc': 1.0}
        }
        
        # Initialize with some default data
        self._initialize_default_data()
    
    def _initialize_default_data(self):
        """Initialize mock client with default data"""
        # Add some default blocks
        for i in range(5):
            self.blocks.append({
                'number': self.current_block_number - i,
                'hash': f'0x{i:064x}',
                'timestamp': int(datetime.now().timestamp()) - (i * 3),
                'transactions': [],
                'gas_used': 21000 * (i + 1),
                'gas_limit': 30000000
            })
    
    def set_balance(self, address: str, balance: int):
        """Set ETH balance for an address"""
        if address not in self.accounts:
            self.accounts[address] = {}
        self.accounts[address]['eth_balance'] = balance
    
    def set_token_balance(self, address: str, balance: int):
        """Set CORE token balance for an address"""
        if address not in self.accounts:
            self.accounts[address] = {}
        self.accounts[address]['core_balance'] = balance
    
    def set_bitcoin_balance(self, address: str, balance: float):
        """Set Bitcoin balance for an address"""
        if address not in self.accounts:
            self.accounts[address] = {}
        self.accounts[address]['bitcoin_balance'] = balance
    
    def get_balance(self, address: str) -> int:
        """Get ETH balance for address"""
        return self.accounts.get(address, {}).get('eth_balance', 0)
    
    def get_token_balance(self, address: str, token_address: str) -> int:
        """Get token balance for address"""
        return self.accounts.get(address, {}).get('core_balance', 0)
    
    def get_bitcoin_balance(self, address: str) -> float:
        """Get Bitcoin balance for address"""
        return self.accounts.get(address, {}).get('bitcoin_balance', 0.0)
    
    def get_block_number(self) -> int:
        """Get current block number"""
        return self.current_block_number
    
    def get_block(self, block_number: Union[int, str]) -> Dict[str, Any]:
        """Get block by number"""
        if isinstance(block_number, str) and block_number == 'latest':
            block_number = self.current_block_number
        
        # Find block by number
        for block in self.blocks:
            if block['number'] == block_number:
                return block
        
        # Return mock block if not found
        return {
            'number': block_number,
            'hash': f'0x{block_number:064x}',
            'timestamp': int(datetime.now().timestamp()),
            'transactions': [],
            'gas_used': 21000,
            'gas_limit': 30000000
        }
    
    def get_transaction_count(self, address: str) -> int:
        """Get transaction count (nonce) for address"""
        # Count transactions from this address
        count = 0
        for tx in self.transactions:
            if tx.get('from') == address:
                count += 1
        return count
    
    def estimate_gas(self, transaction: Dict[str, Any]) -> int:
        """Estimate gas for transaction"""
        # Simple gas estimation based on transaction type
        if 'data' in transaction and transaction['data'] != '0x':
            # Contract call
            return 200000
        else:
            # Simple transfer
            return 21000
    
    def send_transaction(self, transaction: Dict[str, Any]) -> str:
        """Send a transaction and return transaction hash"""
        # Generate mock transaction hash
        tx_hash = f"0x{''.join(['%02x' % (i % 256) for i in range(32)])}"
        
        # Add to transactions list
        mock_tx = {
            'hash': tx_hash,
            'from': transaction.get('from', '0x0'),
            'to': transaction.get('to', '0x0'),
            'value': transaction.get('value', 0),
            'gas': transaction.get('gas', 21000),
            'gas_price': transaction.get('gasPrice', self.gas_price),
            'data': transaction.get('data', '0x'),
            'nonce': self.get_transaction_count(transaction.get('from', '0x0')),
            'block_number': self.current_block_number,
            'timestamp': int(datetime.now().timestamp()),
            'status': 1  # Success
        }
        
        self.transactions.append(mock_tx)
        return tx_hash
    
    def get_transaction_receipt(self, tx_hash: str) -> Dict[str, Any]:
        """Get transaction receipt"""
        # Find transaction by hash
        for tx in self.transactions:
            if tx['hash'] == tx_hash:
                return {
                    'transactionHash': tx_hash,
                    'blockNumber': tx['block_number'],
                    'gasUsed': tx['gas'],
                    'status': tx['status'],
                    'logs': [],
                    'contractAddress': None
                }
        
        # Return mock receipt if not found
        return {
            'transactionHash': tx_hash,
            'blockNumber': self.current_block_number,
            'gasUsed': 21000,
            'status': 1,
            'logs': [],
            'contractAddress': None
        }
    
    def call_contract_function(self, contract_address: str, function_name: str, 
                              *args, **kwargs) -> Any:
        """Call a contract function"""
        # Mock contract function calls
        if function_name == 'get_subnet_info':
            subnet_uid = args[0] if args else 1
            return {
                'total_stake': Web3.to_wei(50000, 'ether'),
                'validator_count': 4,
                'miner_count': 16,
                'difficulty': 5000,
                'last_update': int(datetime.now().timestamp())
            }
        
        elif function_name == 'get_miner_info':
            miner_uid = args[0] if args else b'\x00' * 16
            return {
                'uid': miner_uid,
                'address': '0x742d35Cc6634C0532925a3b8d2D25F95b32A6B3C',
                'stake': Web3.to_wei(1000, 'ether'),
                'staking_tier': 'boost',
                'bitcoin_staked': 0.1,
                'api_endpoint': 'http://localhost:8080',
                'active': True
            }
        
        elif function_name == 'get_validator_info':
            validator_uid = args[0] if args else b'\x00' * 16
            return {
                'uid': validator_uid,
                'address': '0x8ba1f109551bD432803012645Hac136c13e87058',
                'stake': Web3.to_wei(10000, 'ether'),
                'staking_tier': 'super',
                'bitcoin_staked': 0.5,
                'active': True
            }
        
        elif function_name == 'get_staking_info':
            address = args[0] if args else '0x0'
            return self.accounts.get(address, {}).get('staking_info', {
                'core_staked': 0,
                'bitcoin_staked': 0,
                'staking_tier': 'base',
                'lock_time': 0,
                'dual_staking': False
            })
        
        elif function_name == 'calculate_rewards':
            address = args[0] if args else '0x0'
            staking_info = self.accounts.get(address, {}).get('staking_info', {})
            tier = staking_info.get('staking_tier', 'base')
            multiplier = self.staking_tiers[tier]['multiplier']
            
            base_rewards = 100  # Base rewards per period
            return {
                'core_rewards': base_rewards * multiplier,
                'bitcoin_rewards': 0.001 * multiplier if tier != 'base' else 0,
                'total_value_usd': (base_rewards * multiplier * 10)  # Assume $10 per CORE
            }
        
        # Default return for unknown functions
        return None
    
    async def register_miner(self, uid: bytes, subnet_uid: int, stake_amount: int,
                           api_endpoint: str, staking_tier: str, 
                           account_address: str) -> str:
        """Mock miner registration"""
        # Validate staking tier
        if staking_tier not in self.staking_tiers:
            raise ValueError(f"Invalid staking tier: {staking_tier}")
        
        # Create mock transaction
        tx_hash = self.send_transaction({
            'from': account_address,
            'to': '0x1234567890123456789012345678901234567890',  # Contract address
            'data': f'0xregister_miner{uid.hex()}{subnet_uid:08x}{stake_amount:016x}',
            'gas': 200000
        })
        
        # Store miner info
        miner_key = f"{account_address}_{uid.hex()}"
        if account_address not in self.accounts:
            self.accounts[account_address] = {}
        
        self.accounts[account_address]['miner_info'] = {
            'uid': uid,
            'subnet_uid': subnet_uid,
            'stake_amount': stake_amount,
            'api_endpoint': api_endpoint,
            'staking_tier': staking_tier,
            'registration_tx': tx_hash
        }
        
        return tx_hash
    
    async def register_validator(self, uid: bytes, subnet_uid: int, 
                               stake_amount: int, staking_tier: str,
                               account_address: str) -> str:
        """Mock validator registration"""
        # Create mock transaction
        tx_hash = self.send_transaction({
            'from': account_address,
            'to': '0x1234567890123456789012345678901234567890',
            'data': f'0xregister_validator{uid.hex()}{subnet_uid:08x}{stake_amount:016x}',
            'gas': 200000
        })
        
        # Store validator info
        if account_address not in self.accounts:
            self.accounts[account_address] = {}
        
        self.accounts[account_address]['validator_info'] = {
            'uid': uid,
            'subnet_uid': subnet_uid,
            'stake_amount': stake_amount,
            'staking_tier': staking_tier,
            'registration_tx': tx_hash
        }
        
        return tx_hash
    
    async def enable_dual_staking(self, core_amount: int, btc_amount: float,
                                staking_tier: str, account_address: str) -> str:
        """Mock dual staking enablement"""
        # Validate requirements
        min_btc = self.staking_tiers[staking_tier]['min_btc']
        if btc_amount < min_btc:
            raise ValueError(f"Insufficient Bitcoin for {staking_tier} tier. Required: {min_btc}, provided: {btc_amount}")
        
        # Create mock transaction
        tx_hash = self.send_transaction({
            'from': account_address,
            'to': '0x9876543210987654321098765432109876543210',  # Bitcoin staking contract
            'data': f'0xenable_dual_staking{core_amount:016x}',
            'gas': 300000
        })
        
        # Store staking info
        if account_address not in self.accounts:
            self.accounts[account_address] = {}
        
        self.accounts[account_address]['staking_info'] = {
            'core_staked': core_amount,
            'bitcoin_staked': btc_amount,
            'staking_tier': staking_tier,
            'dual_staking': True,
            'lock_time': int((datetime.now() + timedelta(days=30)).timestamp()),
            'enable_tx': tx_hash
        }
        
        return tx_hash
    
    async def claim_rewards(self, account_address: str) -> str:
        """Mock reward claiming"""
        # Create mock transaction
        tx_hash = self.send_transaction({
            'from': account_address,
            'to': '0x1234567890123456789012345678901234567890',
            'data': '0xclaim_rewards',
            'gas': 150000
        })
        
        return tx_hash
    
    def get_network_stats(self) -> Dict[str, Any]:
        """Get mock network statistics"""
        return {
            'total_validators': 64,
            'total_miners': 256,
            'total_core_staked': Web3.to_wei(1000000, 'ether'),
            'total_bitcoin_staked': 100.0,
            'network_difficulty': 10000,
            'average_tps': 4500,
            'current_gas_price': self.gas_price,
            'total_subnets': 5
        }
    
    def simulate_network_conditions(self, conditions: Dict[str, Any]):
        """Simulate different network conditions for testing"""
        if 'high_gas' in conditions:
            self.gas_price = Web3.to_wei(100, 'gwei')
        elif 'low_gas' in conditions:
            self.gas_price = Web3.to_wei(1, 'gwei')
        
        if 'network_congestion' in conditions:
            # Simulate slower response times
            import time
            time.sleep(0.1)
    
    def reset(self):
        """Reset mock client to initial state"""
        self.accounts.clear()
        self.contracts.clear()
        self.transactions.clear()
        self.blocks.clear()
        self.bitcoin_stakes.clear()
        self.current_block_number = 1000000
        self.gas_price = Web3.to_wei(20, 'gwei')
        self._initialize_default_data() 
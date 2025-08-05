#!/usr/bin/env python3
"""
Core Blockchain Metagraph Adapter
Replaces Aptos functionality with Core blockchain calls
"""

import os
import json
from typing import List, Dict, Any, Optional
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from dotenv import load_dotenv

load_dotenv()


class CoreMetagraphClient:
    """Client for fetching metagraph data from Core blockchain"""

    def __init__(self):
        self.rpc_url = "https://rpc.test2.btcs.network"
        self.web3 = Web3(Web3.HTTPProvider(self.rpc_url))
        self.web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

        self.contract_address = os.getenv("CORE_CONTRACT_ADDRESS")

        # Load contract ABI
        abi_path = os.path.join(
            os.path.dirname(__file__),
            "../smartcontract/artifacts/contracts/ModernTensor.sol/ModernTensor.json",
        )

        with open(abi_path, "r") as f:
            contract_data = json.load(f)
            self.contract_abi = contract_data["abi"]

        self.contract = self.web3.eth.contract(
            address=self.contract_address, abi=self.contract_abi
        )

    def get_all_miners(self) -> List[str]:
        """Get all registered miner addresses"""
        try:
            # Try subnet 1 first (where miners are registered)
            miners = self.contract.functions.getSubnetMiners(1).call()
            if miners:
                return miners

            # Fallback to subnet 0
            return self.contract.functions.getSubnetMiners(0).call()
        except Exception as e:
            print(f"Error fetching miners: {e}")
            return []

    def get_all_validators(self) -> List[str]:
        """Get all registered validator addresses"""
        try:
            # Try subnet 1 first (where validators are registered)
            validators = self.contract.functions.getSubnetValidators(1).call()
            if validators:
                return validators

            # Fallback to subnet 0
            return self.contract.functions.getSubnetValidators(0).call()
        except Exception as e:
            print(f"Error fetching validators: {e}")
            return []

    def get_miner_info(self, address: str) -> Optional[Dict[str, Any]]:
        """Get detailed miner information"""
        try:
            miner_info = self.contract.functions.getMinerInfo(address).call()
            # Enhanced MinerData struct: uid, subnet_uid, stake, bitcoin_stake, scaled_last_performance,
            # scaled_trust_score, accumulated_rewards, last_update_time,
            # performance_history_hash, wallet_addr_hash, status, registration_time, api_endpoint, owner
            return {
                "address": address,
                "uid": miner_info[0].hex(),
                "subnet_uid": int(miner_info[1]),
                "stake": float(self.web3.from_wei(miner_info[2], "ether")),
                "bitcoin_stake": (
                    int(miner_info[3]) if len(miner_info) > 12 else 0
                ),  # NEW: Bitcoin stake in satoshis
                "scaled_last_performance": (
                    int(miner_info[4]) if len(miner_info) > 12 else int(miner_info[3])
                ),
                "scaled_trust_score": (
                    int(miner_info[5]) if len(miner_info) > 12 else int(miner_info[4])
                ),
                "accumulated_rewards": float(
                    self.web3.from_wei(
                        miner_info[6] if len(miner_info) > 12 else miner_info[5],
                        "ether",
                    )
                ),
                "last_update_time": (
                    int(miner_info[7]) if len(miner_info) > 12 else int(miner_info[6])
                ),
                "performance_history_hash": (
                    miner_info[8] if len(miner_info) > 12 else miner_info[7]
                ).hex(),
                "wallet_addr_hash": (
                    miner_info[9] if len(miner_info) > 12 else miner_info[8]
                ).hex(),
                "status": (
                    int(miner_info[10]) if len(miner_info) > 12 else int(miner_info[9])
                ),
                "registration_time": (
                    int(miner_info[11]) if len(miner_info) > 12 else int(miner_info[10])
                ),
                "api_endpoint": (
                    miner_info[12] if len(miner_info) > 12 else miner_info[11]
                ),
                "owner": (
                    miner_info[13] if len(miner_info) > 13 else address
                ),  # NEW: Owner address
                "active": bool(
                    miner_info[10] if len(miner_info) > 12 else miner_info[9]
                ),  # status: 0=Inactive, 1=Active, 2=Jailed
            }
        except Exception as e:
            print(f"Error fetching miner {address}: {e}")
            return None

    def get_validator_info(self, address: str) -> Optional[Dict[str, Any]]:
        """Get detailed validator information"""
        try:
            validator_info = self.contract.functions.getValidatorInfo(address).call()
            # ValidatorData struct: uid, subnet_uid, stake, scaled_last_performance,
            # scaled_trust_score, accumulated_rewards, last_update_time,
            # performance_history_hash, wallet_addr_hash, status, registration_time, api_endpoint
            return {
                "address": address,
                "uid": validator_info[0].hex(),
                "subnet_uid": int(validator_info[1]),
                "stake": float(self.web3.from_wei(validator_info[2], "ether")),
                "scaled_last_performance": int(validator_info[3]),
                "scaled_trust_score": int(validator_info[4]),
                "accumulated_rewards": float(
                    self.web3.from_wei(validator_info[5], "ether")
                ),
                "last_update_time": int(validator_info[6]),
                "performance_history_hash": validator_info[7].hex(),
                "wallet_addr_hash": validator_info[8].hex(),
                "status": int(validator_info[9]),
                "registration_time": int(validator_info[10]),
                "api_endpoint": validator_info[11],
                "active": bool(
                    validator_info[9]
                ),  # status: 0=Inactive, 1=Active, 2=Jailed
            }
        except Exception as e:
            print(f"Error fetching validator {address}: {e}")
            return None

    def get_network_stats(self) -> Dict[str, Any]:
        """Get network statistics"""
        miners = self.get_all_miners()
        validators = self.get_all_validators()

        return {
            "total_miners": len(miners),
            "total_validators": len(validators),
            "active_miners": sum(
                1
                for addr in miners
                if self.get_miner_info(addr) and self.get_miner_info(addr)["active"]
            ),
            "active_validators": sum(
                1
                for addr in validators
                if self.get_validator_info(addr)
                and self.get_validator_info(addr)["active"]
            ),
            "contract_address": self.contract_address,
            "network": "Core Testnet",
        }


# Compatibility functions for existing metagraph system
def get_all_miner_data() -> List[Dict[str, Any]]:
    """Get all miner data - Core blockchain version"""
    client = CoreMetagraphClient()
    miners = client.get_all_miners()

    miner_data = []
    for miner_addr in miners:
        info = client.get_miner_info(miner_addr)
        if info:
            miner_data.append(info)

    return miner_data


def get_all_validator_data() -> List[Dict[str, Any]]:
    """Get all validator data - Core blockchain version"""
    client = CoreMetagraphClient()
    validators = client.get_all_validators()

    validator_data = []
    for validator_addr in validators:
        info = client.get_validator_info(validator_addr)
        if info:
            validator_data.append(info)

    return validator_data


def get_network_stats() -> Dict[str, Any]:
    """Get network statistics - Core blockchain version"""
    client = CoreMetagraphClient()
    return client.get_network_stats()


def is_miner_registered(address: str) -> bool:
    """Check if miner is registered"""
    client = CoreMetagraphClient()
    miners = client.get_all_miners()
    return address.lower() in [m.lower() for m in miners]


def is_validator_registered(address: str) -> bool:
    """Check if validator is registered"""
    client = CoreMetagraphClient()
    validators = client.get_all_validators()
    return address.lower() in [v.lower() for v in validators]


def load_metagraph_data() -> Dict[str, Any]:
    """Load complete metagraph data"""
    return {
        "miners": get_all_miner_data(),
        "validators": get_all_validator_data(),
        "network_stats": get_network_stats(),
    }

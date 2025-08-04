#!/usr/bin/env python3
"""
Consensus Blockchain Module
Blockchain operations and data persistence for consensus
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from web3 import Web3
from eth_account import Account

from ..config.config_loader import get_config
from ..core.datatypes import ValidatorInfo, MinerInfo
from ..metagraph.metagraph_datum import (
    ValidatorData,
    MinerData,
    STATUS_ACTIVE,
    STATUS_JAILED,
    STATUS_INACTIVE,
)
from .consensus_errors import BlockchainError, ConsensusErrorHandler

config = get_config()
logger = logging.getLogger(__name__)


async def find_resource_by_uid(
    client: Web3,
    contract_address: str,
    account_address: str,
    resource_type: str,
    uid_bytes: bytes,
) -> Optional[Dict[str, Any]]:
    """
    Find resource data on Core blockchain by UID.

    Args:
        client (Web3): Web3 client for Core blockchain.
        contract_address (str): ModernTensor contract address.
        account_address (str): Account address containing the resource.
        resource_type (str): Type of resource to find.
        uid_bytes (bytes): UID in bytes format for searching.

    Returns:
        Optional[Dict[str, Any]]: Resource data found, or None if not found.
    """
    logger.debug(
        f"Searching for resource {resource_type} with UID {uid_bytes.hex()} "
        f"for account {account_address}..."
    )

    try:
        with ConsensusErrorHandler("find_resource_by_uid"):
            # This is a simplified version - in real implementation,
            # you would query the Core blockchain smart contract
            from ..core_client.contract_client import ModernTensorCoreClient

            contract_client = ModernTensorCoreClient(
                w3=client,
                contract_address=contract_address,
                account=None,  # Read-only operation
            )

            # Query resource by UID
            if "miner" in resource_type.lower():
                miners = await contract_client.get_all_miners()
                uid_hex = uid_bytes.hex()
                if uid_hex in miners:
                    return miners[uid_hex].__dict__
            elif "validator" in resource_type.lower():
                validators = await contract_client.get_all_validators()
                uid_hex = uid_bytes.hex()
                if uid_hex in validators:
                    return validators[uid_hex].__dict__

            logger.warning(
                f"Resource {resource_type} with UID {uid_bytes.hex()} "
                f"not found for account {account_address}."
            )
            return None

    except Exception as e:
        logger.error(
            f"Failed to fetch resources for {account_address} while searching for "
            f"{resource_type} with UID {uid_bytes.hex()}: {e}"
        )
        raise BlockchainError(f"Resource lookup failed: {e}")


async def prepare_miner_updates_logic(
    final_scores: Dict[str, float],
    settings: Any,
    client: Web3,
    contract_address: str,
) -> Dict[str, MinerData]:
    """
    Prepare miner updates based on consensus scores for blockchain submission.

    Args:
        final_scores (Dict[str, float]): Final consensus scores (P_adj) for miners.
        settings (Any): Configuration settings.
        client (Web3): Web3 client for Core blockchain.
        contract_address (str): ModernTensor contract address.

    Returns:
        Dict[str, MinerData]: Dictionary of miner updates to be committed.
    """
    logger.info(f"📝 Preparing miner updates for {len(final_scores)} miners...")

    try:
        with ConsensusErrorHandler("prepare_miner_updates_logic"):
            from ..core_client.contract_client import ModernTensorCoreClient

            contract_client = ModernTensorCoreClient(
                w3=client,
                contract_address=contract_address,
                account=None,  # Read-only for preparation
            )

            # Get current miner data from blockchain
            current_miners = await contract_client.get_all_miners()
            miner_updates = {}

            for miner_uid_hex, p_adj in final_scores.items():
                if miner_uid_hex in current_miners:
                    current_miner = current_miners[miner_uid_hex]

                    # Create updated miner data
                    updated_miner = MinerData(
                        uid=miner_uid_hex,
                        stake=current_miner.stake,
                        bitcoin_stake=getattr(current_miner, "bitcoin_stake", 0),
                        last_performance=p_adj,
                        accumulated_rewards=current_miner.accumulated_rewards,
                        status=current_miner.status,
                        registration_block=current_miner.registration_block,
                        last_update_block=0,  # Will be set during commit
                        metadata=current_miner.metadata or {},
                    )

                    miner_updates[miner_uid_hex] = updated_miner
                    logger.debug(
                        f"  📊 Prepared update for Miner {miner_uid_hex}: "
                        f"performance={p_adj:.4f}"
                    )

            logger.info(f"✅ Prepared {len(miner_updates)} miner updates")
            return miner_updates

    except Exception as e:
        logger.error(f"Error preparing miner updates: {e}")
        raise BlockchainError(f"Failed to prepare miner updates: {e}")


async def prepare_validator_updates_logic(
    calculated_states: Dict[str, Any],
    settings: Any,
    client: Optional[Web3],
    contract_address: str = None,
) -> Dict[str, ValidatorData]:
    """
    Prepare validator updates based on calculated states for blockchain submission.

    Args:
        calculated_states (Dict[str, Any]): Calculated states from consensus.
        settings (Any): Configuration settings.
        client (Optional[Web3]): Web3 client for Core blockchain.
        contract_address (str): ModernTensor contract address.

    Returns:
        Dict[str, ValidatorData]: Dictionary of validator updates to be committed.
    """
    logger.info(
        f"📝 Preparing validator updates for {len(calculated_states)} validators..."
    )

    try:
        with ConsensusErrorHandler("prepare_validator_updates_logic"):
            if not client or not contract_address:
                raise ValueError(
                    "Client and contract address required for validator updates"
                )

            from ..core_client.contract_client import ModernTensorCoreClient

            contract_client = ModernTensorCoreClient(
                w3=client,
                contract_address=contract_address,
                account=None,  # Read-only for preparation
            )

            # Get current validator data from blockchain
            current_validators = await contract_client.get_all_validators()
            validator_updates = {}

            for validator_uid_hex, state in calculated_states.items():
                if validator_uid_hex in current_validators:
                    current_validator = current_validators[validator_uid_hex]

                    # Determine new status
                    new_trust = state.get("trust", current_validator.trust_score)
                    jailed_threshold = getattr(
                        config.consensus, "jailed_severity_threshold", 0.2
                    )

                    if new_trust <= jailed_threshold:
                        new_status = STATUS_JAILED
                    elif new_trust > 0.5:  # Recovery threshold
                        new_status = STATUS_ACTIVE
                    else:
                        new_status = current_validator.status  # Keep current status

                    # Create updated validator data
                    updated_validator = ValidatorData(
                        uid=validator_uid_hex,
                        stake=current_validator.stake,
                        bitcoin_stake=getattr(current_validator, "bitcoin_stake", 0),
                        trust_score=new_trust,
                        last_performance=state.get("E_v", 0.0),
                        accumulated_rewards=current_validator.accumulated_rewards
                        + state.get("reward", 0.0),
                        status=new_status,
                        registration_block=current_validator.registration_block,
                        last_update_block=0,  # Will be set during commit
                        last_update_cycle=state.get("last_update_cycle", 0),
                        metadata=current_validator.metadata or {},
                    )

                    validator_updates[validator_uid_hex] = updated_validator
                    logger.debug(
                        f"  📊 Prepared update for Validator {validator_uid_hex}: "
                        f"trust={new_trust:.4f}, performance={state.get('E_v', 0.0):.4f}, "
                        f"status={new_status}"
                    )

            logger.info(f"✅ Prepared {len(validator_updates)} validator updates")
            return validator_updates

    except Exception as e:
        logger.error(f"Error preparing validator updates: {e}")
        raise BlockchainError(f"Failed to prepare validator updates: {e}")


async def commit_updates_logic(
    validator_updates: Dict[str, ValidatorData],
    client: Web3,
    account: Account,
    settings: Any,
    contract_address: str,
    miner_updates: Optional[Dict[str, MinerData]] = None,
) -> Dict[str, Any]:
    """
    Commit updates to the Core blockchain.

    Args:
        validator_updates (Dict[str, ValidatorData]): Dictionary of validator updates to commit.
        client (Web3): Web3 client for Core blockchain.
        account (Account): Account for signing transactions.
        settings (Any): Full settings object.
        contract_address (str): ModernTensor contract address.
        miner_updates (Optional[Dict[str, MinerData]]): Optional miner updates.

    Returns:
        Dict[str, Any]: Results of the commit operation including transaction hashes.
    """
    logger.info(
        f"🚀 Committing updates: {len(validator_updates)} validators, "
        f"{len(miner_updates) if miner_updates else 0} miners"
    )

    try:
        with ConsensusErrorHandler("commit_updates_logic"):
            from ..core_client.contract_client import ModernTensorCoreClient

            contract_client = ModernTensorCoreClient(
                w3=client, contract_address=contract_address, account=account
            )

            commit_results = {
                "validator_txs": [],
                "miner_txs": [],
                "success_count": 0,
                "error_count": 0,
                "errors": [],
            }

            # Commit validator updates
            for validator_uid, validator_data in validator_updates.items():
                try:
                    tx_hash = await contract_client.update_validator(
                        validator_uid=validator_uid,
                        trust_score=validator_data.trust_score,
                        performance_score=validator_data.last_performance,
                        accumulated_rewards=validator_data.accumulated_rewards,
                        status=validator_data.status,
                    )

                    commit_results["validator_txs"].append(
                        {
                            "validator_uid": validator_uid,
                            "tx_hash": tx_hash,
                            "status": "success",
                        }
                    )
                    commit_results["success_count"] += 1

                    logger.debug(f"  ✅ Committed validator {validator_uid}: {tx_hash}")

                except Exception as e:
                    error_msg = f"Failed to commit validator {validator_uid}: {e}"
                    logger.error(error_msg)
                    commit_results["errors"].append(error_msg)
                    commit_results["error_count"] += 1

            # Commit miner updates if provided
            if miner_updates:
                for miner_uid, miner_data in miner_updates.items():
                    try:
                        tx_hash = await contract_client.update_miner(
                            miner_uid=miner_uid,
                            performance_score=miner_data.last_performance,
                            accumulated_rewards=miner_data.accumulated_rewards,
                            status=miner_data.status,
                        )

                        commit_results["miner_txs"].append(
                            {
                                "miner_uid": miner_uid,
                                "tx_hash": tx_hash,
                                "status": "success",
                            }
                        )
                        commit_results["success_count"] += 1

                        logger.debug(f"  ✅ Committed miner {miner_uid}: {tx_hash}")

                    except Exception as e:
                        error_msg = f"Failed to commit miner {miner_uid}: {e}"
                        logger.error(error_msg)
                        commit_results["errors"].append(error_msg)
                        commit_results["error_count"] += 1

            success_rate = (
                commit_results["success_count"]
                / (commit_results["success_count"] + commit_results["error_count"])
                if (commit_results["success_count"] + commit_results["error_count"]) > 0
                else 0
            )

            logger.info(
                f"🎯 Commit completed: {commit_results['success_count']} success, "
                f"{commit_results['error_count']} errors (Success rate: {success_rate:.1%})"
            )

            return commit_results

    except Exception as e:
        logger.error(f"Critical error in commit_updates_logic: {e}")
        raise BlockchainError(f"Failed to commit updates to blockchain: {e}")


async def verify_blockchain_state(
    client: Web3, contract_address: str, expected_updates: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Verify that blockchain state matches expected updates.

    Args:
        client: Web3 client
        contract_address: Contract address
        expected_updates: Expected state updates

    Returns:
        Verification results
    """
    try:
        with ConsensusErrorHandler("verify_blockchain_state"):
            from ..core_client.contract_client import ModernTensorCoreClient

            contract_client = ModernTensorCoreClient(
                w3=client, contract_address=contract_address, account=None
            )

            verification_results = {
                "validators_verified": 0,
                "miners_verified": 0,
                "mismatches": [],
                "total_checked": 0,
            }

            # Verify validator states
            current_validators = await contract_client.get_all_validators()
            for uid, expected_data in expected_updates.get("validators", {}).items():
                verification_results["total_checked"] += 1

                if uid in current_validators:
                    actual_validator = current_validators[uid]

                    # Check trust score
                    expected_trust = expected_data.get("trust_score", 0.0)
                    actual_trust = actual_validator.trust_score

                    if abs(actual_trust - expected_trust) > 0.001:  # Tolerance
                        verification_results["mismatches"].append(
                            {
                                "type": "validator",
                                "uid": uid,
                                "field": "trust_score",
                                "expected": expected_trust,
                                "actual": actual_trust,
                            }
                        )
                    else:
                        verification_results["validators_verified"] += 1

            # Verify miner states
            current_miners = await contract_client.get_all_miners()
            for uid, expected_data in expected_updates.get("miners", {}).items():
                verification_results["total_checked"] += 1

                if uid in current_miners:
                    actual_miner = current_miners[uid]

                    # Check performance score
                    expected_performance = expected_data.get("last_performance", 0.0)
                    actual_performance = actual_miner.last_performance

                    if abs(actual_performance - expected_performance) > 0.001:
                        verification_results["mismatches"].append(
                            {
                                "type": "miner",
                                "uid": uid,
                                "field": "last_performance",
                                "expected": expected_performance,
                                "actual": actual_performance,
                            }
                        )
                    else:
                        verification_results["miners_verified"] += 1

            logger.info(
                f"🔍 Blockchain verification: {verification_results['validators_verified']} validators, "
                f"{verification_results['miners_verified']} miners verified, "
                f"{len(verification_results['mismatches'])} mismatches found"
            )

            return verification_results

    except Exception as e:
        logger.error(f"Error verifying blockchain state: {e}")
        raise BlockchainError(f"Blockchain verification failed: {e}")


async def get_blockchain_metrics(client: Web3, contract_address: str) -> Dict[str, Any]:
    """
    Get current blockchain metrics and statistics.

    Args:
        client: Web3 client
        contract_address: Contract address

    Returns:
        Dictionary with blockchain metrics
    """
    try:
        with ConsensusErrorHandler("get_blockchain_metrics"):
            from ..core_client.contract_client import ModernTensorCoreClient

            contract_client = ModernTensorCoreClient(
                w3=client, contract_address=contract_address, account=None
            )

            # Get current state
            validators = await contract_client.get_all_validators()
            miners = await contract_client.get_all_miners()

            # Calculate metrics
            active_validators = [
                v for v in validators.values() if v.status == STATUS_ACTIVE
            ]
            active_miners = [m for m in miners.values() if m.status == STATUS_ACTIVE]

            # Enhanced total stake calculation with Bitcoin integration
            total_stake = sum(
                v.stake + getattr(v, "bitcoin_stake", 0) * 2.0  # Bitcoin 2x multiplier
                for v in validators.values()
            )
            avg_trust_score = (
                sum(v.trust_score for v in active_validators) / len(active_validators)
                if active_validators
                else 0.0
            )
            avg_performance = (
                sum(v.last_performance for v in active_validators)
                / len(active_validators)
                if active_validators
                else 0.0
            )

            metrics = {
                "total_validators": len(validators),
                "active_validators": len(active_validators),
                "jailed_validators": len(
                    [v for v in validators.values() if v.status == STATUS_JAILED]
                ),
                "total_miners": len(miners),
                "active_miners": len(active_miners),
                "total_stake": total_stake,
                "average_trust_score": avg_trust_score,
                "average_performance": avg_performance,
                "block_number": client.eth.block_number,
                "network_health": (
                    "healthy" if len(active_validators) >= 2 else "degraded"
                ),
            }

            return metrics

    except Exception as e:
        logger.error(f"Error getting blockchain metrics: {e}")
        raise BlockchainError(f"Failed to get blockchain metrics: {e}")

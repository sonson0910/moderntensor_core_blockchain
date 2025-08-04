"""
Bittensor-Style Consensus Mechanism for ModernTensor Core
Implements UID-based indexing, consensus algorithms, and incentive calculations
"""

import asyncio
import logging
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from web3 import Web3
from eth_account import Account

from ..core_client.contract_client import ModernTensorCoreClient
from ..config.settings import Settings

logger = logging.getLogger(__name__)


@dataclass
class ConsensusRound:
    """Represents a consensus round"""

    round_id: int
    epoch: int
    participants: List[int]  # UIDs
    scores: Dict[int, float]  # UID -> normalized score
    weights: Dict[int, float]  # UID -> weight
    rewards: Dict[int, float]  # UID -> reward
    timestamp: int


@dataclass
class NetworkMetrics:
    """Network-wide performance metrics"""

    total_miners: int
    total_validators: int
    active_miners: int
    active_validators: int
    average_performance: float
    total_stake: int
    bitcoin_stake: int
    consensus_rounds: int


class ModernConsensus:
    """
    Bittensor-style consensus mechanism with:
    - UID-based participant indexing
    - Weighted consensus calculations
    - Trust score updates
    - Incentive distribution
    - Bitcoin staking integration
    """

    def __init__(self, core_client: ModernTensorCoreClient, settings: Settings):
        self.core_client = core_client
        self.settings = settings
        self.consensus_history: List[ConsensusRound] = []
        self.current_epoch = 0
        self.consensus_threshold = 0.67  # 67% consensus threshold

    async def run_consensus_round(self, subnet_uid: int = 1) -> ConsensusRound:
        """
        Run a complete Bittensor-style consensus round

        Args:
            subnet_uid: Subnet to run consensus for

        Returns:
            ConsensusRound: Results of the consensus round
        """
        logger.info(f"🔄 Starting consensus round for subnet {subnet_uid}")

        try:
            # 1. Get active participants
            miners = await self.get_active_miners(subnet_uid)
            validators = await self.get_active_validators(subnet_uid)

            logger.info(
                f"📊 Active miners: {len(miners)}, validators: {len(validators)}"
            )

            # 2. Collect validator scores for miners
            miner_scores = await self.collect_miner_evaluations(miners, validators)

            # 3. Calculate consensus weights
            consensus_weights = await self.calculate_consensus_weights(validators)

            # 4. Apply consensus algorithm
            final_scores = self.apply_consensus_algorithm(
                miner_scores, consensus_weights
            )

            # 5. Calculate incentives
            rewards = self.calculate_incentives(final_scores, miners)

            # 6. Update trust scores
            await self.update_trust_scores(final_scores)

            # 7. Distribute rewards
            await self.distribute_rewards(rewards)

            # Create consensus round record
            round_record = ConsensusRound(
                round_id=len(self.consensus_history) + 1,
                epoch=self.current_epoch,
                participants=list(miners.keys()) + list(validators.keys()),
                scores=final_scores,
                weights=consensus_weights,
                rewards=rewards,
                timestamp=int(asyncio.get_event_loop().time()),
            )

            self.consensus_history.append(round_record)
            logger.info(f"✅ Consensus round completed successfully")

            return round_record

        except Exception as e:
            logger.error(f"❌ Consensus round failed: {e}")
            raise

    async def get_active_miners(self, subnet_uid: int) -> Dict[int, Dict]:
        """Get active miners for subnet with UID indexing"""
        try:
            # Get active miner UIDs from contract
            active_uids = (
                self.core_client.contract.functions.getActiveMinerUids().call()
            )

            miners = {}
            for uid in active_uids:
                miner_data = self.core_client.contract.functions.getMinerData(
                    uid
                ).call()
                if (
                    miner_data[1] == subnet_uid and miner_data[9] == 1
                ):  # subnet_uid and status ACTIVE
                    miners[uid] = {
                        "uid": uid,
                        "stake": miner_data[2],
                        "bitcoin_stake": miner_data[3],
                        "performance": miner_data[4]
                        / 1000000,  # Scale back from contract
                        "trust_score": miner_data[5] / 1000000,
                        "owner": miner_data[13],
                    }

            return miners

        except Exception as e:
            logger.error(f"Error getting active miners: {e}")
            return {}

    async def get_active_validators(self, subnet_uid: int) -> Dict[int, Dict]:
        """Get active validators for subnet with UID indexing"""
        try:
            # Get active validator UIDs from contract
            active_uids = (
                self.core_client.contract.functions.getActiveValidatorUids().call()
            )

            validators = {}
            for uid in active_uids:
                validator_data = self.core_client.contract.functions.getValidatorData(
                    uid
                ).call()
                if (
                    validator_data[1] == subnet_uid and validator_data[9] == 1
                ):  # subnet_uid and status ACTIVE
                    validators[uid] = {
                        "uid": uid,
                        "stake": validator_data[2],
                        "bitcoin_stake": validator_data[3],
                        "performance": validator_data[4] / 1000000,
                        "trust_score": validator_data[5] / 1000000,
                        "owner": validator_data[13],
                    }

            return validators

        except Exception as e:
            logger.error(f"Error getting active validators: {e}")
            return {}

    async def collect_miner_evaluations(
        self, miners: Dict[int, Dict], validators: Dict[int, Dict]
    ) -> Dict[int, Dict[int, float]]:
        """
        Collect evaluations from validators for each miner

        Returns:
            Dict[miner_uid, Dict[validator_uid, score]]
        """
        evaluations = {}

        for miner_uid in miners.keys():
            evaluations[miner_uid] = {}

            # In a real implementation, this would query actual validator evaluations
            # For now, simulate based on current performance and some randomness
            for validator_uid, validator_data in validators.items():
                # Simulate evaluation with some noise
                base_score = miners[miner_uid]["performance"]
                validator_reliability = validator_data["trust_score"]

                # Add some randomness based on validator reliability
                noise = np.random.normal(0, 0.1 * (1 - validator_reliability))
                evaluation_score = max(0, min(1, base_score + noise))

                evaluations[miner_uid][validator_uid] = evaluation_score

        return evaluations

    async def calculate_consensus_weights(
        self, validators: Dict[int, Dict]
    ) -> Dict[int, float]:
        """Calculate consensus weights for validators based on stake and trust"""
        weights = {}
        total_weighted_stake = 0

        # Calculate weighted stakes
        for uid, validator_data in validators.items():
            stake = validator_data["stake"]
            bitcoin_stake = validator_data["bitcoin_stake"]
            trust_score = validator_data["trust_score"]

            # Calculate staking tier multiplier
            tier_multiplier = self.calculate_staking_tier_multiplier(
                stake, bitcoin_stake
            )

            # Weight = (stake * tier_multiplier * trust_score)
            weight = stake * tier_multiplier * trust_score
            weights[uid] = weight
            total_weighted_stake += weight

        # Normalize weights
        if total_weighted_stake > 0:
            for uid in weights:
                weights[uid] = weights[uid] / total_weighted_stake

        return weights

    def calculate_staking_tier_multiplier(
        self, core_stake: int, bitcoin_stake: int
    ) -> float:
        """Calculate staking tier multiplier based on dual staking"""
        if bitcoin_stake == 0:
            return 1.0  # Base tier

        ratio = (core_stake * 1000) // bitcoin_stake  # Avoid division by zero

        if ratio >= 1000:
            return 2.0  # Satoshi tier
        elif ratio >= 500:
            return 1.5  # Super tier
        elif ratio >= 100:
            return 1.25  # Boost tier
        else:
            return 1.0  # Base tier

    def apply_consensus_algorithm(
        self,
        miner_scores: Dict[int, Dict[int, float]],
        validator_weights: Dict[int, float],
    ) -> Dict[int, float]:
        """
        Apply Bittensor-style consensus algorithm

        Args:
            miner_scores: Dict[miner_uid, Dict[validator_uid, score]]
            validator_weights: Dict[validator_uid, weight]

        Returns:
            Dict[miner_uid, final_consensus_score]
        """
        consensus_scores = {}

        for miner_uid, evaluations in miner_scores.items():
            weighted_sum = 0
            total_weight = 0

            for validator_uid, score in evaluations.items():
                if validator_uid in validator_weights:
                    weight = validator_weights[validator_uid]
                    weighted_sum += score * weight
                    total_weight += weight

            if total_weight > 0:
                consensus_scores[miner_uid] = weighted_sum / total_weight
            else:
                consensus_scores[miner_uid] = 0

        return consensus_scores

    def calculate_incentives(
        self, consensus_scores: Dict[int, float], miners: Dict[int, Dict]
    ) -> Dict[int, float]:
        """
        Calculate incentive distribution based on Bittensor formulas

        Implements the formula from the whitepaper:
        Incentive_miner(x) = trust_score(x) * (W_x * P_x) / sum(W_i * P_i)
        """
        rewards = {}
        total_weighted_performance = 0

        # Calculate total weighted performance
        for miner_uid, score in consensus_scores.items():
            if miner_uid in miners:
                miner_data = miners[miner_uid]
                stake = miner_data["stake"]
                bitcoin_stake = miner_data["bitcoin_stake"]

                # Calculate weight (stake * tier_multiplier)
                tier_multiplier = self.calculate_staking_tier_multiplier(
                    stake, bitcoin_stake
                )
                weight = stake * tier_multiplier

                total_weighted_performance += weight * score

        # Calculate individual rewards
        for miner_uid, score in consensus_scores.items():
            if miner_uid in miners:
                miner_data = miners[miner_uid]
                stake = miner_data["stake"]
                bitcoin_stake = miner_data["bitcoin_stake"]
                trust_score = miner_data["trust_score"]

                # Calculate weight
                tier_multiplier = self.calculate_staking_tier_multiplier(
                    stake, bitcoin_stake
                )
                weight = stake * tier_multiplier

                # Apply Bittensor incentive formula
                if total_weighted_performance > 0:
                    reward = trust_score * (weight * score) / total_weighted_performance
                    rewards[miner_uid] = reward
                else:
                    rewards[miner_uid] = 0

        return rewards

    async def update_trust_scores(self, consensus_scores: Dict[int, float]):
        """Update trust scores based on consensus performance"""
        for miner_uid, score in consensus_scores.items():
            # Convert score to scaled integer for contract
            scaled_performance = int(score * 1000000)

            # Trust score update with exponential moving average
            # new_trust = old_trust * 0.9 + new_performance * 0.1
            current_trust_scaled = int(consensus_scores.get(miner_uid, 0.5) * 1000000)
            new_trust_scaled = int(
                current_trust_scaled * 0.9 + scaled_performance * 0.1
            )

            try:
                # Update performance and trust score on contract
                tx_hash = self.core_client.contract.functions.updateMinerPerformance(
                    miner_uid, scaled_performance, new_trust_scaled
                ).transact()

                logger.debug(
                    f"📊 Updated miner {miner_uid} scores: performance={score:.4f}, trust={new_trust_scaled/1000000:.4f}"
                )

            except Exception as e:
                logger.error(f"Failed to update scores for miner {miner_uid}: {e}")

    async def distribute_rewards(self, rewards: Dict[int, float]):
        """Distribute calculated rewards to miners"""
        # In a real implementation, this would trigger actual token transfers
        # For now, just log the rewards
        total_rewards = sum(rewards.values())

        logger.info(f"💰 Distributing rewards: {total_rewards:.6f} total")
        for uid, reward in rewards.items():
            if reward > 0:
                logger.info(f"  Miner {uid}: {reward:.6f} CORE tokens")

    async def get_network_metrics(self) -> NetworkMetrics:
        """Get comprehensive network metrics"""
        try:
            # Get all active participants
            miners = await self.get_active_miners(1)  # Default subnet
            validators = await self.get_active_validators(1)

            # Calculate metrics
            total_stake = sum(m["stake"] for m in miners.values()) + sum(
                v["stake"] for v in validators.values()
            )
            bitcoin_stake = sum(m["bitcoin_stake"] for m in miners.values()) + sum(
                v["bitcoin_stake"] for v in validators.values()
            )
            avg_performance = (
                np.mean([m["performance"] for m in miners.values()]) if miners else 0
            )

            return NetworkMetrics(
                total_miners=len(miners),
                total_validators=len(validators),
                active_miners=len(
                    [m for m in miners.values() if m["performance"] > 0.1]
                ),
                active_validators=len(
                    [v for v in validators.values() if v["trust_score"] > 0.5]
                ),
                average_performance=avg_performance,
                total_stake=total_stake,
                bitcoin_stake=bitcoin_stake,
                consensus_rounds=len(self.consensus_history),
            )

        except Exception as e:
            logger.error(f"Error getting network metrics: {e}")
            return NetworkMetrics(0, 0, 0, 0, 0, 0, 0, 0)


# Consensus utilities
def format_consensus_results(consensus_round: ConsensusRound) -> str:
    """Format consensus results for display"""
    result = f"""
🎯 Consensus Round #{consensus_round.round_id} Results:
📊 Epoch: {consensus_round.epoch}
👥 Participants: {len(consensus_round.participants)}
💰 Total Rewards: {sum(consensus_round.rewards.values()):.6f} CORE
⏰ Timestamp: {consensus_round.timestamp}

Top Performers:
"""

    # Sort by rewards
    sorted_rewards = sorted(
        consensus_round.rewards.items(), key=lambda x: x[1], reverse=True
    )
    for uid, reward in sorted_rewards[:5]:  # Top 5
        score = consensus_round.scores.get(uid, 0)
        result += f"  UID {uid}: {reward:.6f} CORE (score: {score:.4f})\n"

    return result

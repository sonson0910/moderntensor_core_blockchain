#!/usr/bin/env python3
"""
Scoring Module for ModernTensor Consensus

This module implements the scoring algorithms for the ModernTensor consensus protocol.
It provides functions for calculating miner performance scores, validator weights,
and various scoring metrics used in the consensus process.

Key Components:
- Performance score calculation
- Validator weight calculation
- Consensus score aggregation
- Trust score updates
- Incentive calculations

The scoring system is designed to reward high-performing miners and validators
while penalizing malicious or underperforming participants.
"""

import logging
import math
import json
import statistics
import asyncio
import binascii
from collections import defaultdict
from typing import Dict, List, Optional, Tuple, Any, TYPE_CHECKING

# Third-party imports
import httpx
import nacl.signing
from nacl.exceptions import CryptoError
from pydantic import BaseModel

# Updated imports for Core blockchain
from web3 import Web3
from eth_account import Account
from eth_account.signers.local import LocalAccount

# Remove Aptos SDK imports
# from eth_account import Account

from ..config.settings import settings
from ..core.datatypes import (
    ValidatorInfo,
    MinerInfo,
    ValidatorScore,
    TaskAssignment,
    MinerResult,
)

# PHASE 1: Import advanced scoring formulas
import time
import statistics
from collections import defaultdict
from typing import Any, Dict, List, Tuple

from ..formulas.performance import (
    calculate_task_completion_rate,
    calculate_adjusted_miner_performance,
    calculate_validator_performance,
    calculate_penalty_term,
)
from ..formulas.trust_score import update_trust_score, calculate_selection_probability
from ..formulas.incentive import (
    calculate_miner_incentive,
    calculate_validator_incentive,
)
from ..formulas.miner_weight import calculate_miner_weight
from ..formulas.penalty import (
    calculate_performance_adjustment,
    calculate_fraud_severity_value,
)


class ScoreSubmissionPayload(BaseModel):
    """Payload for submitting scores to other validators."""

    submitter_validator_uid: str
    cycle: int
    scores: List[ValidatorScore]
    signature: str
    public_key_hex: str


logger = logging.getLogger(__name__)


# PHASE 1: Advanced scoring configuration
ADVANCED_SCORING_CONFIG = {
    "enable_trust_scores": True,
    "enable_historical_weighting": True,
    "enable_fraud_detection": True,
    "enable_performance_adjustment": True,
    # Trust score parameters
    "trust_decay_rate": 0.1,
    "trust_learning_rate": 0.1,
    "trust_sigmoid_k": 5.0,
    # Performance weighting
    "performance_decay_constant": 0.5,
    "min_history_for_weighting": 3,
    # Fraud detection thresholds
    "deviation_threshold": 0.3,
    "fraud_penalty_factor": 0.5,
    # Incentive calculation
    "incentive_sigmoid_k": 10.0,
    "incentive_sigmoid_L": 1.0,
}


# Move ScoreSubmissionPayload class to after ValidatorScore import


# --- Helper function for canonical serialization ---
def canonical_json_serialize(data: Any) -> str:
    """Serialize dữ liệu thành chuỗi JSON ổn định (sắp xếp key).

    Recursively converts dataclasses and dictionaries, handling bytes by
    encoding them as hex strings. Ensures consistent output for signing
    by sorting dictionary keys.

    Args:
        data: Dữ liệu cần serialize (có thể là dataclass, dict, list, etc.).

    Returns:
        Chuỗi JSON đại diện cho dữ liệu, với keys được sắp xếp.
    """
    import dataclasses  # Ensure dataclasses is imported here or globally

    def convert_to_dict(obj):
        if dataclasses.is_dataclass(obj):
            result = {}
            for f in dataclasses.fields(obj):
                value = getattr(obj, f.name)
                result[f.name] = convert_to_dict(value)
            return result
        elif isinstance(obj, list):
            return [convert_to_dict(item) for item in obj]
        elif isinstance(obj, dict):
            return {k: convert_to_dict(v) for k, v in obj.items()}
        # Thêm xử lý bytes -> hex string để JSON serialize được
        elif isinstance(obj, bytes):
            return obj.hex()
        else:
            return obj

    data_to_serialize = convert_to_dict(data)
    return json.dumps(data_to_serialize, sort_keys=True, separators=(",", ":"))


# --- END INSERT ---

if TYPE_CHECKING:
    # Import ValidatorNode only for type checking to avoid circular import
    from .validator_node_refactored import ValidatorNode
    from ..core.datatypes import (
        ValidatorScore,
        ValidatorInfo,
    )


# PHASE 1: Advanced scoring data structures
MINER_PERFORMANCE_HISTORY = defaultdict(list)  # miner_uid -> [scores]
MINER_TRUST_SCORES = defaultdict(lambda: 0.5)  # miner_uid -> trust_score
MINER_LAST_EVALUATION = defaultdict(int)  # miner_uid -> timestamp
VALIDATOR_DEVIATION_HISTORY = defaultdict(list)  # validator_uid -> [deviations]


def calculate_advanced_score(
    task_data: Any,
    result_data: Any,
    miner_uid: str,
    validator_uid: str,
    validator_instance=None,
    current_time_step: int = None,
) -> Tuple[float, Dict[str, Any]]:
    """
    PHASE 1: Advanced scoring engine with trust scores, historical weighting, and fraud detection.

    Args:
        task_data: Task assignment data
        result_data: Miner result data
        miner_uid: Miner identifier
        validator_uid: Validator identifier
        validator_instance: Validator instance for subnet-specific scoring
        current_time_step: Current time step for historical weighting

    Returns:
        Tuple of (final_score, scoring_metadata)
    """
    config = ADVANCED_SCORING_CONFIG
    metadata = {}

    try:
        # 1. Get basic score from validator instance or default
        if validator_instance and hasattr(
            validator_instance, "_score_individual_result"
        ):
            basic_score = validator_instance._score_individual_result(
                task_data, result_data
            )
        else:
            basic_score = _calculate_score_from_result_fallback(task_data, result_data)

        basic_score = max(0.0, min(1.0, basic_score))
        metadata["basic_score"] = basic_score

        # 2. Historical performance weighting (if enabled)
        weighted_score = basic_score
        if (
            config["enable_historical_weighting"]
            and len(MINER_PERFORMANCE_HISTORY[miner_uid])
            >= config["min_history_for_weighting"]
        ):
            miner_weight = calculate_miner_weight(
                MINER_PERFORMANCE_HISTORY[miner_uid],
                current_time_step or int(time.time()),
                decay_constant_W=config["performance_decay_constant"],
            )
            weighted_score = basic_score * (
                1.0 + miner_weight * 0.1
            )  # 10% boost for good history
            metadata["miner_weight"] = miner_weight
            metadata["weighted_score"] = weighted_score

        # 3. Trust score adjustment (if enabled)
        trust_adjusted_score = weighted_score
        if config["enable_trust_scores"]:
            current_trust = MINER_TRUST_SCORES[miner_uid]
            time_since_last = max(
                1, int(time.time()) - MINER_LAST_EVALUATION[miner_uid]
            )

            # Update trust score based on performance
            new_trust = update_trust_score(
                trust_score_old=current_trust,
                time_since_last_eval=time_since_last,
                score_new=basic_score,
                delta_trust=config["trust_decay_rate"],
                alpha_base=config["trust_learning_rate"],
                update_sigmoid_k=config["trust_sigmoid_k"],
            )

            MINER_TRUST_SCORES[miner_uid] = new_trust
            MINER_LAST_EVALUATION[miner_uid] = int(time.time())

            # Apply trust multiplier
            trust_multiplier = 0.5 + (new_trust * 0.5)  # Range [0.5, 1.0]
            trust_adjusted_score = weighted_score * trust_multiplier

            metadata["trust_score_old"] = current_trust
            metadata["trust_score_new"] = new_trust
            metadata["trust_multiplier"] = trust_multiplier
            metadata["trust_adjusted_score"] = trust_adjusted_score

        # 4. Update performance history
        MINER_PERFORMANCE_HISTORY[miner_uid].append(basic_score)
        if len(MINER_PERFORMANCE_HISTORY[miner_uid]) > 50:  # Keep last 50 scores
            MINER_PERFORMANCE_HISTORY[miner_uid].pop(0)

        # 5. Fraud detection (if enabled)
        fraud_penalty = 0.0
        if (
            config["enable_fraud_detection"]
            and len(MINER_PERFORMANCE_HISTORY[miner_uid]) > 5
        ):
            # Calculate deviation from recent average
            recent_scores = MINER_PERFORMANCE_HISTORY[miner_uid][-5:]
            avg_score = sum(recent_scores) / len(recent_scores)
            deviation = abs(basic_score - avg_score)

            if deviation > config["deviation_threshold"]:
                fraud_penalty = deviation * config["fraud_penalty_factor"]
                metadata["fraud_detected"] = True
                metadata["deviation"] = deviation
                metadata["fraud_penalty"] = fraud_penalty
                logger.warning(
                    f"🚨 Possible fraud detected for miner {miner_uid}: deviation {deviation:.3f}"
                )

        # 6. Calculate final score
        final_score = max(0.0, min(1.0, trust_adjusted_score - fraud_penalty))
        metadata["final_score"] = final_score
        metadata["performance_improvement"] = final_score - basic_score

        # 7. Logging for transparency
        if final_score != basic_score:
            logger.info(
                f"📊 Advanced scoring for {miner_uid}: "
                f"basic={basic_score:.3f} → final={final_score:.3f} "
                f"(trust={MINER_TRUST_SCORES[miner_uid]:.3f}, fraud_penalty={fraud_penalty:.3f})"
            )

        return final_score, metadata

    except Exception as e:
        logger.error(f"Error in advanced scoring for {miner_uid}: {e}")
        return basic_score, {"error": str(e), "fallback_used": True}


# --- 1. Fallback for basic scoring (legacy compatibility) ---
def _calculate_score_from_result_fallback(task_data: Any, result_data: Any) -> float:
    """
    Fallback scoring logic when no validator-specific implementation is available.

    Args:
        task_data: Task assignment data
        result_data: Miner result data

    Returns:
        Basic score (0.0 to 1.0)
    """
    # Handle timeout/error cases
    if isinstance(result_data, dict):
        if result_data.get("error") == "timeout" or result_data.get("timeout"):
            return 0.0
        if "error" in result_data:
            return 0.1  # Small score for attempt but error

    # Basic image validation for common AI tasks
    if isinstance(result_data, dict) and "image" in str(result_data).lower():
        # Simple validation: check if base64 data exists
        for key, value in result_data.items():
            if isinstance(value, str) and len(value) > 100:  # Likely base64 image
                return 0.8  # Good score for valid image

    # Default: moderate score for any non-error response
    return 0.5


def _calculate_score_from_result(task_data: Any, result_data: Any) -> float:
    """
    (Legacy function - maintained for compatibility)
    Basic scoring function that delegates to advanced scoring.
    """
    score, _ = calculate_advanced_score(task_data, result_data, "unknown", "unknown")
    return score


# ---------------------------------------


def score_results_logic(
    results_received: Dict[str, List[MinerResult]],
    tasks_sent: Dict[str, TaskAssignment],
    validator_uid: str,
    validator_instance=None,  # Thêm validator instance
) -> Dict[str, List[ValidatorScore]]:
    """
    Chấm điểm tất cả các kết quả hợp lệ nhận được từ miners cho chu kỳ hiện tại.

    Iterates through results received for each task ID. For each result, it verifies:
    1. If the task ID corresponds to a task actually sent by this validator.
    2. If the result came from the miner the task was assigned to.

    Valid results are then scored using `_calculate_score_from_result`, and a
    `ValidatorScore` object is created.

    Args:
        results_received: Dictionary mapping task IDs to lists of `MinerResult` objects received.
                          {task_id: [MinerResult, MinerResult, ...]}.
        tasks_sent: Dictionary mapping task IDs to the `TaskAssignment` objects sent out.
                    {task_id: TaskAssignment}.
        validator_uid: UID (hex string) of the validator performing the scoring.

    Returns:
        Dictionary mapping task IDs to lists of `ValidatorScore` objects generated by this validator.
        {task_id: [ValidatorScore, ValidatorScore, ...]}. Returns scores only for valid, processed results.
    """
    logger.info(
        f"[V:{validator_uid}] Scoring {len(results_received)} received tasks..."
    )
    validator_scores: Dict[str, List[ValidatorScore]] = defaultdict(list)

    for task_id, results in results_received.items():
        assignment = tasks_sent.get(task_id)
        if not assignment:
            logger.warning(
                f"Scoring skipped: Task assignment not found for task_id {task_id}."
            )
            continue

        # Handle timeout case: empty results list means task was sent but no response received
        if not results:
            logger.warning(
                f"No results received for task {task_id} from miner {assignment.miner_uid} (timeout). Assigning 0 score."
            )
            val_score = ValidatorScore(
                task_id=task_id,
                miner_uid=assignment.miner_uid,
                validator_uid=validator_uid,
                score=0.0,  # 0 điểm cho timeout
            )
            validator_scores[task_id].append(val_score)
            logger.info(
                f"  Assigned 0.0000 score to miner {assignment.miner_uid} for task {task_id} (timeout)"
            )
            continue

        # Chỉ chấm điểm kết quả đầu tiên hợp lệ từ đúng miner? Hay chấm tất cả?
        # Tạm thời chấm kết quả đầu tiên từ đúng miner
        valid_result_found = False
        for result in results:
            if result.miner_uid == assignment.miner_uid:
                # PHASE 1: Use advanced scoring engine
                try:
                    current_time_step = int(time.time())

                    # Use advanced scoring with full context
                    score, scoring_metadata = calculate_advanced_score(
                        task_data=assignment.task_data,
                        result_data=result.result_data,
                        miner_uid=result.miner_uid,
                        validator_uid=validator_uid,
                        validator_instance=validator_instance,
                        current_time_step=current_time_step,
                    )

                    # Đảm bảo điểm nằm trong khoảng [0, 1]
                    score = max(0.0, min(1.0, score))
                    valid_result_found = True  # Đánh dấu đã tìm thấy kết quả hợp lệ

                    # Log advanced scoring details if score was adjusted
                    if scoring_metadata.get("performance_improvement", 0) != 0:
                        improvement = scoring_metadata["performance_improvement"]
                        logger.info(
                            f"🎯 Advanced scoring improved score by {improvement:+.3f} for {result.miner_uid}"
                        )

                    # Log trust score evolution
                    if "trust_score_new" in scoring_metadata:
                        trust_old = scoring_metadata.get("trust_score_old", 0.5)
                        trust_new = scoring_metadata["trust_score_new"]
                        trust_change = trust_new - trust_old
                        logger.info(
                            f"📈 Trust score for {result.miner_uid}: {trust_old:.3f} → {trust_new:.3f} ({trust_change:+.3f})"
                        )
                except NotImplementedError:
                    logger.error(
                        f"Scoring logic not implemented for task {task_id}! Assigning score 0."
                    )
                    score = 0.0
                    valid_result_found = True  # Vẫn coi như đã xử lý
                except Exception as e:
                    logger.exception(
                        f"Error calculating score for task {task_id}, miner {result.miner_uid}: {e}. Assigning score 0."
                    )
                    score = 0.0
                    # Có nên coi đây là kết quả hợp lệ để dừng không? Tạm thời không.
                    continue  # Thử kết quả tiếp theo nếu có lỗi

                # Enhanced logging with advanced scoring details
                basic_score = scoring_metadata.get("basic_score", score)
                if score != basic_score:
                    logger.info(
                        f"  📊 Advanced Scored Miner {result.miner_uid} for task {task_id}: "
                        f"basic={basic_score:.4f} → final={score:.4f}"
                    )
                else:
                    logger.info(
                        f"  📊 Scored Miner {result.miner_uid} for task {task_id}: {score:.4f}"
                    )

                val_score = ValidatorScore(
                    task_id=task_id,
                    miner_uid=result.miner_uid,
                    validator_uid=validator_uid,
                    score=score,
                )
                validator_scores[task_id].append(val_score)
                break  # Chỉ chấm điểm kết quả hợp lệ đầu tiên từ đúng miner

        if not valid_result_found:
            logger.warning(
                f"No valid result found from expected miner {assignment.miner_uid} for task {task_id}. Assigning 0 score for timeout/no response."
            )
            # Tạo điểm 0 cho miner timeout/không response
            val_score = ValidatorScore(
                task_id=task_id,
                miner_uid=assignment.miner_uid,
                validator_uid=validator_uid,
                score=0.0,  # 0 điểm cho timeout
            )
            validator_scores[task_id].append(val_score)
            logger.info(
                f"  Assigned 0.0000 score to miner {assignment.miner_uid} for task {task_id} (timeout/no response)"
            )

    logger.info(
        f"Finished scoring. Generated scores for {len(validator_scores)} tasks."
    )

    # PHASE 1: Calculate advanced incentives based on sophisticated scoring
    if ADVANCED_SCORING_CONFIG["enable_trust_scores"]:
        _calculate_and_log_advanced_incentives(validator_scores, validator_uid)

    return dict(validator_scores)


def _calculate_and_log_advanced_incentives(
    validator_scores: Dict[str, List[ValidatorScore]], validator_uid: str
) -> Dict[str, float]:
    """
    PHASE 1: Calculate advanced incentives for miners based on sophisticated scoring results.

    Args:
        validator_scores: Dictionary of task_id -> ValidatorScore objects
        validator_uid: Validator identifier

    Returns:
        Dictionary of miner_uid -> incentive_amount
    """
    try:
        config = ADVANCED_SCORING_CONFIG
        miner_incentives = {}

        # Collect all miner scores
        miner_total_scores = defaultdict(list)
        for task_scores in validator_scores.values():
            for score_obj in task_scores:
                miner_total_scores[score_obj.miner_uid].append(score_obj.score)

        # Calculate total system value for relative incentives
        total_system_value = 0.0
        for miner_uid, scores in miner_total_scores.items():
            miner_weight = 1.0  # Default weight
            if (
                len(MINER_PERFORMANCE_HISTORY[miner_uid])
                >= config["min_history_for_weighting"]
            ):
                miner_weight = calculate_miner_weight(
                    MINER_PERFORMANCE_HISTORY[miner_uid],
                    int(time.time()),
                    decay_constant_W=config["performance_decay_constant"],
                )

            avg_score = sum(scores) / len(scores) if scores else 0.0
            total_system_value += miner_weight * avg_score

        # Calculate incentives for each miner
        for miner_uid, scores in miner_total_scores.items():
            if not scores:
                continue

            avg_score = sum(scores) / len(scores)
            trust_score = MINER_TRUST_SCORES[miner_uid]

            # Get miner weight from history
            miner_weight = 1.0
            if (
                len(MINER_PERFORMANCE_HISTORY[miner_uid])
                >= config["min_history_for_weighting"]
            ):
                miner_weight = calculate_miner_weight(
                    MINER_PERFORMANCE_HISTORY[miner_uid],
                    int(time.time()),
                    decay_constant_W=config["performance_decay_constant"],
                )

            # Calculate sophisticated incentive
            incentive = calculate_miner_incentive(
                trust_score=trust_score,
                miner_weight=miner_weight,
                miner_performance_scores=scores,
                total_system_value=max(
                    total_system_value, 0.001
                ),  # Avoid division by zero
                incentive_sigmoid_L=config["incentive_sigmoid_L"],
                incentive_sigmoid_k=config["incentive_sigmoid_k"],
            )

            miner_incentives[miner_uid] = incentive

            # Log incentive calculation details
            logger.info(
                f"💰 Advanced incentive for {miner_uid}: {incentive:.6f} "
                f"(trust={trust_score:.3f}, weight={miner_weight:.3f}, avg_score={avg_score:.3f})"
            )

        # Log system-wide incentive distribution
        total_incentives = sum(miner_incentives.values())
        if total_incentives > 0:
            logger.info(
                f"📊 Total incentives distributed: {total_incentives:.6f} across {len(miner_incentives)} miners"
            )

            # Log top performers
            sorted_miners = sorted(
                miner_incentives.items(), key=lambda x: x[1], reverse=True
            )
            for i, (miner_uid, incentive) in enumerate(sorted_miners[:3]):
                logger.info(f"🏆 Rank #{i+1}: {miner_uid} → {incentive:.6f} incentive")

        return miner_incentives

    except Exception as e:
        logger.error(f"Error calculating advanced incentives: {e}")
        return {}


def get_miner_advanced_stats(miner_uid: str) -> Dict[str, Any]:
    """
    PHASE 1: Get comprehensive statistics for a miner.

    Args:
        miner_uid: Miner identifier

    Returns:
        Dictionary with miner statistics
    """
    try:
        stats = {
            "miner_uid": miner_uid,
            "trust_score": MINER_TRUST_SCORES[miner_uid],
            "performance_history_length": len(MINER_PERFORMANCE_HISTORY[miner_uid]),
            "last_evaluation": MINER_LAST_EVALUATION[miner_uid],
        }

        if MINER_PERFORMANCE_HISTORY[miner_uid]:
            scores = MINER_PERFORMANCE_HISTORY[miner_uid]
            stats.update(
                {
                    "average_score": sum(scores) / len(scores),
                    "latest_score": scores[-1],
                    "score_trend": scores[-1] - scores[0] if len(scores) > 1 else 0.0,
                    "score_variance": (
                        statistics.variance(scores) if len(scores) > 1 else 0.0
                    ),
                }
            )

            # Calculate miner weight if enough history
            if len(scores) >= ADVANCED_SCORING_CONFIG["min_history_for_weighting"]:
                miner_weight = calculate_miner_weight(
                    scores,
                    int(time.time()),
                    decay_constant_W=ADVANCED_SCORING_CONFIG[
                        "performance_decay_constant"
                    ],
                )
                stats["miner_weight"] = miner_weight

        return stats

    except Exception as e:
        logger.error(f"Error getting miner stats for {miner_uid}: {e}")
        return {"miner_uid": miner_uid, "error": str(e)}


async def broadcast_scores_logic(
    validator_node: "ValidatorNode",
    cycle_scores_dict: Dict[str, List["ValidatorScore"]],
):
    """
    Gửi điểm số cục bộ (local_scores) đến các validator khác (peers), có ký dữ liệu.

    Performs the following steps:
    1. Fetches necessary info (signing key, active peers, http client) from the validator node.
    2. Flattens the `cycle_scores_dict` into a single list, keeping only scores generated
       by this validator (`self_uid`).
    3. If no local scores generated, logs a debug message and returns.
    4. Serializes the filtered list of scores into a canonical JSON string.
    5. Signs the serialized data using the validator's signing key.
    6. Creates a `ScoreSubmissionPayload` containing the scores, signature (hex),
       and the validator's public key.
    7. Iterates through the list of active validator peers (excluding self).
    8. Sends the payload via HTTP POST to the `/submit_scores` endpoint of each peer.

    Args:
        validator_node: The instance of the `ValidatorNode` running this logic.
                        Provides access to configuration, keys, peers, and HTTP client.
        cycle_scores_dict: A dictionary containing scores generated or received
                           during the current cycle, keyed by task ID.
                           {task_id: [ValidatorScore, ...]}. This function will
                           filter and broadcast only the scores generated *by* this node.

    Raises:
        AttributeError: If `validator_node` is missing required attributes/methods.
        TypeError: If the derived verification key type is unexpected.
        CryptoError: If signing fails.
        httpx.RequestError: If sending the request to a peer fails (e.g., connection error, timeout).
        Exception: For other unexpected errors during setup, signing, or sending.
    """
    try:
        # Lấy thông tin cần thiết từ validator_node
        self_validator_info = validator_node.info
        # Lấy signing key từ validator_node
        signing_key = validator_node.signing_key  # type: ignore
        # Lấy danh sách validator *active* từ node
        active_validator_peers = await validator_node._get_active_validators()
        current_cycle = validator_node.current_cycle
        http_client = validator_node.http_client
        settings = validator_node.settings
        self_uid = self_validator_info.uid  # UID của node hiện tại (dạng hex string)
    except AttributeError as e:  # Khôi phục khối except
        logger.error(
            f"Missing required attribute/method on validator_node for broadcasting: {e}"
        )
        return
    except Exception as e:  # Thêm một except chung để bắt lỗi khác khi lấy attributes
        logger.error(f"Error getting attributes from validator_node: {e}")
        return

    # --- Flatten và Lọc điểm cần gửi ---
    local_scores_list: List[ValidatorScore] = []
    for task_id, scores in cycle_scores_dict.items():
        for score in scores:
            if score.validator_uid == self_uid:
                local_scores_list.append(score)

    if not local_scores_list:
        logger.debug(f"[V:{self_uid}] No local scores to broadcast.")
        return

    logger.info(
        f"[V:{self_uid}] Preparing to broadcast {len(local_scores_list)} score entries generated by self for cycle {current_cycle}."
    )
    # Log peers for debugging
    active_peer_uids = [p.uid for p in active_validator_peers if p.uid != self_uid]
    logger.debug(
        f"[V:{self_uid}] Target active peers for broadcast: {active_peer_uids}"
    )

    # --- Ký Dữ liệu ---
    signature_hex: Optional[str] = None
    public_key_hex: Optional[str] = None
    try:
        # Serialize list điểm ĐÃ LỌC VÀ FLATTEN bằng hàm canonical
        data_to_sign_str = canonical_json_serialize(local_scores_list)
        data_to_sign_bytes = data_to_sign_str.encode("utf-8")

        # Ký bằng PyNaCl hoặc Aptos SDK (tùy vào validator_node.signing_key là gì)
        # Ví dụ sử dụng PyNaCl
        nacl_signing_key = nacl.signing.SigningKey(signing_key.private_key)
        signed_data = nacl_signing_key.sign(data_to_sign_bytes)
        signature_bytes = signed_data.signature

        # Lấy public key
        public_key_bytes = nacl_signing_key.verify_key.encode()

        signature_hex = binascii.hexlify(signature_bytes).decode("utf-8")
        public_key_hex = binascii.hexlify(public_key_bytes).decode("utf-8")

        logger.debug(f"[V:{self_uid}] Payload signed successfully.")
    except TypeError as type_e:
        logger.error(
            f"[V:{self_uid}] Type error during key derivation or serialization: {type_e}"
        )
        return
    except CryptoError as sign_e:  # USE IMPORTED CryptoError
        logger.exception(
            f"[V:{self_uid}] Failed to sign broadcast payload (PyNaCl): {sign_e}"
        )
        return
    except Exception as sign_e:  # Bắt lỗi chung khác
        logger.exception(
            f"[V:{self_uid}] Failed to prepare or sign broadcast payload: {sign_e}"
        )
        return

    # --- Tạo Payload ---
    # Đảm bảo các biến cần thiết đã được gán giá trị
    if signature_hex is None or public_key_hex is None:
        logger.error(
            f"[V:{self_uid}] Failed to obtain signature or public key. Aborting broadcast."
        )
        return

    payload = ScoreSubmissionPayload(
        submitter_validator_uid=self_uid,
        cycle=current_cycle,
        scores=local_scores_list,
        signature=signature_hex,
        public_key_hex=public_key_hex,  # Sử dụng trường public_key_hex thay vì submitter_vkey_cbor_hex
    )
    logger.debug(
        f"[V:{self_uid}] ScoreSubmissionPayload created. Scores count: {len(payload.scores)}, Cycle: {payload.cycle}"
    )

    # --- Gửi đến Peers ---
    tasks = []
    peer_endpoints = {}
    for peer_info in active_validator_peers:  # Lấy thông tin endpoint từ ValidatorInfo
        if peer_info.uid == self_uid:
            continue  # Bỏ qua chính mình
        if peer_info.api_endpoint:
            peer_endpoints[peer_info.uid] = (
                f"{peer_info.api_endpoint.rstrip('/')}/submit_scores"
            )
        else:
            logger.warning(
                f"[V:{self_uid}] Peer {peer_info.uid} has no API endpoint defined. Skipping broadcast."
            )

    async def send_score(peer_uid: str, peer_endpoint: str, payload_dict: dict):
        """Gửi payload điểm số đến một peer cụ thể."""
        try:
            # === FIX: Remove incorrect async with for shared client ===
            # async with http_client as client:  # Sử dụng http_client từ validator_node
            # Use the shared http_client directly
            response = await http_client.post(  # <<< Use http_client directly
                peer_endpoint,
                json=payload_dict,
                headers={"Content-Type": "application/json"},
                timeout=settings.CONSENSUS_NETWORK_TIMEOUT_SECONDS,
            )
            if response.status_code == 200:
                logger.info(
                    f"[V:{self_uid}] Successfully sent scores to peer {peer_uid} at {peer_endpoint}"
                )
            else:
                logger.warning(
                    f"[V:{self_uid}] Failed to send scores to peer {peer_uid} at {peer_endpoint}: Status {response.status_code} - {response.text[:100]}..."
                )
        except httpx.RequestError as req_err:
            logger.warning(
                f"[V:{self_uid}] HTTP request error sending scores to peer {peer_uid} at {peer_endpoint}: {req_err}"
            )
        except Exception as e:
            logger.error(
                f"[V:{self_uid}] Unexpected error sending scores to peer {peer_uid} ({peer_endpoint}): {e}",
                exc_info=True,
            )

    payload_as_dict = payload.dict()  # Chuyển payload thành dict một lần
    for peer_uid, endpoint in peer_endpoints.items():
        tasks.append(send_score(peer_uid, endpoint, payload_as_dict))

    if tasks:
        logger.info(f"[V:{self_uid}] Broadcasting scores to {len(tasks)} peers...")
        await asyncio.gather(*tasks)
        logger.info(
            f"[V:{self_uid}] Finished broadcasting scores for cycle {current_cycle}."
        )
    else:
        logger.info(
            f"[V:{self_uid}] No active peers with endpoints found to broadcast scores to."
        )

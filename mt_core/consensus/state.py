# DEPRECATED - USE state_refactored.py INSTEAD
"""
⚠️  DEPRECATION WARNING ⚠️
This file has been DEPRECATED and replaced by modular components.

Please use imports from:
- state_refactored.py (main orchestrator + backward compatibility)
- consensus_state_core.py (core consensus logic)
- consensus_penalties.py (penalty calculations)
- consensus_blockchain.py (blockchain operations)
- consensus_validation.py (validation logic)
- consensus_utils.py (utility functions)
- consensus_errors.py (error handling)
- consensus_config.py (configuration)

This file will be removed in a future version.
"""

import warnings
import logging
import numpy as np
from typing import Dict, List, Optional, Tuple, Any, Union, Set
from collections import defaultdict

warnings.warn(
    "mt_core.consensus.state is deprecated. Use state_refactored or specific consensus modules instead.",
    DeprecationWarning,
    stacklevel=2,
)


# Updated imports for Core blockchain
from web3 import Web3
from eth_account import Account
from eth_account.signers.local import LocalAccount

# FIXED: Use new configuration system
from ..config.config_loader import get_config
from ..core.datatypes import (
    MinerInfo,
    ValidatorInfo,
    ValidatorScore,
    TaskAssignment,
)
from ..formulas.performance import (
    calculate_adjusted_miner_performance,
    calculate_validator_performance,
)
from ..formulas.trust_score import update_trust_score
from ..formulas.penalty import calculate_fraud_severity_value, calculate_slash_amount
from ..formulas.incentive import (
    calculate_miner_incentive,
    calculate_validator_incentive,
)

from ..metagraph.metagraph_data import get_all_validator_data
from ..metagraph.hash.hash_datum import hash_data

from ..metagraph.metagraph_datum import (
    ValidatorData,
    MinerData,
    STATUS_ACTIVE,
    STATUS_JAILED,
    STATUS_INACTIVE,
)

# Load configuration
config = get_config()

EPSILON = 1e-9
logger = logging.getLogger(__name__)

# Default empty bytes for hash placeholders
EMPTY_HASH_BYTES = b""

# --- Logic Đồng thuận và Tính toán Trạng thái Validator ---


def calculate_historical_consistency(
    scores: List[float], max_stddev_penalty: float = 2.0
) -> float:
    """
    Calculates a quality score based on the standard deviation of historical scores.
    A lower standard deviation (more stable performance) results in a higher score.

    Args:
        scores (List[float]): A list of historical performance scores.
        max_stddev_penalty (float): The maximum standard deviation allowed before
                                  the quality score drops to 0. Defaults to 2.0.

    Returns:
        float: A quality score between 0.0 and 1.0.
    """
    if not scores or len(scores) < 2:
        return 0.5  # Return average value if insufficient data

    stddev = float(np.std(scores))

    # Chuẩn hóa điểm: 1.0 khi stddev=0, giảm dần về 0 khi stddev tăng
    # Ví dụ: Giảm tuyến tính, về 0 khi stddev >= max_stddev_penalty
    # Cần đảm bảo max_stddev_penalty > 0
    if max_stddev_penalty <= 0:
        max_stddev_penalty = 0.5  # Giá trị an toàn

    normalized_penalty = min(1.0, stddev / max_stddev_penalty)
    consistency_score = 1.0 - normalized_penalty

    # Đảm bảo kết quả cuối cùng trong khoảng [0, 1]
    return max(0.0, min(1.0, consistency_score))


# --- Hàm tìm dữ liệu theo UID trên Aptos ---
async def find_resource_by_uid(
    client: Web3,
    contract_address: str,
    account_address: str,
    resource_type: str,  # Ví dụ: "miner::MinerInfo" hoặc "validator::ValidatorInfo"
    uid_bytes: bytes,
) -> Optional[Dict[str, Any]]:
    """
    Tìm resource dữ liệu trên Aptos theo UID.

    Args:
        client (Web3): Client Aptos REST API.
        contract_address (str): Địa chỉ contract ModernTensor.
        account_address (str): Địa chỉ tài khoản chứa resource.
        resource_type (str): Loại resource cần tìm.
        uid_bytes (bytes): UID dưới dạng bytes để tìm kiếm.

    Returns:
        Optional[Dict[str, Any]]: Dữ liệu resource tìm được, hoặc None nếu không tìm thấy.
    """
    logger.debug(
        f"Searching for resource {resource_type} with UID {uid_bytes.hex()} for account {account_address}..."
    )

    try:
        # Format resource full path
        full_resource_type = f"{contract_address}::{resource_type}"

        # Lấy dữ liệu resource từ tài khoản
        resources = await client.eth.get_account_resources(account_address)

        # Lọc resource theo loại
        for resource in resources:
            if resource["type"] == full_resource_type:
                # Kiểm tra UID
                if resource["data"].get("uid") == uid_bytes.hex():
                    return resource["data"]

        logger.warning(
            f"Resource {resource_type} with UID {uid_bytes.hex()} not found for account {account_address}."
        )
        return None

    except Exception as e:
        logger.error(
            f"Failed to fetch resources for {account_address} while searching for {resource_type} with UID {uid_bytes.hex()}: {e}"
        )
        return None


# --- Hàm tính Severity tinh chỉnh hơn ---
def _calculate_fraud_severity(reason: str, tolerance: float) -> float:
    """
    Calculates a fraud severity score based on the deviation reason string.

    Parses mismatch details from the reason string and compares the difference
    against the tolerance to determine severity.

    Args:
        reason (str): String describing the deviation (e.g., "Trust mismatch (... Diff: 0.1)").
        tolerance (float): The acceptable tolerance for floating-point comparisons.

    Returns:
        float: A severity score (e.g., 0.05 for non-commit, 0.1-0.7 for mismatches).
    """
    severity = 0.0
    max_deviation_factor = 0.0
    if "Did not commit" in reason:
        return 0.05
    parts = reason.split(";")
    for part in parts:
        part = part.strip()
        if "mismatch" in part:
            try:
                diff_str = part.split("Diff:")[-1].strip().rstrip(")")
                diff_float = float(diff_str)
                if tolerance > 1e-9:
                    deviation_factor = diff_float / tolerance
                    max_deviation_factor = max(max_deviation_factor, deviation_factor)
            except Exception:
                pass
    severe_threshold_factor = getattr(config, "CONSENSUS_SEVERITY_SEVERE_FACTOR", 10.0)
    moderate_threshold_factor = getattr(
        config, "CONSENSUS_SEVERITY_MODERATE_FACTOR", 3.0
    )
    if max_deviation_factor >= severe_threshold_factor:
        severity = 0.7
    elif max_deviation_factor >= moderate_threshold_factor:
        severity = 0.3
    else:
        severity = 0.1
    return severity


def run_consensus_logic(
    current_cycle: int,
    tasks_sent: Dict[str, TaskAssignment],
    received_scores: Dict[
        str, Dict[str, ValidatorScore]
    ],  # {task_id: {validator_uid_hex: ValidatorScore}}
    validators_info: Dict[
        str, ValidatorInfo
    ],  # {validator_uid_hex: ValidatorInfo} - State at the start of the cycle
    settings: Any,
    consensus_possible: bool,
    self_validator_uid: str,
) -> Tuple[Dict[str, float], Dict[str, Any]]:
    """
    Calculates consensus and penalties for a cycle based on scores from validators.
    Calculates P_adj, new trust scores, and incentives for miners.

    Args:
        current_cycle (int): The current consensus cycle number.
        tasks_sent (Dict[str, TaskAssignment]): Tasks sent to miners.
        received_scores (Dict[str, Dict[str, ValidatorScore]]): Scores from validators for tasks.
        validators_info (Dict[str, ValidatorInfo]): Information about all validators.
        settings (Any): Configuration settings.
        consensus_possible (bool): Whether enough data was available for consensus.
        self_validator_uid (str): UID of the validator running this calculation.

    Returns:
        Tuple[Dict[str, float], Dict[str, Any]]:
            - Final scores for miners (P_adj)
            - Internal state data for debugging/verification
    """
    logger.info(f":brain: Running consensus calculations for cycle {current_cycle}...")
    final_miner_scores: Dict[str, float] = {}  # {miner_uid_hex: P_adj}
    validator_deviations: Dict[str, List[float]] = defaultdict(
        list
    )  # {validator_uid_hex: [deviation1, deviation2,...]}
    calculated_validator_states: Dict[str, Any] = {}  # {validator_uid_hex: {state}}
    total_validator_contribution: float = 0.0  # Tổng W*E để tính thưởng validator
    if not consensus_possible:
        logger.warning(
            f":warning: Cycle {current_cycle}: Insufficient P2P scores received. Skipping detailed consensus. Applying only trust decay."
        )
        # Chỉ tính decay cho trust score, không tính P_adj, E_v, reward
        for validator_uid_hex, validator_info in validators_info.items():
            time_since_val_eval = 1  # Giả định 1 chu kỳ
            # Tính trust chỉ với decay (score_new = 0)
            new_val_trust_score = update_trust_score(
                validator_info.trust_score,
                time_since_val_eval,
                0.0,
                delta_trust=settings.CONSENSUS_PARAM_DELTA_TRUST,
                # Các tham số alpha, k_alpha, sigmoid không ảnh hưởng khi score_new=0
                alpha_base=settings.CONSENSUS_PARAM_ALPHA_BASE,
                k_alpha=settings.CONSENSUS_PARAM_K_ALPHA,
                update_sigmoid_L=settings.CONSENSUS_PARAM_UPDATE_SIG_L,
                update_sigmoid_k=settings.CONSENSUS_PARAM_UPDATE_SIG_K,
                update_sigmoid_x0=settings.CONSENSUS_PARAM_UPDATE_SIG_X0,
            )
            # Lưu trạng thái tối thiểu
            calculated_validator_states[validator_uid_hex] = {
                "E_v": getattr(validator_info, "last_performance", 0.0),  # Giữ E_v cũ
                "trust": new_val_trust_score,  # Chỉ có decay
                "reward": 0.0,  # Không có reward
                "weight": validator_info.weight,
                "contribution": 0.0,
                "last_update_cycle": current_cycle,
                "start_trust": validator_info.trust_score,
                "start_status": validator_info.status,
                "notes": "Consensus skipped due to insufficient scores.",
            }
            # final_miner_scores vẫn rỗng

        return (
            final_miner_scores,
            calculated_validator_states,
        )  # Trả về kết quả rỗng/chỉ decay

    # --- 1. Tính điểm đồng thuận Miner (P_miner_adjusted) và độ lệch ---
    scores_by_miner: Dict[str, List[Tuple[float, float]]] = defaultdict(
        list
    )  # {miner_uid_hex: [(score, validator_trust)]}
    tasks_processed_by_miner: Dict[str, Set[str]] = defaultdict(
        set
    )  # {miner_uid_hex: {task_id1, task_id2,...}}
    validator_scores_by_task: Dict[str, Dict[str, float]] = defaultdict(
        dict
    )  # {task_id: {validator_uid: score}}

    # Gom điểm theo miner VÀ theo task
    for task_id, validator_scores_dict in received_scores.items():
        first_score = next(iter(validator_scores_dict.values()), None)
        if not first_score:
            continue
        miner_uid_hex = first_score.miner_uid
        tasks_processed_by_miner[miner_uid_hex].add(
            task_id
        )  # Lưu tất cả task miner đã làm

        for validator_uid_hex, score_entry in validator_scores_dict.items():
            validator = validators_info.get(validator_uid_hex)
            if (
                validator
                and getattr(validator, "status", STATUS_ACTIVE) == STATUS_ACTIVE
            ):  # Chỉ tính điểm từ validator active
                # Lưu (điểm, trust của validator chấm điểm) cho miner
                scores_by_miner[miner_uid_hex].append(
                    (score_entry.score, validator.trust_score)
                )
                # Lưu điểm của validator cho task này
                validator_scores_by_task[task_id][validator_uid_hex] = score_entry.score
            # else: logger.warning(...) # Bỏ qua validator không tồn tại hoặc inactive

    # Tính P_adj và độ lệch
    for miner_uid_hex, scores_trusts in scores_by_miner.items():
        if not scores_trusts:
            continue
        scores = [s for s, t in scores_trusts]
        trusts = [t for s, t in scores_trusts]

        p_adj = calculate_adjusted_miner_performance(scores, trusts)
        final_miner_scores[miner_uid_hex] = p_adj
        logger.info(
            f"  :chart_with_upwards_trend: Consensus score (P_adj) for Miner [cyan]{miner_uid_hex}[/cyan]: [yellow]{p_adj:.4f}[/yellow]"
        )

        # Tính độ lệch cho từng validator đã chấm điểm miner này, trên từng task
        related_task_ids = tasks_processed_by_miner.get(miner_uid_hex, set())
        for task_id in related_task_ids:
            scores_for_this_task = validator_scores_by_task.get(task_id, {})
            for validator_uid_hex, score in scores_for_this_task.items():
                # Độ lệch = |điểm validator chấm - điểm đồng thuận của miner|
                deviation = abs(score - p_adj)
                validator_deviations[validator_uid_hex].append(deviation)
                logger.debug(
                    f"  Deviation for V:{validator_uid_hex} on M:{miner_uid_hex} (Task:{task_id}): {deviation:.4f}"
                )

    # --- 2. Tính E_validator, Trust mới dự kiến, và Đóng góp cho thưởng ---
    temp_validator_contributions: Dict[str, float] = {}

    # Cải thiện cách tính E_avg: Trung bình trọng số theo stake của các validator ACTIVE
    active_validators_info = {
        uid: v
        for uid, v in validators_info.items()
        if getattr(v, "status", STATUS_ACTIVE) == STATUS_ACTIVE
    }
    total_active_stake = sum(v.stake for v in active_validators_info.values())
    e_avg_weighted = 0.0
    if total_active_stake > EPSILON:
        # Tính E_v trung bình dựa trên trạng thái *đầu chu kỳ* (last_performance từ ValidatorInfo)
        valid_e_validators_for_avg = [
            (v.stake, getattr(v, "last_performance", 0.0))
            for v in active_validators_info.values()
        ]
        if valid_e_validators_for_avg:
            e_avg_weighted = (
                sum(stake * perf for stake, perf in valid_e_validators_for_avg)
                / total_active_stake
            )
    else:
        e_avg_weighted = 0.5  # Default nếu không có ai active hoặc stake=0

    logger.info(
        f"  Weighted E_avg (based on start-of-cycle active validator stake): {e_avg_weighted:.4f}"
    )

    # Tính toán cho từng validator (kể cả inactive/jailed để có trạng thái dự kiến nếu họ quay lại)
    for validator_uid_hex, validator_info in validators_info.items():
        deviations = validator_deviations.get(validator_uid_hex, [])
        avg_dev = sum(deviations) / len(deviations) if deviations else 0.0

        # Nếu validator không chấm điểm nào thì avg_dev = 0.
        # Cân nhắc: Có nên phạt validator không tham gia chấm điểm không? (Hiện tại thì không)
        logger.debug(
            f"  Validator {validator_uid_hex}: Average deviation = {avg_dev:.4f} ({len(deviations)} scores evaluated)"
        )

        # Metric Quality Placeholder
        # Giả định validator_info.performance_history chứa list điểm số float
        historical_scores = getattr(validator_info, "performance_history", [])
        # Cần lấy tham số max_stddev_penalty từ settings hoặc đặt mặc định
        max_penalty_for_consistency = getattr(
            config, "CONSENSUS_METRIC_MAX_STDDEV", 0.2
        )  # Ví dụ: ngưỡng 0.2
        metric_quality = calculate_historical_consistency(
            historical_scores, max_penalty_for_consistency
        )
        logger.debug(
            f"  Validator {validator_uid_hex}: Historical Consistency Metric = {metric_quality:.3f} (based on {len(historical_scores)} scores)"
        )

        # Kiểm tra xem UID của validator này có trong danh sách điểm miner cuối cùng không
        q_task_val = 0.0  # Mặc định là 0
        if (
            validator_uid_hex in final_miner_scores
        ):  # final_miner_scores đã được tính ở phần 1 của hàm
            q_task_val = final_miner_scores[validator_uid_hex]
            logger.debug(
                f"  Validator {validator_uid_hex} also acted as miner. Using P_adj={q_task_val:.4f} as Q_task_validator."
            )

        # Tính E_validator mới
        new_e_validator = calculate_validator_performance(
            q_task_validator=q_task_val,
            metric_validator_quality=metric_quality,
            deviation=avg_dev,  # Độ lệch trung bình của validator này
            theta1=settings.CONSENSUS_PARAM_THETA1,
            theta2=settings.CONSENSUS_PARAM_THETA2,
            theta3=settings.CONSENSUS_PARAM_THETA3,
            # Tham số Penalty Term lấy từ settings
            penalty_threshold_dev=settings.CONSENSUS_PARAM_PENALTY_THRESHOLD_DEV,
            penalty_k_penalty=settings.CONSENSUS_PARAM_PENALTY_K_PENALTY,
            penalty_p_penalty=settings.CONSENSUS_PARAM_PENALTY_P_PENALTY,
        )
        logger.info(
            f"  :chart_with_downwards_trend: Calculated performance (E_val) for Validator [cyan]{validator_uid_hex}[/cyan]: [yellow]{new_e_validator:.4f}[/yellow]"
        )

        # Tính Trust Score mới dự kiến
        # Nếu validator không hoạt động (inactive/jailed), chỉ áp dụng suy giảm
        time_since_val_eval = 1  # Mặc định là 1 chu kỳ
        score_for_trust_update = 0.0
        if getattr(validator_info, "status", STATUS_ACTIVE) == STATUS_ACTIVE:
            # Chỉ cập nhật trust dựa trên E_v mới nếu validator đang active
            score_for_trust_update = new_e_validator
        else:
            # Nếu không active, trust chỉ bị suy giảm (score_new = 0)
            # Có thể cần logic tính time_since phức tạp hơn nếu validator bị inactive/jailed lâu
            logger.debug(
                f"Validator {validator_uid_hex} is not active. Applying only trust decay."
            )

        new_val_trust_score = update_trust_score(
            validator_info.trust_score,  # Trust score đầu chu kỳ
            time_since_val_eval,
            score_for_trust_update,  # Dùng E_val mới tính nếu active, nếu không thì dùng 0
            delta_trust=settings.CONSENSUS_PARAM_DELTA_TRUST,
            alpha_base=settings.CONSENSUS_PARAM_ALPHA_BASE,
            k_alpha=settings.CONSENSUS_PARAM_K_ALPHA,
            update_sigmoid_L=settings.CONSENSUS_PARAM_UPDATE_SIG_L,
            update_sigmoid_k=settings.CONSENSUS_PARAM_UPDATE_SIG_K,
            update_sigmoid_x0=settings.CONSENSUS_PARAM_UPDATE_SIG_X0,
        )
        logger.info(
            f"  :sparkles: Calculated next Trust for Validator [cyan]{validator_uid_hex}[/cyan]: [yellow]{new_val_trust_score:.4f}[/yellow]"
        )

        # Tính đóng góp W*E cho việc tính thưởng (dùng weight đầu chu kỳ và E_v mới)
        current_weight = getattr(validator_info, "weight", 0.0)
        # Chỉ validator active mới đóng góp vào việc chia thưởng
        contribution = 0.0
        if getattr(validator_info, "status", STATUS_ACTIVE) == STATUS_ACTIVE:
            contribution = current_weight * new_e_validator
            temp_validator_contributions[validator_uid_hex] = contribution
            total_validator_contribution += contribution

        # Lưu trạng thái dự kiến (bao gồm cả E_v, trust cho validator inactive/jailed)
        calculated_validator_states[validator_uid_hex] = {
            "E_v": new_e_validator,
            "trust": new_val_trust_score,  # Trust dự kiến cuối chu kỳ
            "weight": current_weight,  # Weight đầu chu kỳ
            "contribution": contribution,  # Đóng góp W*E (chỉ > 0 nếu active)
            "last_update_cycle": current_cycle,
            # Lưu thêm trạng thái đầu vào để tiện debug/kiểm tra
            "avg_deviation": avg_dev,
            "metric_quality": metric_quality,
            "start_trust": validator_info.trust_score,
            "start_status": getattr(validator_info, "status", STATUS_ACTIVE),
        }

    # --- 3. Tính phần thưởng dự kiến cho từng validator (chỉ những ai active) ---
    logger.info(
        f":moneybag: Total validator contribution (Sum W*E from Active): [yellow]{total_validator_contribution:.4f}[/yellow]"
    )
    if total_validator_contribution > EPSILON:
        for validator_uid_hex, state in calculated_validator_states.items():
            # Chỉ tính thưởng cho validator active
            if state.get("start_status") == STATUS_ACTIVE:
                trust_for_reward = state["start_trust"]  # Dùng trust đầu chu kỳ
                reward = calculate_validator_incentive(
                    trust_score=trust_for_reward,
                    validator_weight=state["weight"],  # Weight đầu chu kỳ
                    validator_performance=state["E_v"],  # E_v mới tính
                    total_validator_value=total_validator_contribution,  # Tổng contribution của những người active
                    incentive_sigmoid_L=settings.CONSENSUS_PARAM_INCENTIVE_SIG_L,
                    incentive_sigmoid_k=settings.CONSENSUS_PARAM_INCENTIVE_SIG_K,
                    incentive_sigmoid_x0=settings.CONSENSUS_PARAM_INCENTIVE_SIG_X0,
                )
                state["reward"] = reward  # Thêm phần thưởng vào trạng thái dự kiến
                logger.info(
                    f"  :dollar: Validator [cyan]{validator_uid_hex}[/cyan]: Calculated Reward = [green]{reward:.6f}[/green]"
                )
            else:
                state["reward"] = 0.0  # Không có thưởng nếu không active
    else:
        logger.warning(
            ":warning: Total active validator contribution is zero. No validator rewards calculated."
        )
        for state in calculated_validator_states.values():
            state["reward"] = 0.0

    logger.info(
        ":brain: Finished consensus calculations and validator state estimation."
    )
    return final_miner_scores, calculated_validator_states


# --- Logic Kiểm tra và Phạt Validator ---


async def verify_and_penalize_logic(
    current_cycle: int,
    previous_calculated_states: Dict[str, Any],  # Expected state from cycle N-1
    validators_info: Dict[
        str, ValidatorInfo
    ],  # Current state (start of cycle N), MODIFIED IN-PLACE
    context: Web3,  # Changed from BlockFrostChainContext to RestClient
    settings: Any,
    contract_address: str,  # Changed from script_hash to contract_address
) -> None:
    """
    Verifies that validators correctly published their calculated states from the previous cycle.
    Penalizes validators who have incorrect or missing publications by reducing their trust score.
    In this implementation, we use Aptos instead of Cardano.

    Args:
        current_cycle (int): The current cycle number.
        previous_calculated_states (Dict[str, Any]): Expected states from cycle N-1.
        validators_info (Dict[str, ValidatorInfo]): Current validator state at the start of cycle N.
            This dictionary is MODIFIED IN-PLACE to update trust scores based on penalties.
        context (Web3): Aptos REST client.
        settings (Any): Configuration settings.
        contract_address (str): ModernTensor contract address.
    """
    logger.info(f"Verifying previous cycle ({current_cycle - 1}) validator updates...")
    previous_cycle = current_cycle - 1
    if previous_cycle < 0:
        return

    # Get tolerance settings
    tolerance = settings.CONSENSUS_DATUM_COMPARISON_TOLERANCE

    from ..core_client.contract_client import ModernTensorCoreClient

    # Create contract client
    contract_client = ModernTensorCoreClient(
        w3=context,
        contract_address=contract_address,
        account=None,  # No account needed for reading
    )

    try:
        # Get all validators from the blockchain
        all_validators = await contract_client.get_all_validators()
        logger.info(f"Found {len(all_validators)} validators on chain for verification")

        # Extract validators that were updated in the previous cycle
        on_chain_states = {}
        for uid_hex, validator_info in all_validators.items():
            # Check if this validator was updated in the previous cycle
            if (
                hasattr(validator_info, "last_update_cycle")
                and validator_info.last_update_cycle == previous_cycle
            ):
                on_chain_states[uid_hex] = {
                    "trust_score": validator_info.trust_score,
                    "last_performance": validator_info.last_performance,
                    "status": validator_info.status,
                }

        logger.info(
            f"Found {len(on_chain_states)} validators updated in cycle {previous_cycle}"
        )

        # Compare with expected states and identify suspicious validators
        expected_states = previous_calculated_states
        if not expected_states:
            logger.warning("No expected validator states found from previous cycle")
            return

        suspicious_validators = {}
        for uid_hex, expected in expected_states.items():
            actual = on_chain_states.get(uid_hex)
            reason_parts = []

            # Check if validator committed any updates
            if not actual:
                if expected.get("start_status") == STATUS_ACTIVE:
                    reason_parts.append(
                        f"Did not commit updates in cycle {previous_cycle}"
                    )
                if reason_parts:
                    suspicious_validators[uid_hex] = "; ".join(reason_parts)
                continue

            # Compare trust score
            expected_trust = expected.get("trust", -1.0)
            actual_trust = actual.get("trust_score", -999.0)
            if actual_trust == -999.0:
                reason_parts.append("Trust score missing in on-chain data")
            else:
                diff_trust = abs(actual_trust - expected_trust)
                if diff_trust > tolerance:
                    reason_parts.append(
                        f"Trust mismatch (Expected: {expected_trust:.5f}, Actual: {actual_trust:.5f}, Diff: {diff_trust:.5f})"
                    )

            # Compare performance score
            expected_perf = expected.get("E_v", -1.0)
            actual_perf = actual.get("last_performance", -999.0)
            if actual_perf == -999.0:
                reason_parts.append("Performance score missing in on-chain data")
            else:
                diff_perf = abs(actual_perf - expected_perf)
                if diff_perf > tolerance:
                    reason_parts.append(
                        f"Performance mismatch (Expected: {expected_perf:.5f}, Actual: {actual_perf:.5f}, Diff: {diff_perf:.5f})"
                    )

            if reason_parts:
                suspicious_validators[uid_hex] = "; ".join(reason_parts)
                logger.warning(
                    f"Deviation detected for Validator {uid_hex}: {suspicious_validators[uid_hex]}"
                )

        # Apply penalties for suspicious validators
        for uid_hex, reason in suspicious_validators.items():
            validator_info = validators_info.get(uid_hex)
            if not validator_info:
                logger.warning(
                    f"Info for suspicious validator {uid_hex} not found in current state"
                )
                continue

            logger.warning(f"Applying penalty to Validator {uid_hex} for: {reason}")

            # Determine severity of the deviation
            fraud_severity = _calculate_fraud_severity(reason, tolerance)

            # Calculate potential slash amount
            slash_amount = calculate_slash_amount(
                validator_info.stake,
                fraud_severity,
                settings.CONSENSUS_PARAM_MAX_SLASH_RATE,
            )
            if slash_amount > 0:
                logger.warning(
                    f"Potential slash for {uid_hex}: {slash_amount:.6f} (Severity: {fraud_severity:.2f})"
                )

            # Update trust score
            penalty_eta = settings.CONSENSUS_PARAM_PENALTY_ETA
            original_trust = validator_info.trust_score
            new_trust_score = max(
                0.0, original_trust * (1 - penalty_eta * fraud_severity)
            )

            if abs(new_trust_score - original_trust) > 1e-9:
                logger.warning(
                    f"Updating trust score for {uid_hex}: {original_trust:.4f} -> {new_trust_score:.4f}"
                )
                validator_info.trust_score = new_trust_score

            # Update status if needed
            jailed_threshold = getattr(
                config, "CONSENSUS_JAILED_SEVERITY_THRESHOLD", 0.2
            )
            if (
                fraud_severity >= jailed_threshold
                and validator_info.status == STATUS_ACTIVE
            ):
                logger.warning(
                    f"Changing status for {uid_hex} to JAILED due to severe deviation"
                )
                validator_info.status = STATUS_JAILED

    except Exception as e:
        logger.exception(f"Error during validator verification: {e}")

    return


# --- Logic Chuẩn bị và Commit Cập nhật ---


async def prepare_miner_updates_logic(
    current_cycle: int,
    miners_info: Dict[str, MinerInfo],  # Input miner state (start of cycle)
    final_scores: Dict[str, float],  # Adjusted performance scores (P_adj)
    settings: Any,
    client: Web3,  # Changed from context/UTxO to RestClient
    contract_address: str,  # Added contract address
) -> Dict[str, MinerData]:
    """
    Prepares miner state updates based on consensus scores.
    For each miner, calculates new trust score and creates updated datum.
    In this implementation, we use Aptos instead of Cardano.

    Args:
        current_cycle (int): Current consensus cycle number.
        miners_info (Dict[str, MinerInfo]): Current miner states at cycle start.
        final_scores (Dict[str, float]): Final consensus scores (P_adj) for miners.
        settings (Any): Configuration settings.
        client (Web3): Aptos REST client.
        contract_address (str): ModernTensor contract address.

    Returns:
        Dict[str, MinerData]: Dictionary of updated MinerData objects for miners.
    """
    logger.info(f"Preparing miner updates for cycle {current_cycle}")
    miner_updates = {}

    from ..core_client.contract_client import ModernTensorCoreClient

    # Create contract client
    contract_client = ModernTensorCoreClient(
        w3=client,
        contract_address=contract_address,
        account=None,  # No account needed for reading
    )

    # Track which miners were involved in this cycle
    scored_miners = set(final_scores.keys())
    all_miners = set(miners_info.keys())
    unscored_miners = all_miners - scored_miners

    # Update scored miners
    for miner_uid_hex, p_adj in final_scores.items():
        try:
            # Get current info if available
            if miner_uid_hex in miners_info:
                miner_info = miners_info[miner_uid_hex]
            else:
                # Try to fetch from blockchain if not in memory
                miner_info = await contract_client.get_miner_info(miner_uid_hex)
                if not miner_info:
                    logger.warning(f"Miner {miner_uid_hex} not found, skipping update")
                    continue

            # Calculate new trust score
            old_trust = miner_info.trust_score
            time_since_miner_eval = 1  # Assume 1 cycle since last evaluation

            # Get history or initialize empty
            performance_history = getattr(miner_info, "performance_history", [])

            # Add new score to history
            if len(performance_history) >= 10:  # Keep last 10 scores
                performance_history = performance_history[1:] + [p_adj]
            else:
                performance_history.append(p_adj)

            # Calculate trust score
            new_trust_score = update_trust_score(
                old_trust,
                time_since_miner_eval,
                p_adj,
                delta_trust=settings.CONSENSUS_PARAM_DELTA_TRUST,
                alpha_base=settings.CONSENSUS_PARAM_ALPHA_BASE,
                k_alpha=settings.CONSENSUS_PARAM_K_ALPHA,
                update_sigmoid_L=settings.CONSENSUS_PARAM_UPDATE_SIG_L,
                update_sigmoid_k=settings.CONSENSUS_PARAM_UPDATE_SIG_K,
                update_sigmoid_x0=settings.CONSENSUS_PARAM_UPDATE_SIG_X0,
            )

            # Create new datum
            new_datum = MinerData(
                miner_uid=miner_uid_hex,
                owner=miner_info.address,
                api_endpoint=miner_info.api_endpoint,
                trust_score=new_trust_score,
                performance_history=performance_history,
                status=miner_info.status,
                subnet_uid=miner_info.subnet_uid,
                weight=miner_info.weight,
                stake=miner_info.stake,
                registration_slot=miner_info.registration_slot,
            )

            # Submit transaction to update miner
            tx_hash = await contract_client.update_miner_info(
                miner_uid=miner_uid_hex,
                performance=p_adj,
                trust_score=new_trust_score,
            )

            if tx_hash:
                logger.info(f"Updated miner {miner_uid_hex} with tx {tx_hash}")

            # Add to updates
            miner_updates[miner_uid_hex] = new_datum

        except Exception as e:
            logger.error(f"Error preparing update for miner {miner_uid_hex}: {e}")

    # Handle unscored miners (apply trust decay only)
    for miner_uid_hex in unscored_miners:
        try:
            miner_info = miners_info[miner_uid_hex]

            # Apply trust decay
            old_trust = miner_info.trust_score
            time_since_miner_eval = 1  # Assume 1 cycle since last evaluation

            # Get decay rate from settings
            delta_trust = getattr(settings, "CONSENSUS_PARAM_DELTA_TRUST", 0.01)

            # Decay formula: trust = trust * (1 - delta)
            new_trust_score = old_trust * (1 - delta_trust)

            # Create new datum with trust decay
            new_datum = MinerData(
                miner_uid=miner_uid_hex,
                owner=miner_info.address,
                api_endpoint=miner_info.api_endpoint,
                trust_score=new_trust_score,
                performance_history=getattr(miner_info, "performance_history", []),
                status=miner_info.status,
                subnet_uid=miner_info.subnet_uid,
                weight=miner_info.weight,
                stake=miner_info.stake,
                registration_slot=miner_info.registration_slot,
            )

            # Add to updates (but don't submit to blockchain to save gas)
            miner_updates[miner_uid_hex] = new_datum

        except Exception as e:
            logger.error(f"Error applying trust decay for miner {miner_uid_hex}: {e}")

    return miner_updates


async def prepare_validator_updates_logic(
    current_cycle: int,
    self_validator_info: ValidatorInfo,
    calculated_states: Dict[str, Any],
    settings: Any,
    client: Optional[Web3],  # Changed from BlockFrostChainContext to RestClient
    contract_address: str = None,  # Added contract address
) -> Dict[str, ValidatorData]:
    """
    Prepares validator state updates for the current validator.
    In this implementation, we use Aptos instead of Cardano.

    Args:
        current_cycle (int): Current consensus cycle number.
        self_validator_info (ValidatorInfo): The validator's own info.
        calculated_states (Dict[str, Any]): Calculated states from consensus.
        settings (Any): Configuration settings.
        client (Optional[Web3]): Aptos REST client.
        contract_address (str): ModernTensor contract address.

    Returns:
        Dict[str, ValidatorData]: Dictionary of updated ValidatorData objects.
    """
    logger.info(f"Preparing validator updates for cycle {current_cycle}")
    validator_updates = {}
    self_uid_hex = self_validator_info.uid

    # Check if we have calculated state for this validator
    if self_uid_hex not in calculated_states:
        logger.warning(
            f"Calculated state for validator {self_uid_hex} not found, skipping update"
        )
        return {}

    from ..core_client.contract_client import ModernTensorCoreClient

    # Create contract client if client is provided
    contract_client = None
    if client and contract_address:
        contract_client = ModernTensorCoreClient(
            w3=client,
            contract_address=contract_address,
            account=None,  # No account needed for reading
        )

    # Get the calculated state
    state = calculated_states[self_uid_hex]

    # Get current performance and trust scores
    new_performance = state.get("E_v", 0.0)
    new_trust = state.get("trust", 0.0)

    # Get performance history or initialize
    performance_history = getattr(self_validator_info, "performance_history", [])

    # Add new performance to history
    if len(performance_history) >= 10:  # Keep last 10 scores
        performance_history = performance_history[1:] + [new_performance]
    else:
        performance_history.append(new_performance)

    # Create updated datum
    new_datum = ValidatorData(
        validator_uid=self_uid_hex,
        owner=self_validator_info.address,
        api_endpoint=self_validator_info.api_endpoint,
        last_performance=new_performance,
        trust_score=new_trust,
        performance_history=performance_history,
        status=self_validator_info.status,
        subnet_uid=getattr(self_validator_info, "subnet_uid", 0),
        weight=getattr(self_validator_info, "weight", 0.0),
        stake=getattr(self_validator_info, "stake", 0.0),
        registration_slot=getattr(self_validator_info, "registration_slot", 0),
    )

    validator_updates[self_uid_hex] = new_datum
    logger.info(
        f"Prepared update for validator {self_uid_hex}: performance={new_performance:.4f}, trust={new_trust:.4f}"
    )

    return validator_updates


async def commit_updates_logic(
    validator_updates: Dict[str, ValidatorData],  # Should contain only the self-update
    client: Web3,  # Changed from BlockFrostChainContext to RestClient
    account: Account,  # Changed from signing_key to account
    settings: Any,  # Full settings object
    contract_address: str,  # Changed from script_hash/bytes to contract_address
) -> Dict[str, Any]:
    """
    Commit validator updates to the blockchain.
    In this implementation, we use Aptos instead of Cardano.

    Args:
        validator_updates (Dict[str, ValidatorData]): Dictionary of validator datum to update (usually just self)
        client (Web3): Aptos REST client
        account (Account): Aptos account for signing transactions
        settings (Any): Full settings object
        contract_address (str): ModernTensor contract address on Aptos

    Returns:
        Dict[str, Any]: Transaction details
    """
    if not validator_updates:
        logger.info("No validator updates to commit.")
        return {"status": "skipped", "reason": "no_updates"}

    # Currently, we only expect a single self-update datum
    if len(validator_updates) > 1:
        logger.warning(
            f"Found {len(validator_updates)} validator updates, but we typically expect only one (self). "
            "Proceeding with all updates anyway."
        )

    tx_results = []

    from ..core_client.contract_client import ModernTensorCoreClient

    # Create contract client
    contract_client = ModernTensorCoreClient(
        w3=client,
        contract_address=contract_address,
        account=account,
    )

    # Process each validator update
    for validator_uid_hex, datum in validator_updates.items():
        try:
            logger.info(f"Committing update for validator {validator_uid_hex}...")

            # Extract performance and trust score from datum
            performance = datum.last_performance or 0.0
            trust_score = datum.trust_score or 0.0

            # Use the contract client to update validator
            tx_hash = await contract_client.update_validator_info(
                validator_uid=validator_uid_hex,
                performance=performance,
                trust_score=trust_score,
            )

            if tx_hash:
                logger.info(
                    f"Successfully updated validator {validator_uid_hex}, tx: {tx_hash}"
                )
                tx_results.append(
                    {
                        "validator_uid": validator_uid_hex,
                        "status": "success",
                        "tx_hash": tx_hash,
                    }
                )
            else:
                logger.error(f"Failed to update validator {validator_uid_hex}")
                tx_results.append(
                    {
                        "validator_uid": validator_uid_hex,
                        "status": "error",
                        "reason": "transaction_failed",
                    }
                )

        except Exception as e:
            logger.error(
                f"Error committing validator update for {validator_uid_hex}: {e}"
            )
            tx_results.append(
                {
                    "validator_uid": validator_uid_hex,
                    "status": "error",
                    "reason": str(e),
                }
            )

    # Return summary of all transactions
    return {
        "status": "completed",
        "transactions": tx_results,
    }

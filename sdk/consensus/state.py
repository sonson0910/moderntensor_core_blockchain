# sdk/consensus/state.py
"""
Logic tính toán đồng thuận, kiểm tra phạt, chuẩn bị và commit cập nhật trạng thái.
"""
import logging
import math
import asyncio
from typing import List, Dict, Any, Tuple, Optional, Set
from collections import defaultdict

from sdk.config.settings import settings
from sdk.core.datatypes import MinerInfo, ValidatorInfo, ValidatorScore
from sdk.formulas import (
    calculate_adjusted_miner_performance,
    calculate_validator_performance,
    update_trust_score,
    calculate_fraud_severity_value, # Cần logic cụ thể
    calculate_slash_amount,
    calculate_miner_weight,
    calculate_miner_incentive
    # Import các công thức khác nếu cần
)
from sdk.metagraph import metagraph_data, update_metagraph
from sdk.metagraph.metagraph_datum import MinerDatum, ValidatorDatum
# from sdk.metagraph.hash import hash_data # Cần hàm hash
def hash_data(data): return f"hashed_{str(data)[:10]}" # Mock hash
from pycardano import BlockFrostChainContext, PaymentSigningKey, StakeSigningKey, TransactionId, Network
from sdk.metagraph.metagraph_datum import MinerDatum, ValidatorDatum, STATUS_ACTIVE, STATUS_JAILED, STATUS_INACTIVE


logger = logging.getLogger(__name__)

# --- Logic Đồng thuận và Tính toán Trạng thái Validator ---

def run_consensus_logic(
    current_cycle: int,
    tasks_sent: Dict[str, Any], # Cần TaskAssignment type
    received_scores: Dict[str, Dict[str, ValidatorScore]], # {task_id: {validator_uid: ValidatorScore}}
    validators_info: Dict[str, ValidatorInfo],
    settings: Any # Đối tượng settings
) -> Tuple[Dict[str, float], Dict[str, Any]]:
    """
    Thực hiện đồng thuận điểm miners và tính toán trạng thái dự kiến cho validators.

    Args:
        current_cycle: Chu kỳ hiện tại.
        tasks_sent: Dict các task đã gửi trong chu kỳ này.
        received_scores: Dict điểm số nhận được từ các validator khác cho chu kỳ này.
        validators_info: Thông tin của tất cả validators đã biết.
        settings: Đối tượng cấu hình.

    Returns:
        Tuple gồm:
        - final_miner_scores: Dict {miner_uid: P_adj} điểm đồng thuận cho miner.
        - calculated_validator_states: Dict {validator_uid: {"E_v": float, "trust": float, ...}} trạng thái dự kiến.
    """
    logger.info(f"Running consensus calculations for cycle {current_cycle}...")
    final_miner_scores: Dict[str, float] = {}
    validator_avg_deviations: Dict[str, float] = defaultdict(float)
    validator_deviation_counts: Dict[str, int] = defaultdict(int)
    calculated_validator_states: Dict[str, Any] = {}

    # 1. Tính điểm đồng thuận Miner (P_adj)
    scores_by_miner: Dict[str, List[Tuple[float, float]]] = defaultdict(list)
    tasks_processed_by_miner: Dict[str, str] = {}

    for task_id, validator_scores_dict in received_scores.items():
        assignment = tasks_sent.get(task_id)
        if not assignment: continue # Bỏ qua nếu không phải task mình gửi? Hoặc xử lý khác?

        miner_uid = assignment.miner_uid
        tasks_processed_by_miner[miner_uid] = task_id

        for validator_uid, score_entry in validator_scores_dict.items():
            validator = validators_info.get(validator_uid)
            if validator:
                scores_by_miner[miner_uid].append((score_entry.score, validator.trust_score))

    for miner_uid, scores_trusts in scores_by_miner.items():
        if not scores_trusts: continue
        scores = [s for s, t in scores_trusts]
        trusts = [t for s, t in scores_trusts]
        p_adj = calculate_adjusted_miner_performance(scores, trusts)
        final_miner_scores[miner_uid] = p_adj
        logger.info(f"  Consensus score (P_adj) for Miner {miner_uid}: {p_adj:.3f}")

        # 2. Tính độ lệch cho từng validator đã chấm điểm miner này
        task_id = tasks_processed_by_miner.get(miner_uid)
        if not task_id: continue
        for validator_uid, score_entry in received_scores.get(task_id, {}).items():
             if score_entry.miner_uid == miner_uid:
                 deviation = abs(score_entry.score - p_adj)
                 validator_avg_deviations[validator_uid] += deviation
                 validator_deviation_counts[validator_uid] += 1

    # Hoàn tất tính độ lệch trung bình
    for val_uid in validator_avg_deviations:
        count = validator_deviation_counts[val_uid]
        if count > 0:
            validator_avg_deviations[val_uid] /= count
            logger.debug(f"  Validator {val_uid} average deviation: {validator_avg_deviations[val_uid]:.4f}")

    # 3. Tính E_validator và Trust mới dự kiến cho tất cả Validators
    for validator_uid, validator_info in validators_info.items():
        avg_dev = validator_avg_deviations.get(validator_uid, 0.0) # Nếu validator không chấm điểm nào, độ lệch = 0

        # TODO: Triển khai logic tính Metric_Validator_Quality thực tế
        metric_quality_example = max(0.0, 1.0 - avg_dev * 1.5)
        # TODO: Lấy Q_task của validator nếu có
        q_task_val_example = 0.0

        new_e_validator = calculate_validator_performance(
            q_task_validator=q_task_val_example,
            metric_validator_quality=metric_quality_example,
            deviation=avg_dev, # TODO: Cần chuẩn hóa độ lệch này không?
            theta1=settings.CONSENSUS_PARAM_THETA1,
            theta2=settings.CONSENSUS_PARAM_THETA2,
            theta3=settings.CONSENSUS_PARAM_THETA3,
            penalty_threshold_dev=settings.CONSENSUS_PARAM_PENALTY_THRESHOLD_DEV,
            penalty_k_penalty=settings.CONSENSUS_PARAM_PENALTY_K_PENALTY,
            penalty_p_penalty=settings.CONSENSUS_PARAM_PENALTY_P_PENALTY
        )
        logger.info(f"  Calculated performance (E_val) for Validator {validator_uid}: {new_e_validator:.3f}")

        # Tính Trust Score mới dự kiến (không áp dụng phạt ở đây)
        time_since_val_eval = 1 # Giả định đánh giá mỗi chu kỳ
        new_val_trust_score = update_trust_score(
             validator_info.trust_score, time_since_val_eval, new_e_validator,
             delta_trust=settings.CONSENSUS_PARAM_DELTA_TRUST,
             alpha_base=settings.CONSENSUS_PARAM_ALPHA_BASE,
             k_alpha=settings.CONSENSUS_PARAM_K_ALPHA,
             update_sigmoid_L=settings.CONSENSUS_PARAM_UPDATE_SIG_L,
             update_sigmoid_k=settings.CONSENSUS_PARAM_UPDATE_SIG_K,
             update_sigmoid_x0=settings.CONSENSUS_PARAM_UPDATE_SIG_X0
        )
        logger.info(f"  Calculated next Trust for Validator {validator_uid}: {new_val_trust_score:.3f}")

        # TODO: Tính Weight mới cho Validator nếu cần lưu trữ
        # new_val_weight = calculate_validator_weight(...)

        calculated_validator_states[validator_uid] = {
            "E_v": new_e_validator,
            "trust": new_val_trust_score,
            # "weight": new_val_weight,
            "last_update_cycle": current_cycle
        }

    return final_miner_scores, calculated_validator_states

# --- Logic Kiểm tra và Phạt Validator ---

async def verify_and_penalize_logic(
    current_cycle: int,
    previous_calculated_states: Dict[str, Any],
    validators_info: Dict[str, ValidatorInfo], # Trạng thái hiện tại (đã load)
    context: BlockFrostChainContext,
    settings: Any,
    # Thêm các tham số cần thiết khác: signing_key, cơ chế đồng thuận P2P,...
):
    """
    Logic kiểm tra ValidatorDatum đã commit ở chu kỳ trước và áp dụng phạt.
    *** Cần triển khai chi tiết logic đồng thuận P2P về gian lận và trigger slashing ***
    """
    logger.info(f"Verifying previous cycle ({current_cycle - 1}) validator updates...")
    previous_cycle = current_cycle - 1
    if previous_cycle < 0: return # Bỏ qua chu kỳ đầu

    penalized_validators_updates: Dict[str, ValidatorDatum] = {} # Lưu datum mới cho validator bị phạt

    try:
        # 1. Lấy dữ liệu on-chain
        # TODO: Triển khai logic gọi metagraph_data hiệu quả hơn để lấy datum chu kỳ trước
        logger.debug("Fetching on-chain validator data for previous cycle...")
        all_validator_datums: List[ValidatorDatum] = await metagraph_data.get_all_validator_data(context, settings.SCRIPT_HASH, settings.CARDANO_NETWORK) # Giả sử hàm nhận script_hash
        on_chain_states = {
             datum.uid.hex(): { # Giả sử uid là bytes
                 "trust_score": getattr(datum, 'trust_score', 0.0), # Dùng property
                 "last_update_cycle": getattr(datum, 'last_update_slot', -1)
                 # Thêm các trường khác cần kiểm tra
             } for datum in all_validator_datums if getattr(datum, 'last_update_slot', -1) == previous_cycle
        }
        logger.info(f"Fetched {len(on_chain_states)} validator datums updated in cycle {previous_cycle}.")

        # 2. So sánh với trạng thái dự kiến đã lưu
        expected_states = previous_calculated_states
        if not expected_states: logger.warning("No expected validator states found from previous cycle."); return

        suspicious_validators: Dict[str, str] = {}
        tolerance = settings.CONSENSUS_DATUM_COMPARISON_TOLERANCE
        for uid_hex, expected in expected_states.items():
            actual = on_chain_states.get(uid_hex)
            if not actual: logger.warning(f"Validator {uid_hex} did not commit updates in cycle {previous_cycle}."); continue

            diff_trust = abs(actual.get("trust_score", -1) - expected.get("trust", -1))
            if diff_trust > tolerance:
                reason = f"Trust mismatch (Expected: {expected.get('trust', -1):.5f}, Actual: {actual.get('trust_score', -1):.5f})"
                suspicious_validators[uid_hex] = reason
                logger.warning(f"Potential fraud detected for Validator {uid_hex}: {reason}")
            # TODO: Thêm kiểm tra cho các trường khác (ví dụ: weight, E_v nếu lưu)

        # 3. Đồng thuận về Gian lận (Placeholder)
        confirmed_cheaters: Dict[str, str] = {}
        if suspicious_validators:
            logger.info(f"Requesting consensus on {len(suspicious_validators)} suspicious validators...")
            # TODO: Triển khai logic P2P để đồng thuận.
            # confirmed_cheaters = await request_fraud_consensus(suspicious_validators)
            confirmed_cheaters = suspicious_validators # Giả lập
            logger.warning(f"Fraud confirmed (mock): {list(confirmed_cheaters.keys())}")

        # 4. Áp dụng Trừng phạt
        for uid_hex, reason in confirmed_cheaters.items():
            validator_info = validators_info.get(uid_hex) # Lấy thông tin mới nhất từ dict hiện tại
            if not validator_info: logger.warning(f"Info for penalized validator {uid_hex} not found."); continue

            logger.warning(f"Applying penalty to Validator {uid_hex} for: {reason}")
            # TODO: Xác định fraud_severity dựa trên loại gian lận
            fraud_severity = 0.8 # Giả định Bậc 3 cho Datum Manipulation

            slash_amount = calculate_slash_amount(validator_info.stake, fraud_severity, settings.CONSENSUS_PARAM_MAX_SLASH_RATE)
            logger.warning(f"Calculated slash amount for {uid_hex}: {slash_amount}")
            # TODO: Kích hoạt cơ chế Slashing thực tế (Smart Contract call?)
            # success_slash = await trigger_slashing(context, signing_key, uid_hex, slash_amount)

            # Phạt Trust Score và cập nhật trạng thái local ngay lập tức
            new_trust_score = validator_info.trust_score * (1 - settings.CONSENSUS_PARAM_PENALTY_ETA)
            logger.warning(f"Penalizing Trust Score for {uid_hex}: {validator_info.trust_score:.3f} -> {new_trust_score:.3f}")
            validator_info.trust_score = new_trust_score # Cập nhật ngay lập tức
            validator_info.status = STATUS_JAILED # Cập nhật trạng thái nếu cần

            # TODO: Chuẩn bị ValidatorDatum mới để commit hình phạt
            # Cần lấy UTXO và Datum cũ của validator bị phạt
            # old_datum = ...
            # new_penalty_datum = ValidatorDatum(..., trust_score=int(new_trust_score*1e6), status=STATUS_JAILED, last_update_cycle=current_cycle)
            # penalized_validators_updates[uid_hex] = new_penalty_datum

    except Exception as e:
        logger.exception(f"Error during validator verification/penalization: {e}")

    # Trả về dict các datum cần cập nhật do phạt (có thể rỗng)
    return penalized_validators_updates


# --- Logic Chuẩn bị và Commit Cập nhật ---

def prepare_miner_updates_logic(
    current_cycle: int,
    miners_info: Dict[str, MinerInfo], # Trạng thái miner đã được cập nhật trust/weight local
    final_scores: Dict[str, float], # Điểm P_adj
    settings: Any
) -> Dict[str, MinerDatum]:
    """Chuẩn bị dữ liệu MinerDatum mới để commit."""
    logger.info(f"Preparing miner state updates for cycle {current_cycle}...")
    miner_updates: Dict[str, MinerDatum] = {}
    total_system_value_example = 50.0 # TODO: Cần giá trị thực tế

    for miner_uid_hex, miner_info in miners_info.items():
        score_new = final_scores.get(miner_uid_hex, 0.0)

        # Tính Incentive (dùng trust/weight đã cập nhật?) -> Cần quyết định rõ ràng
        incentive = calculate_miner_incentive(
            trust_score=miner_info.trust_score,
            miner_weight=miner_info.weight,
            miner_performance_scores=[score_new],
            total_system_value=total_system_value_example,
            incentive_sigmoid_L=settings.CONSENSUS_PARAM_INCENTIVE_SIG_L,
            incentive_sigmoid_k=settings.CONSENSUS_PARAM_INCENTIVE_SIG_K,
            incentive_sigmoid_x0=settings.CONSENSUS_PARAM_INCENTIVE_SIG_X0
        )
        reward_to_add = incentive
        logger.debug(f"  Miner {miner_uid_hex}: Incentive={incentive:.4f}")

        # TODO: Lấy Datum cũ để cộng dồn thưởng
        # old_datum = await metagraph_data.get_miner_datum(context, miner_uid_hex)
        pending_rewards_old = 0 # Giả định

        # TODO: Hash lịch sử hiệu suất
        # perf_history_hash = hash_data(miner_info.performance_history) if miner_info.performance_history else None
        perf_history_hash = None

        # TODO: Hash địa chỉ ví
        # wallet_addr_hash = hash_data(miner_info.address) # Hoặc lấy từ datum cũ
        wallet_addr_hash = b'wallet_hash_placeholder'

        # Tạo MinerDatum mới
        try:
            new_datum = MinerDatum(
                uid=bytes.fromhex(miner_uid_hex), # Chuyển hex về bytes
                subnet_uid=miner_info.subnet_uid,
                stake=int(miner_info.stake), # Đảm bảo là int
                scaled_last_performance=int(score_new * settings.METAGRAPH_DATUM_INT_DIVISOR),
                scaled_trust_score=int(miner_info.trust_score * settings.METAGRAPH_DATUM_INT_DIVISOR),
                accumulated_rewards = pending_rewards_old + int(reward_to_add * settings.METAGRAPH_DATUM_INT_DIVISOR),
                last_update_slot=current_cycle, # Hoặc slot thực tế?
                performance_history_hash=perf_history_hash,
                wallet_addr_hash=wallet_addr_hash,
                status=getattr(miner_info, 'status', STATUS_ACTIVE), # Lấy status hiện tại
                registration_slot=getattr(miner_info, 'registration_slot', 0), # Lấy từ info
                api_endpoint=miner_info.api_endpoint.encode('utf-8') if miner_info.api_endpoint else None,
                version=getattr(miner_info, 'version', 1) # Lấy version hiện tại
            )
            miner_updates[miner_uid_hex] = new_datum
        except Exception as e:
            logger.error(f"Failed to create MinerDatum for {miner_uid_hex}: {e}")

    logger.info(f"Prepared {len(miner_updates)} miner datums for update.")
    return miner_updates

async def prepare_validator_updates_logic( # <<<--- Chuyển thành async vì cần lấy datum cũ
    current_cycle: int,
    self_validator_info: ValidatorInfo, # <<<--- Nhận thông tin validator hiện tại
    calculated_states: Dict[str, Any], # Trạng thái validator dự kiến đã tính (bao gồm cả reward)
    settings: Any,
    context: BlockFrostChainContext # <<<--- Thêm context
) -> Dict[str, ValidatorDatum]:
    """Chuẩn bị dữ liệu ValidatorDatum mới cho chính validator này."""
    logger.info(f"Preparing self validator state update for cycle {current_cycle}...")
    validator_updates: Dict[str, ValidatorDatum] = {}
    self_uid_hex = self_validator_info.uid # Lấy UID hex từ info object

    if self_uid_hex in calculated_states:
        state = calculated_states[self_uid_hex]
        old_datum: Optional[ValidatorDatum] = None
        pending_rewards_old = 0
        wallet_addr_hash_old = b'default_wallet_hash_placeholder' # Giá trị mặc định
        perf_history_hash_old = None
        registration_slot_old = 0
        subnet_uid_old = 0
        stake_old = 0
        status_old = STATUS_ACTIVE
        version_old = 0
        api_endpoint_old = None


        # TODO: Triển khai logic lấy Datum cũ của chính mình bằng context và self_uid_hex
        try:
            # Giả sử có hàm get_validator_datum hoặc cách tìm UTXO + decode datum
            # validator_utxo = await metagraph_data.find_validator_utxo(context, self_uid_hex)
            # if validator_utxo and validator_utxo.output.datum:
            #     old_datum = ValidatorDatum.from_cbor(validator_utxo.output.datum.cbor)
            #     pending_rewards_old = getattr(old_datum, 'accumulated_rewards', 0)
            #     wallet_addr_hash_old = getattr(old_datum, 'wallet_addr_hash', wallet_addr_hash_old)
            #     perf_history_hash_old = getattr(old_datum, 'performance_history_hash', None)
            #     registration_slot_old = getattr(old_datum, 'registration_slot', 0)
            #     subnet_uid_old = getattr(old_datum, 'subnet_uid', 0)
            #     stake_old = getattr(old_datum, 'stake', 0) # Lấy stake từ datum cũ hay từ info mới nhất? -> Nên từ info
            #     status_old = getattr(old_datum, 'status', STATUS_ACTIVE)
            #     version_old = getattr(old_datum, 'version', 0)
            #     api_endpoint_old = getattr(old_datum, 'api_endpoint', None)

            logger.debug(f"Successfully fetched old datum for self ({self_uid_hex}). Old rewards: {pending_rewards_old}")
            # Lấy các giá trị không đổi từ self_validator_info (đã được load mới nhất)
            stake_current = int(self_validator_info.stake)
            subnet_uid_current = self_validator_info.subnet_uid
            registration_slot_current = getattr(self_validator_info, 'registration_slot', registration_slot_old) # Giữ slot gốc
            wallet_addr_hash_current = wallet_addr_hash_old # Giả sử hash ví không đổi, hoặc lấy từ info nếu có
            api_endpoint_current = self_validator_info.api_endpoint
            status_current = getattr(self_validator_info, 'status', status_old) # Lấy status hiện tại (có thể đã bị phạt)
            version_current = max(1, getattr(self_validator_info, 'version', version_old)) # Lấy version hiện tại

        except Exception as e:
            logger.warning(f"Could not fetch or parse old datum for self ({self_uid_hex}): {e}. Using defaults/current info.")
            # Sử dụng giá trị từ self_validator_info nếu không lấy được datum cũ
            stake_current = int(self_validator_info.stake)
            subnet_uid_current = self_validator_info.subnet_uid
            registration_slot_current = getattr(self_validator_info, 'registration_slot', 0)
            wallet_addr_hash_current = hash_data(self_validator_info.address) # Hash lại nếu ko có datum cũ
            api_endpoint_current = self_validator_info.api_endpoint
            status_current = getattr(self_validator_info, 'status', STATUS_ACTIVE)
            version_current = getattr(self_validator_info, 'version', 1)


        # TODO: Hash lịch sử hiệu suất mới nếu cần lưu
        # new_perf_history = ...
        # perf_history_hash = hash_data(new_perf_history) if new_perf_history else perf_history_hash_old
        perf_history_hash = perf_history_hash_old # Tạm thời giữ hash cũ

        # Tính phần thưởng mới tích lũy
        calculated_reward = state.get("reward", 0.0)
        accumulated_rewards_new = pending_rewards_old + int(calculated_reward * settings.METAGRAPH_DATUM_INT_DIVISOR)

        # Tạo ValidatorDatum mới
        try:
            new_datum = ValidatorDatum(
                uid=bytes.fromhex(self_uid_hex),
                subnet_uid=subnet_uid_current,
                stake=stake_current,
                scaled_last_performance=int(state.get("E_v", 0.0) * settings.METAGRAPH_DATUM_INT_DIVISOR),
                scaled_trust_score=int(state.get("trust", 0.0) * settings.METAGRAPH_DATUM_INT_DIVISOR),
                accumulated_rewards=accumulated_rewards_new,
                last_update_slot=current_cycle, # Ghi lại chu kỳ hiện tại
                performance_history_hash=perf_history_hash,
                wallet_addr_hash=wallet_addr_hash_current,
                status=status_current,
                registration_slot=registration_slot_current,
                api_endpoint=api_endpoint_current.encode('utf-8') if api_endpoint_current else None,
                version=version_current # Có thể tăng version nếu cấu trúc thay đổi
            )
            validator_updates[self_uid_hex] = new_datum
            logger.info(f"Prepared update for self ({self_uid_hex})")
        except Exception as e:
            logger.exception(f"Failed to create ValidatorDatum for self ({self_uid_hex}): {e}")

    return validator_updates


async def commit_updates_logic(
    miner_updates: Dict[str, MinerDatum],
    validator_updates: Dict[str, ValidatorDatum],
    context: BlockFrostChainContext,
    signing_key: PaymentSigningKey,
    stake_signing_key: Optional[StakeSigningKey],
    settings: Any
):
    """Gửi giao dịch cập nhật Datum lên blockchain (async)."""
    logger.info("Attempting to commit updates to blockchain...")
    # TODO: Triển khai logic thực tế:
    # 1. Gom các cập nhật thành các giao dịch (có thể 1 tx cho nhiều update).
    # 2. Với mỗi giao dịch:
    #    a. Tìm UTXO input cho từng datum cần cập nhật (miner/validator).
    #    b. Tạo TransactionBuilder.
    #    c. Add input UTXO với script và Redeemer phù hợp.
    #    d. Add output mới với Datum mới tại cùng địa chỉ script.
    #    e. Add input từ ví validator để trả phí (+ collateral).
    #    f. Add change output về ví validator.
    #    g. Build, sign (dùng signing_key, stake_signing_key), submit (dùng context).
    #    h. Xử lý kết quả, log lỗi/thành công.

    logger.info(f"  (Mock) Preparing to commit {len(miner_updates)} Miner datums.")
    await asyncio.sleep(0.1)
    logger.info(f"  (Mock) Preparing to commit {len(validator_updates)} Validator datums.")
    await asyncio.sleep(0.1)
    logger.info("  (Mock) Datum update transactions supposedly sent.")
    # Trả về kết quả commit nếu cần (ví dụ: list các tx_id)


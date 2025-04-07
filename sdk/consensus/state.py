# sdk/consensus/state.py
"""
Logic tính toán đồng thuận, kiểm tra phạt, chuẩn bị và commit cập nhật trạng thái.
"""
import logging
import math
import asyncio
from typing import List, Dict, Any, Tuple, Optional, Set, Union
from collections import defaultdict

from sdk.config.settings import settings
from sdk.core.datatypes import MinerInfo, ValidatorInfo, ValidatorScore, TaskAssignment
from sdk.formulas import (
    calculate_adjusted_miner_performance,
    calculate_validator_performance,
    update_trust_score,
    calculate_fraud_severity_value, # Cần logic cụ thể
    calculate_slash_amount,
    calculate_miner_weight,
    calculate_miner_incentive,
    calculate_validator_incentive
    # Import các công thức khác nếu cần
)
from sdk.metagraph import metagraph_data, update_datum
from sdk.metagraph.metagraph_datum import MinerDatum, ValidatorDatum
from sdk.metagraph.metagraph_data import get_all_validator_data
# from sdk.metagraph.hash import hash_data # Cần hàm hash
def hash_data(data): return f"hashed_{str(data)[:10]}" # Mock hash
from pycardano import BlockFrostChainContext, PaymentSigningKey, StakeSigningKey, TransactionId, Network, ScriptHash, UTxO, Address, PlutusV3Script, Redeemer, InvalidTransaction, VerificationKeyHash
from sdk.metagraph.metagraph_datum import MinerDatum, ValidatorDatum, STATUS_ACTIVE, STATUS_JAILED, STATUS_INACTIVE

EPSILON=1e-9

logger = logging.getLogger(__name__)

# --- Logic Đồng thuận và Tính toán Trạng thái Validator ---

# --- Placeholder Function: Tìm UTXO theo UID ---
# Cần thay thế bằng logic thực tế, có thể cần sửa đổi get_all_miner/validator_data
async def find_utxo_by_uid(
    context: BlockFrostChainContext,
    script_hash: ScriptHash,
    network: Network,
    uid_bytes: bytes,
    datum_class: type # MinerDatum hoặc ValidatorDatum
) -> Optional[UTxO]:
    """
    (Placeholder/Mock) Tìm UTXO tại địa chỉ script chứa Datum có UID khớp.
    Trong thực tế, nên tối ưu hóa việc này.
    """
    logger.debug(f"Searching for UTxO with UID {uid_bytes.hex()} of type {datum_class.__name__}...")
    contract_address = Address(payment_part=script_hash, network=network)
    try:
        # TODO: Tối ưu hóa: chỉ fetch UTXO liên quan nếu có thể
        # Tạm thời fetch hết và lọc
        utxos = await context.utxos(str(contract_address))
        for utxo in utxos:
            if utxo.output.datum:
                try:
                    decoded_datum = datum_class.from_cbor(utxo.output.datum.cbor)
                    if hasattr(decoded_datum, 'uid') and getattr(decoded_datum, 'uid') == uid_bytes:
                        logger.debug(f"Found matching UTxO: {utxo.input}")
                        return utxo
                except Exception:
                    # logger.warning(f"Failed to decode datum for {utxo.input} as {datum_class.__name__}")
                    continue # Bỏ qua datum không decode được hoặc sai loại
    except Exception as e:
        logger.error(f"Failed to fetch UTxOs for {contract_address} while searching for UID {uid_bytes.hex()}: {e}")

    logger.warning(f"UTxO for UID {uid_bytes.hex()} of type {datum_class.__name__} not found.")
    return None
# -----------------------------------------

# --- Helper Function (Ví dụ đơn giản cho severity) ---
def _calculate_simple_fraud_severity(reason: str) -> float:
    """Xác định mức độ nghiêm trọng dựa trên lý do (ví dụ đơn giản)."""
    if "Trust mismatch" in reason:
        # Có thể phân tích độ lệch để quyết định bậc 1, 2, 3
        # Ví dụ: Độ lệch lớn (> 0.1) -> Bậc 2
        try:
             parts = reason.split(',')
             expected_str = parts[0].split(':')[-1].strip()
             actual_str = parts[1].split(':')[-1].strip().rstrip(')')
             deviation = abs(float(actual_str) - float(expected_str))
             if deviation > 0.1: return 0.3 # Moderate
             else: return 0.1 # Minor
        except:
             return 0.1 # Default Minor nếu parse lỗi
    elif "Did not commit" in reason:
         return 0.1 # Minor (có thể do lỗi mạng?)
    # Thêm các loại gian lận khác
    else:
        return 0.05 # Rất nhỏ cho các trường hợp không rõ

def run_consensus_logic(
    current_cycle: int,
    tasks_sent: Dict[str, TaskAssignment],
    received_scores: Dict[str, Dict[str, ValidatorScore]], # {task_id: {validator_uid_hex: ValidatorScore}}
    validators_info: Dict[str, ValidatorInfo], # {validator_uid_hex: ValidatorInfo} - Trạng thái đầu chu kỳ
    settings: Any
) -> Tuple[Dict[str, float], Dict[str, Any]]:
    """
    Thực hiện đồng thuận điểm miners, tính toán trạng thái dự kiến VÀ phần thưởng dự kiến cho validators.
    """
    logger.info(f"Running consensus calculations for cycle {current_cycle}...")
    final_miner_scores: Dict[str, float] = {} # {miner_uid_hex: P_adj}
    validator_deviations: Dict[str, List[float]] = defaultdict(list) # {validator_uid_hex: [deviation1, deviation2,...]}
    calculated_validator_states: Dict[str, Any] = {} # {validator_uid_hex: {state}}
    total_validator_contribution: float = 0.0 # Tổng W*E để tính thưởng validator

    # --- 1. Tính điểm đồng thuận Miner (P_miner_adjusted) và độ lệch ---
    scores_by_miner: Dict[str, List[Tuple[float, float]]] = defaultdict(list) # {miner_uid_hex: [(score, validator_trust)]}
    tasks_processed_by_miner: Dict[str, Set[str]] = defaultdict(set) # {miner_uid_hex: {task_id1, task_id2,...}}
    validator_scores_by_task: Dict[str, Dict[str, float]] = defaultdict(dict) # {task_id: {validator_uid: score}}

    # Gom điểm theo miner VÀ theo task
    for task_id, validator_scores_dict in received_scores.items():
        first_score = next(iter(validator_scores_dict.values()), None)
        if not first_score: continue
        miner_uid_hex = first_score.miner_uid
        tasks_processed_by_miner[miner_uid_hex].add(task_id) # Lưu tất cả task miner đã làm

        for validator_uid_hex, score_entry in validator_scores_dict.items():
            validator = validators_info.get(validator_uid_hex)
            if validator and getattr(validator, 'status', STATUS_ACTIVE) == STATUS_ACTIVE: # Chỉ tính điểm từ validator active
                # Lưu (điểm, trust của validator chấm điểm) cho miner
                scores_by_miner[miner_uid_hex].append((score_entry.score, validator.trust_score))
                # Lưu điểm của validator cho task này
                validator_scores_by_task[task_id][validator_uid_hex] = score_entry.score
            # else: logger.warning(...) # Bỏ qua validator không tồn tại hoặc inactive

    # Tính P_adj và độ lệch
    for miner_uid_hex, scores_trusts in scores_by_miner.items():
        if not scores_trusts: continue
        scores = [s for s, t in scores_trusts]
        trusts = [t for s, t in scores_trusts]

        p_adj = calculate_adjusted_miner_performance(scores, trusts)
        final_miner_scores[miner_uid_hex] = p_adj
        logger.info(f"  Consensus score (P_adj) for Miner {miner_uid_hex}: {p_adj:.4f}")

        # Tính độ lệch cho từng validator đã chấm điểm miner này, trên từng task
        related_task_ids = tasks_processed_by_miner.get(miner_uid_hex, set())
        for task_id in related_task_ids:
            scores_for_this_task = validator_scores_by_task.get(task_id, {})
            for validator_uid_hex, score in scores_for_this_task.items():
                 # Độ lệch = |điểm validator chấm - điểm đồng thuận của miner|
                 deviation = abs(score - p_adj)
                 validator_deviations[validator_uid_hex].append(deviation)
                 logger.debug(f"  Deviation for V:{validator_uid_hex} on M:{miner_uid_hex} (Task:{task_id}): {deviation:.4f}")

    # --- 2. Tính E_validator, Trust mới dự kiến, và Đóng góp cho thưởng ---
    temp_validator_contributions: Dict[str, float] = {}

    # Cải thiện cách tính E_avg: Trung bình trọng số theo stake của các validator ACTIVE
    active_validators_info = {uid: v for uid, v in validators_info.items() if getattr(v, 'status', STATUS_ACTIVE) == STATUS_ACTIVE}
    total_active_stake = sum(v.stake for v in active_validators_info.values())
    e_avg_weighted = 0.0
    if total_active_stake > EPSILON:
         # Tính E_v trung bình dựa trên trạng thái *đầu chu kỳ* (last_performance từ ValidatorInfo)
         valid_e_validators_for_avg = [(v.stake, getattr(v, 'last_performance', 0.0)) for v in active_validators_info.values()]
         if valid_e_validators_for_avg:
              e_avg_weighted = sum(stake * perf for stake, perf in valid_e_validators_for_avg) / total_active_stake
    else:
         e_avg_weighted = 0.5 # Default nếu không có ai active hoặc stake=0

    logger.info(f"  Weighted E_avg (based on start-of-cycle active validator stake): {e_avg_weighted:.4f}")

    # Tính toán cho từng validator (kể cả inactive/jailed để có trạng thái dự kiến nếu họ quay lại)
    for validator_uid_hex, validator_info in validators_info.items():
        deviations = validator_deviations.get(validator_uid_hex, [])
        avg_dev = sum(deviations) / len(deviations) if deviations else 0.0

        # Nếu validator không chấm điểm nào thì avg_dev = 0.
        # Cân nhắc: Có nên phạt validator không tham gia chấm điểm không? (Hiện tại thì không)
        logger.debug(f"  Validator {validator_uid_hex}: Average deviation = {avg_dev:.4f} ({len(deviations)} scores evaluated)")

        # Metric Quality Placeholder
        metric_quality_example = max(0.0, 1.0 - avg_dev * 1.5)
        logger.debug(f"  Validator {validator_uid_hex}: Mock Metric Quality = {metric_quality_example:.3f}")

        # Q_task Placeholder (giả sử validator không làm task)
        q_task_val_example = 0.0

        # Tính E_validator mới
        new_e_validator = calculate_validator_performance(
            q_task_validator=q_task_val_example,
            metric_validator_quality=metric_quality_example,
            deviation=avg_dev, # Độ lệch trung bình của validator này
            theta1=settings.CONSENSUS_PARAM_THETA1,
            theta2=settings.CONSENSUS_PARAM_THETA2,
            theta3=settings.CONSENSUS_PARAM_THETA3,
            # Tham số Penalty Term lấy từ settings
            penalty_threshold_dev=settings.CONSENSUS_PARAM_PENALTY_THRESHOLD_DEV,
            penalty_k_penalty=settings.CONSENSUS_PARAM_PENALTY_K_PENALTY,
            penalty_p_penalty=settings.CONSENSUS_PARAM_PENALTY_P_PENALTY
        )
        logger.info(f"  Calculated performance (E_val) for Validator {validator_uid_hex}: {new_e_validator:.4f}")

        # Tính Trust Score mới dự kiến
        # Nếu validator không hoạt động (inactive/jailed), chỉ áp dụng suy giảm
        time_since_val_eval = 1 # Mặc định là 1 chu kỳ
        score_for_trust_update = 0.0
        if getattr(validator_info, 'status', STATUS_ACTIVE) == STATUS_ACTIVE:
            # Chỉ cập nhật trust dựa trên E_v mới nếu validator đang active
            score_for_trust_update = new_e_validator
        else:
            # Nếu không active, trust chỉ bị suy giảm (score_new = 0)
            # Có thể cần logic tính time_since phức tạp hơn nếu validator bị inactive/jailed lâu
            logger.debug(f"Validator {validator_uid_hex} is not active. Applying only trust decay.")

        new_val_trust_score = update_trust_score(
             validator_info.trust_score, # Trust score đầu chu kỳ
             time_since_val_eval,
             score_for_trust_update, # Dùng E_val mới tính nếu active, nếu không thì dùng 0
             delta_trust=settings.CONSENSUS_PARAM_DELTA_TRUST,
             alpha_base=settings.CONSENSUS_PARAM_ALPHA_BASE,
             k_alpha=settings.CONSENSUS_PARAM_K_ALPHA,
             update_sigmoid_L=settings.CONSENSUS_PARAM_UPDATE_SIG_L,
             update_sigmoid_k=settings.CONSENSUS_PARAM_UPDATE_SIG_K,
             update_sigmoid_x0=settings.CONSENSUS_PARAM_UPDATE_SIG_X0
        )
        logger.info(f"  Calculated next Trust for Validator {validator_uid_hex}: {new_val_trust_score:.4f}")

        # Tính đóng góp W*E cho việc tính thưởng (dùng weight đầu chu kỳ và E_v mới)
        current_weight = getattr(validator_info, 'weight', 0.0)
        # Chỉ validator active mới đóng góp vào việc chia thưởng
        contribution = 0.0
        if getattr(validator_info, 'status', STATUS_ACTIVE) == STATUS_ACTIVE:
            contribution = current_weight * new_e_validator
            temp_validator_contributions[validator_uid_hex] = contribution
            total_validator_contribution += contribution

        # Lưu trạng thái dự kiến (bao gồm cả E_v, trust cho validator inactive/jailed)
        calculated_validator_states[validator_uid_hex] = {
            "E_v": new_e_validator,
            "trust": new_val_trust_score, # Trust dự kiến cuối chu kỳ
            "weight": current_weight, # Weight đầu chu kỳ
            "contribution": contribution, # Đóng góp W*E (chỉ > 0 nếu active)
            "last_update_cycle": current_cycle,
            # Lưu thêm trạng thái đầu vào để tiện debug/kiểm tra
            "avg_deviation": avg_dev,
            "metric_quality": metric_quality_example,
            "start_trust": validator_info.trust_score,
            "start_status": getattr(validator_info, 'status', STATUS_ACTIVE),
        }

    # --- 3. Tính phần thưởng dự kiến cho từng validator (chỉ những ai active) ---
    logger.info(f"Total validator contribution (Sum W_current*E_new from Active): {total_validator_contribution:.4f}")
    if total_validator_contribution > EPSILON:
        for validator_uid_hex, state in calculated_validator_states.items():
            # Chỉ tính thưởng cho validator active
            if state.get("start_status") == STATUS_ACTIVE:
                trust_for_reward = state["start_trust"] # Dùng trust đầu chu kỳ
                reward = calculate_validator_incentive(
                    trust_score=trust_for_reward,
                    validator_weight=state["weight"], # Weight đầu chu kỳ
                    validator_performance=state["E_v"], # E_v mới tính
                    total_validator_value=total_validator_contribution, # Tổng contribution của những người active
                    incentive_sigmoid_L=settings.CONSENSUS_PARAM_INCENTIVE_SIG_L,
                    incentive_sigmoid_k=settings.CONSENSUS_PARAM_INCENTIVE_SIG_K,
                    incentive_sigmoid_x0=settings.CONSENSUS_PARAM_INCENTIVE_SIG_X0
                )
                state["reward"] = reward # Thêm phần thưởng vào trạng thái dự kiến
                logger.info(f"  Validator {validator_uid_hex}: Calculated Reward = {reward:.6f}")
            else:
                state["reward"] = 0.0 # Không có thưởng nếu không active
    else:
         logger.warning("Total active validator contribution is zero. No validator rewards calculated.")
         for state in calculated_validator_states.values():
             state["reward"] = 0.0

    logger.info("Finished consensus calculations and validator state estimation.")
    return final_miner_scores, calculated_validator_states


# --- Logic Kiểm tra và Phạt Validator ---

async def verify_and_penalize_logic(
    current_cycle: int,
    previous_calculated_states: Dict[str, Any], # Trạng thái dự kiến của cycle N-1
    validators_info: Dict[str, ValidatorInfo], # Trạng thái hiện tại (đầu cycle N), sẽ bị thay đổi trực tiếp nếu phạt
    context: BlockFrostChainContext,
    settings: Any,
    script_hash: ScriptHash, # <<--- Thêm script_hash để query đúng contract
    network: Network,        # <<--- Thêm network
    signing_key: PaymentSigningKey, # <<--- Thêm signing key để chuẩn bị commit phạt
    stake_signing_key: Optional[StakeSigningKey] # <<--- Thêm stake key
): # <<--- Đổi tên hàm để rõ mục đích trả về
    """
    Logic kiểm tra ValidatorDatum đã commit ở chu kỳ trước, áp dụng phạt trust/status
    và chuẩn bị ValidatorDatum mới để commit hình phạt đó.

    Returns:
        Dict[str, ValidatorDatum]: Dictionary chứa UID và Datum mới cho các validator bị phạt.
                                   Sẽ được merge vào dict commit cuối chu kỳ.
    """
    logger.info(f"Verifying previous cycle ({current_cycle - 1}) validator updates...")
    previous_cycle = current_cycle - 1
    if previous_cycle < 0:
        logger.info("Skipping verification for the first cycle.")
        return {} # Trả về dict rỗng

    penalized_validator_datums: Dict[str, ValidatorDatum] = {} # Lưu datum mới cho validator bị phạt

    try:
        # 1. Lấy dữ liệu on-chain của chu kỳ TRƯỚC
        logger.debug(f"Fetching on-chain validator data updated in cycle {previous_cycle}...")
        # Sử dụng hàm đã có trong metagraph_data
        all_validator_data_list = await get_all_validator_data(context, script_hash, network)

        # Lọc và xử lý dữ liệu on-chain
        on_chain_states: Dict[str, Dict] = {}
        utxo_map: Dict[str, UTxO] = {} # Lưu UTXO để cập nhật nếu phạt
        datum_map: Dict[str, ValidatorDatum] = {} # Lưu Datum gốc để cập nhật

        for data in all_validator_data_list:
            datum_dict = data.get("datum", {})
            uid_hex = datum_dict.get("uid")
            last_update = datum_dict.get("last_update_slot")

            # Chỉ xem xét datum được cập nhật đúng ở chu kỳ trước
            if uid_hex and last_update == previous_cycle:
                on_chain_states[uid_hex] = {
                    "trust": datum_dict.get("trust_score", 0.0), # Lấy trust đã unscale từ dict
                    "E_v": datum_dict.get("last_performance", 0.0), # Lấy performance đã unscale
                    # Thêm các trường khác nếu cần kiểm tra (ví dụ: weight, rewards)
                }
                # Lưu lại UTXO và Datum gốc để có thể cập nhật nếu bị phạt
                # Cần tìm lại UTxO từ tx_id và index trong 'data'
                # Hoặc sửa get_all_validator_data để trả về cả UTxO object
                # Giả sử get_all_validator_data trả về cả UTXO gốc (cần cập nhật hàm đó)
                # if "utxo_object" in data:
                #     utxo_map[uid_hex] = data["utxo_object"]
                # if "original_datum_object" in data:
                #     datum_map[uid_hex] = data["original_datum_object"]

        logger.info(f"Found {len(on_chain_states)} validator datums updated in cycle {previous_cycle}.")

        # 2. So sánh với trạng thái dự kiến đã lưu từ chu kỳ trước
        expected_states = previous_calculated_states
        if not expected_states:
            logger.warning("No expected validator states found from previous cycle to verify against.")
            return {}

        suspicious_validators: Dict[str, str] = {} # {uid_hex: reason}
        tolerance = settings.CONSENSUS_DATUM_COMPARISON_TOLERANCE # Lấy từ settings

        # Kiểm tra những validator có trạng thái dự kiến từ chu kỳ trước
        for uid_hex, expected in expected_states.items():
            # Chỉ kiểm tra những validator được kỳ vọng sẽ cập nhật (ví dụ: active ở cycle trước)
            # if expected.get("start_status") != STATUS_ACTIVE: continue

            actual = on_chain_states.get(uid_hex)
            reason = ""
            if not actual:
                reason = f"Did not commit updates in cycle {previous_cycle}"
                suspicious_validators[uid_hex] = reason
                logger.warning(f"Potential issue for Validator {uid_hex}: {reason}")
                continue # Không có dữ liệu thực tế để so sánh sâu hơn

            # So sánh Trust Score
            expected_trust = expected.get("trust", -1.0)
            actual_trust = actual.get("trust", -2.0) # Dùng giá trị khác biệt để dễ nhận biết lỗi
            diff_trust = abs(actual_trust - expected_trust)
            if diff_trust > tolerance:
                 reason += f"Trust mismatch (Expected: {expected_trust:.5f}, Actual: {actual_trust:.5f}, Diff: {diff_trust:.5f})"

            # TODO: So sánh các trường quan trọng khác nếu cần (E_v, Weight, Rewards)
            # diff_perf = abs(actual.get("E_v", -1.0) - expected.get("E_v", -2.0))
            # if diff_perf > tolerance:
            #      reason += f"; Performance mismatch (Exp: {expected.get('E_v'):.5f}, Act: {actual.get('E_v'):.5f})"

            if reason:
                suspicious_validators[uid_hex] = reason.strip("; ")
                logger.warning(f"Potential deviation detected for Validator {uid_hex}: {reason}")

        # 3. Đồng thuận về Gian lận (Vẫn là Placeholder)
        confirmed_deviators: Dict[str, str] = {}
        if suspicious_validators:
            logger.info(f"Requesting consensus on {len(suspicious_validators)} suspicious validators...")
            # TODO: Triển khai logic P2P để đồng thuận về việc validator có thực sự "gian lận"
            # hay chỉ là lỗi mạng/trễ commit. Có thể cần nhiều bằng chứng hơn là chỉ sai lệch 1 chu kỳ.
            # confirmed_deviators = await request_fraud_consensus(suspicious_validators)
            confirmed_deviators = suspicious_validators # <<<--- Tạm thời xác nhận tất cả các sai lệch
            logger.warning(f"Deviation confirmed (mock): {list(confirmed_deviators.keys())}")

        # 4. Áp dụng Trừng phạt Trust/Status và Chuẩn bị Datum Phạt
        for uid_hex, reason in confirmed_deviators.items():
            # Lấy thông tin validator MỚI NHẤT từ validators_info (đã load đầu chu kỳ hiện tại)
            validator_info = validators_info.get(uid_hex)
            if not validator_info:
                logger.warning(f"Info for penalized validator {uid_hex} not found in current state.")
                continue

            # Chỉ phạt những validator đang Active? Hay cả Jailed/Inactive?
            # => Nên phạt cả những ai đang không active nhưng lại commit sai
            # if getattr(validator_info, 'status', STATUS_ACTIVE) != STATUS_ACTIVE:
            #     logger.info(f"Validator {uid_hex} is not active, skipping penalty application (but deviation logged).")
            #     continue

            logger.warning(f"Applying penalty to Validator {uid_hex} for: {reason}")

            # ---- Tính toán và Áp dụng Phạt ----
            # a. Xác định mức độ nghiêm trọng
            fraud_severity = _calculate_simple_fraud_severity(reason)

            # b. Tính lượng stake có thể bị slash (nhưng chưa thực hiện)
            slash_amount = calculate_slash_amount(validator_info.stake, fraud_severity, settings.CONSENSUS_PARAM_MAX_SLASH_RATE)
            if slash_amount > 0:
                 logger.warning(f"Calculated potential slash amount for {uid_hex}: {slash_amount / 1e6:.6f} ADA (Severity: {fraud_severity:.2f})")
                 # TODO: Trigger Slashing Mechanism (Future)

            # c. Phạt Trust Score (Áp dụng vào trạng thái trong bộ nhớ)
            penalty_eta = settings.CONSENSUS_PARAM_PENALTY_ETA # Lấy hệ số phạt từ settings
            original_trust = validator_info.trust_score
            new_trust_score = original_trust * (1 - penalty_eta * fraud_severity) # Giảm trust theo mức độ nghiêm trọng
            new_trust_score = max(0.0, new_trust_score) # Đảm bảo không âm
            logger.warning(f"Penalizing Trust Score for {uid_hex}: {original_trust:.4f} -> {new_trust_score:.4f} (Eta: {penalty_eta}, Severity: {fraud_severity:.2f})")
            validator_info.trust_score = new_trust_score # *** Cập nhật trust score trong bộ nhớ ***

            # d. Phạt Status (Ví dụ: Jailed nếu severity > ngưỡng)
            new_status = validator_info.status # Giữ nguyên status cũ
            if fraud_severity >= 0.2 and validator_info.status == STATUS_ACTIVE: # Ví dụ: Jailed nếu severity >= 0.2
                new_status = STATUS_JAILED
                logger.warning(f"Setting Validator {uid_hex} status to JAILED due to severity {fraud_severity:.2f}.")
                validator_info.status = new_status # *** Cập nhật status trong bộ nhớ ***
            # ---------------------------------

            # e. Chuẩn bị ValidatorDatum mới để Commit Hình Phạt
            # Cần lấy Datum cũ nhất của validator này (có thể không phải là datum từ previous_cycle nếu họ bị trễ)
            # Hoặc đơn giản là tạo datum mới dựa trên trạng thái hiện tại trong validator_info
            try:
                penalized_address_str = validator_info.address
                if not penalized_address_str:
                    logger.error(f"Missing address for penalized validator {uid_hex}. Cannot build penalty datum.")
                    continue
                penalized_wallet_addr_hash_bytes = penalized_address_str.encode('utf-8')
                 
                 # Lấy các thông tin khác từ validator_info (đã load đầu chu kỳ)
                datum_to_commit = ValidatorDatum(
                    uid=bytes.fromhex(uid_hex),
                    subnet_uid=validator_info.subnet_uid,
                    stake=int(validator_info.stake),
                    scaled_last_performance=int(getattr(validator_info, 'last_performance', 0.0) * settings.METAGRAPH_DATUM_INT_DIVISOR), # Giữ performance cũ
                    scaled_trust_score=int(new_trust_score * settings.METAGRAPH_DATUM_INT_DIVISOR), # <<< Trust mới bị phạt
                    accumulated_rewards=int(getattr(validator_info, 'accumulated_rewards', 0)), # Giữ rewards cũ
                    last_update_slot=current_cycle, # <<< Cập nhật slot là chu kỳ hiện tại
                    performance_history_hash=getattr(validator_info, 'performance_history_hash', None), # Giữ hash cũ
                    wallet_addr_hash=penalized_wallet_addr_hash_bytes, # Giữ hash cũ
                    status=new_status, # <<< Status mới (có thể là JAILED)
                    registration_slot=validator_info.registration_slot,
                    api_endpoint=validator_info.api_endpoint.encode('utf-8') if validator_info.api_endpoint else None,
                    version=validator_info.version
                )
                penalized_validator_datums[uid_hex] = datum_to_commit
                logger.info(f"Prepared penalty datum update for {uid_hex}.")
            except Exception as build_e:
                logger.error(f"Failed to build penalty datum for {uid_hex}: {build_e}")


    except Exception as e:
        logger.exception(f"Error during validator verification/penalization: {e}")

    # Trả về dict các datum cần cập nhật do phạt
    return penalized_validator_datums


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
            validator_address_str = self_validator_info.address
            wallet_addr_hash_bytes = validator_address_str.encode('utf-8') # Encode address thành bytes
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
                wallet_addr_hash=wallet_addr_hash_bytes,
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
    penalized_validator_updates: Dict[str, ValidatorDatum],
    # --- Thêm utxo_map ---
    current_utxo_map: Dict[str, UTxO], # Map từ uid_hex -> UTxO object ở đầu chu kỳ
    # --------------------
    context: BlockFrostChainContext,
    signing_key: PaymentSigningKey,
    stake_signing_key: Optional[StakeSigningKey],
    settings: Any,
    script_hash: ScriptHash,
    script_bytes: PlutusV3Script,
    network: Network
):
    """
    Commit các cập nhật MinerDatum và ValidatorDatum lên blockchain.
    Sử dụng current_utxo_map để lấy input UTXO.
    Thực hiện mỗi update một giao dịch riêng lẻ.
    """
    logger.info(f"Attempting to commit updates: {len(miner_updates)} miners, {len(validator_updates)} self-validators, {len(penalized_validator_updates)} penalized validators.")

    # Tạo Redeemer mặc định (cho script always_true)
    default_redeemer = Redeemer(0)

    submitted_tx_ids: Dict[str, str] = {} # {uid_hex_type: tx_id}
    failed_updates: Dict[str, str] = {}   # {uid_hex: error_message}
    skipped_updates: Dict[str, str] = {}  # {uid_hex: reason}

    # Hợp nhất các cập nhật Validator
    all_validator_updates = validator_updates.copy()
    all_validator_updates.update(penalized_validator_updates)
    logger.info(f"Total validator updates to commit: {len(all_validator_updates)}")

    # --- Gom tất cả updates vào một list để xử lý chung ---
    # List các tuple: (uid_hex, new_datum, datum_type_str)
    all_updates: List[Tuple[str, Union[MinerDatum, ValidatorDatum], str]] = []
    for uid_hex, datum in miner_updates.items():
        all_updates.append((uid_hex, datum, "Miner"))
    for uid_hex, datum in all_validator_updates.items():
        all_updates.append((uid_hex, datum, "Validator"))

    logger.info(f"Total updates to process: {len(all_updates)}")

    # --- Xử lý từng update ---
    for uid_hex, new_datum, datum_type in all_updates:
        logger.debug(f"Processing {datum_type} update for UID: {uid_hex}")

        # 1. Lấy Input UTXO từ map đã có
        input_utxo = current_utxo_map.get(uid_hex)

        if not input_utxo:
            # Lý do không tìm thấy UTXO:
            # - Miner/Validator mới đăng ký ở chu kỳ này? (Chưa có UTXO cũ) -> Lỗi logic chuẩn bị datum?
            # - UTXO đã bị tiêu thụ bởi giao dịch khác?
            # - Lỗi khi load metagraph ban đầu?
            logger.error(f"Commit skipped: Input UTxO for {datum_type} {uid_hex} not found in the initial map.")
            skipped_updates[uid_hex] = f"Input UTxO not found in initial map for {datum_type}"
            continue

        # 2. Thực hiện cập nhật bằng hàm update_datum
        try:
            logger.info(f"Submitting update transaction for {datum_type} {uid_hex}...")
            # Hàm update_datum đã bao gồm việc build, sign, submit
            tx_id: TransactionId = update_datum( # Hàm này trả về TransactionId object
                payment_xsk=signing_key,
                stake_xsk=stake_signing_key,
                script_hash=script_hash,
                utxo=input_utxo, # <<< Input UTXO đã tìm thấy
                new_datum=new_datum, # <<< Datum mới cần ghi
                script=script_bytes,
                context=context,
                network=network,
                redeemer=default_redeemer,
            )
            tx_id_str = str(tx_id)
            logger.info(f"Successfully submitted update for {datum_type} {uid_hex}. TxID: {tx_id_str}")
            submitted_tx_ids[f"{datum_type.lower()}_{uid_hex}"] = tx_id_str

            # Cập nhật lại utxo_map để loại bỏ utxo vừa dùng, tránh dùng lại trong cùng batch nếu tối ưu sau này
            # (Hiện tại không cần vì mỗi update 1 tx)
            # del current_utxo_map[uid_hex] # Cẩn thận nếu map được dùng ở nơi khác

            # Delay nhỏ giữa các lần submit để tránh rate limit
            # Có thể cấu hình thời gian delay này
            await asyncio.sleep(settings.CONSENSUS_COMMIT_DELAY_SECONDS or 1.5)

        except InvalidTransaction as e:
            # Lỗi cụ thể từ node Cardano (thường do build sai, thiếu phí, script fail,...)
            logger.error(f"Invalid Transaction committing update for {datum_type} {uid_hex}: {e}", exc_info=True)
            # Ghi lại cả context lỗi nếu có thể
            error_detail = str(e)
            if hasattr(e, 'response') and e.response:
                 error_detail += f" - Details: {e.response}"[:500] # Giới hạn độ dài log
            failed_updates[uid_hex] = f"Invalid Transaction: {error_detail}"
            # Xem xét có nên dừng lại không? Tạm thời tiếp tục với các update khác.
        except Exception as e:
            # Các lỗi khác (mạng khi submit, lỗi không mong muốn)
            logger.exception(f"Failed to commit update for {datum_type} {uid_hex}: {e}")
            failed_updates[uid_hex] = str(e)

    # --- Tổng kết ---
    total_submitted = len(submitted_tx_ids)
    total_failed = len(failed_updates)
    total_skipped = len(skipped_updates)
    logger.info(f"Commit process finished. Submitted: {total_submitted}, Failed: {total_failed}, Skipped (No Input UTXO): {total_skipped}")
    if failed_updates:
        logger.warning(f"Failed updates details: {failed_updates}")
    if skipped_updates:
        logger.warning(f"Skipped updates details: {skipped_updates}")

    # Có thể trả về kết quả commit nếu cần
    # return {"submitted": submitted_tx_ids, "failed": failed_updates, "skipped": skipped_updates}

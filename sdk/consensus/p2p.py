# sdk/consensus/scoring.py
"""
Logic chấm điểm kết quả từ miners.
"""
import dataclasses
import logging
from typing import List, Dict, Any, Optional
from pycardano import PaymentSigningKey, ExtendedSigningKey
import binascii
import asyncio
import httpx # Đảm bảo đã import httpx
import json

from sdk.core.datatypes import MinerResult, TaskAssignment, ValidatorScore, ValidatorInfo, PaymentVerificationKey, ScoreSubmissionPayload

logger = logging.getLogger(__name__)

# --- Helper function for canonical serialization (Sửa lỗi) ---
def canonical_json_serialize(data: Any) -> str:
    """
    Serialize dữ liệu thành chuỗi JSON một cách ổn định (sắp xếp key).
    Handles nested dataclasses and basic types.
    """
    # Helper function to convert dataclasses to dicts recursively
    def convert_to_dict(obj):
        if dataclasses.is_dataclass(obj):
            # Convert dataclass to dict, recursively converting fields
            # Chỉ lấy các trường được định nghĩa trong dataclass
            result = {}
            for f in dataclasses.fields(obj):
                value = getattr(obj, f.name)
                result[f.name] = convert_to_dict(value)
            return result
            # Hoặc dùng asdict đơn giản nếu không có nested dataclass phức tạp cần tùy chỉnh
            # return dataclasses.asdict(obj)
        elif isinstance(obj, list):
            # Recursively convert items in a list
            return [convert_to_dict(item) for item in obj]
        elif isinstance(obj, dict):
             # Recursively convert values in a dict
            return {k: convert_to_dict(v) for k, v in obj.items()}
        else:
            # Return basic types as is (int, float, str, bool, None)
            # Cần cẩn thận nếu có các kiểu dữ liệu khác (ví dụ: bytes, datetime)
            # Có thể cần xử lý thêm ở đây nếu cần
            return obj

    # Convert the entire input data structure to dicts
    data_to_serialize = convert_to_dict(data)

    # Dump the resulting dict structure to JSON, ensuring keys are sorted
    return json.dumps(data_to_serialize, sort_keys=True, separators=(',', ':'))
# -----------------------------------------------------------------------------------



def _calculate_score_from_result(task_data: Any, result_data: Any) -> float:
    """
    Tính điểm P_miner,v từ dữ liệu task và kết quả.
    *** Cần logic chấm điểm thực tế dựa trên loại task AI ***
    """
    # TODO: Triển khai logic chấm điểm thực tế.
    # Ví dụ đơn giản dựa trên loss:
    score = 0.0
    try:
        loss = float(result_data.get("loss", 1.0))
        score = max(0.0, min(1.0, 1.0 - loss * 1.2)) # Điều chỉnh hệ số
        logger.debug(f"Calculated score based on loss {loss:.4f}: {score:.3f}")
    except (TypeError, ValueError) as e:
        score = 0.1 # Phạt nhẹ nếu format sai
        logger.warning(f"Could not parse loss from result data {str(result_data)[:50]}... : {e}. Assigning low score.")
    except Exception as e:
        logger.exception(f"Unexpected error calculating score from result: {e}. Assigning low score.")
        score = 0.1
    return score

def score_results_logic(
    results_received: Dict[str, List[MinerResult]],
    tasks_sent: Dict[str, TaskAssignment],
    validator_uid: str
) -> Dict[str, List[ValidatorScore]]:
    """
    Chấm điểm tất cả các kết quả hợp lệ nhận được từ miners.

    Args:
        results_received: Dictionary kết quả nhận được {task_id: [MinerResult]}.
        tasks_sent: Dictionary các task đã gửi {task_id: TaskAssignment}.
        validator_uid: UID của validator đang thực hiện chấm điểm.

    Returns:
        Dictionary điểm số đã chấm {task_id: [ValidatorScore]}.
    """
    logger.info(f"[V:{validator_uid}] Scoring {len(results_received)} received tasks...")
    validator_scores: Dict[str, List[ValidatorScore]] = {}

    for task_id, results in results_received.items():
        assignment = tasks_sent.get(task_id)
        if not assignment:
            logger.warning(f"Received result for unknown/unsent task {task_id}. Skipping scoring.")
            continue

        if task_id not in validator_scores:
            validator_scores[task_id] = []

        for result in results:
            # Kiểm tra xem miner có đúng là miner được giao task không
            if result.miner_uid != assignment.miner_uid:
                 logger.warning(f"Received result for task {task_id} from unexpected miner {result.miner_uid}. Expected {assignment.miner_uid}. Skipping.")
                 continue

            score = _calculate_score_from_result(assignment.task_data, result.result_data)
            logger.info(f"  Scored Miner {result.miner_uid} for task {task_id}: {score:.3f}")

            val_score = ValidatorScore(
                task_id=task_id,
                miner_uid=result.miner_uid,
                validator_uid=validator_uid,
                score=score # Điểm P_miner,v
                # timestamp được tự động gán khi tạo ValidatorScore
            )
            validator_scores[task_id].append(val_score)

    logger.info(f"Finished scoring. Generated scores for {len(validator_scores)} tasks.")
    return validator_scores

async def broadcast_scores_logic(
    local_scores: Dict[str, List[ValidatorScore]],
    self_validator_info: ValidatorInfo,
    signing_key: ExtendedSigningKey,
    active_validators: List[ValidatorInfo],
    current_cycle: int,
    http_client: httpx.AsyncClient
):
    """
    Gửi điểm số cục bộ (local_scores) đến các validator khác, có ký dữ liệu.
    """
    self_uid = self_validator_info.uid
    logger.info(f"[V:{self_uid}] Broadcasting local scores for cycle {current_cycle}...")

    # 1. Chuẩn bị danh sách điểm số cần gửi
    local_scores_list: List[ValidatorScore] = []
    # ... (logic chuẩn bị local_scores_list giữ nguyên) ...
    for task_id, scores in local_scores.items():
        scores_from_self = [s for s in scores if s.validator_uid == self_uid]
        if scores_from_self:
            local_scores_list.extend(scores_from_self)

    if not local_scores_list:
        logger.info(f"[V:{self_uid}] No local scores generated in this cycle to broadcast.")
        return

    logger.info(f"[V:{self_uid}] Preparing to broadcast {len(local_scores_list)} score entries.")

    # --- 2. Ký dữ liệu ---
    signature_hex: Optional[str] = None
    submitter_vkey_cbor_hex: Optional[str] = None
    try:
        # a. Lấy PaymentVerificationKey hoặc ExtendedVerificationKey
        #    to_verification_key() trên ExtendedSigningKey trả về ExtendedVerificationKey
        vkey = signing_key.to_verification_key()
        # Lấy CBOR hex (ExtendedVerificationKey cũng có phương thức này)
        submitter_vkey_cbor_hex = vkey.to_cbor_hex()

        # Sử dụng hàm serialize đã sửa lỗi
        data_to_sign_str = canonical_json_serialize(local_scores_list) # <<< Sử dụng hàm đã sửa
        data_to_sign_bytes = data_to_sign_str.encode('utf-8')

        signature_bytes = signing_key.sign(data_to_sign_bytes)
        signature_hex = binascii.hexlify(signature_bytes).decode('utf-8')
    except Exception as sign_e:
        logger.error(f"Failed to sign broadcast payload: {sign_e}")
        return

    # Tạo Payload (cần import ScoreSubmissionPayload)
    # Giả sử ScoreSubmissionPayload đã được import
    from sdk.network.app.api.v1.endpoints.consensus import ScoreSubmissionPayload
    if 'ScoreSubmissionPayload' not in globals() or not callable(ScoreSubmissionPayload):
         logger.error("ScoreSubmissionPayload model is not available. Cannot broadcast.")
         return

    try:
        payload = ScoreSubmissionPayload(
            scores=local_scores_list,
            submitter_validator_uid=self_validator_info.uid,
            cycle=current_cycle,
            submitter_vkey_cbor_hex=submitter_vkey_cbor_hex,
            signature=signature_hex
        )
        payload_dict = payload.model_dump(mode='json') # payload là Pydantic nên dùng model_dump
    except Exception as pydantic_e:
        logger.exception(f"Failed to create or serialize ScoreSubmissionPayload: {pydantic_e}")
        return


    # -----------------------

    # 3. Tạo Payload (thêm signature_hex)
    if 'ScoreSubmissionPayload' not in globals() or not callable(ScoreSubmissionPayload):
        logger.error("ScoreSubmissionPayload model is not available or not callable. Cannot broadcast.")
        return

    try:
        payload = ScoreSubmissionPayload(
            scores=local_scores_list,
            submitter_validator_uid=self_uid,
            cycle=current_cycle,
            submitter_vkey_cbor_hex=submitter_vkey_cbor_hex,
            signature=signature_hex # <<<--- Thêm chữ ký vào payload
        )
        payload_dict = payload.model_dump(mode='json')
    except Exception as pydantic_e:
        logger.exception(f"Failed to create or serialize ScoreSubmissionPayload: {pydantic_e}")
        return

    # 4. Gửi request đến các validator khác
    # ... (logic gửi request giữ nguyên) ...
    broadcast_tasks = []
    sent_to_validators: List[ValidatorInfo] = []

    for validator in active_validators:
        if validator.uid == self_uid: continue
        if not validator.api_endpoint or not validator.api_endpoint.startswith(("http://", "https://")):
            logger.warning(f"Validator {validator.uid} has invalid API endpoint: '{validator.api_endpoint}'. Skipping broadcast.")
            continue

        target_url = f"{validator.api_endpoint}/v1/consensus/receive_scores" # Endpoint nhận
        logger.debug(f"Preparing to send scores to V:{validator.uid} at {target_url}")

        try:
            broadcast_tasks.append(http_client.post(target_url, json=payload_dict))
            sent_to_validators.append(validator)
        except Exception as post_err:
            logger.error(f"Error initiating post request to V:{validator.uid} at {target_url}: {post_err}")

    if not broadcast_tasks:
        logger.info("No valid target validators found to broadcast scores to.")
        return

    logger.info(f"Sending scores concurrently to {len(broadcast_tasks)} validators...")
    results = await asyncio.gather(*broadcast_tasks, return_exceptions=True)

    # 5. Xử lý kết quả gửi
    # ... (logic xử lý kết quả giữ nguyên) ...
    success_count = 0
    for i, res in enumerate(results):
        target_validator = sent_to_validators[i]
        target_val_uid = target_validator.uid

        if isinstance(res, httpx.Response):
            if 200 <= res.status_code < 300:
                success_count += 1
                logger.debug(f"Successfully sent scores to V:{target_val_uid} (Status: {res.status_code})")
            else:
                response_text = res.text[:200]
                logger.warning(f"Failed to send scores to V:{target_val_uid}. Status: {res.status_code}, Response: '{response_text}'")
        elif isinstance(res, Exception):
            logger.error(f"Error broadcasting scores to V:{target_val_uid}: {type(res).__name__} - {res}")
        else:
            logger.error(f"Unknown result type ({type(res)}) when broadcasting to V:{target_val_uid}")

    logger.info(f"Broadcast attempt finished for cycle {current_cycle}. Success: {success_count}/{len(broadcast_tasks)}.")

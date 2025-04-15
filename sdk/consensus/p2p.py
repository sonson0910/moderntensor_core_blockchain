# sdk/consensus/scoring.py
"""
Logic chấm điểm kết quả từ miners.
"""
import dataclasses
import logging
from typing import List, Dict, Any, Optional, Union, cast
from pycardano import (
    PaymentSigningKey,
    ExtendedSigningKey,
    PaymentVerificationKey,
    ExtendedVerificationKey,
)
import binascii
import asyncio
import httpx  # Đảm bảo đã import httpx
import json
import nacl.signing

from sdk.core.datatypes import (
    MinerResult,
    TaskAssignment,
    ValidatorScore,
    ValidatorInfo,
    ScoreSubmissionPayload,
)
from sdk.metagraph.metagraph_datum import STATUS_ACTIVE, STATUS_INACTIVE
from typing import TYPE_CHECKING, List  # Đảm bảo có List

if TYPE_CHECKING:
    from ..consensus.node import (
        ValidatorNode,
    )  # Sử dụng type hint để tránh import vòng tròn
    from ..core.datatypes import (
        ValidatorScore,
        ValidatorInfo,
    )  # Thêm ValidatorInfo nếu cần

logger = logging.getLogger(__name__)


# --- Helper function for canonical serialization (Sửa lỗi) ---
def canonical_json_serialize(data: Any) -> str:
    """Serialize dữ liệu thành chuỗi JSON ổn định (sắp xếp key)."""

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
        score = max(0.0, min(1.0, 1.0 - loss * 1.2))  # Điều chỉnh hệ số
        logger.debug(f"Calculated score based on loss {loss:.4f}: {score:.3f}")
    except (TypeError, ValueError) as e:
        score = 0.1  # Phạt nhẹ nếu format sai
        logger.warning(
            f"Could not parse loss from result data {str(result_data)[:50]}... : {e}. Assigning low score."
        )
    except Exception as e:
        logger.exception(
            f"Unexpected error calculating score from result: {e}. Assigning low score."
        )
        score = 0.1
    return score


def score_results_logic(
    results_received: Dict[str, List[MinerResult]],
    tasks_sent: Dict[str, TaskAssignment],
    validator_uid: str,
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
    logger.info(
        f"[V:{validator_uid}] Scoring {len(results_received)} received tasks..."
    )
    validator_scores: Dict[str, List[ValidatorScore]] = {}

    for task_id, results in results_received.items():
        assignment = tasks_sent.get(task_id)
        if not assignment:
            logger.warning(
                f"Received result for unknown/unsent task {task_id}. Skipping scoring."
            )
            continue

        if task_id not in validator_scores:
            validator_scores[task_id] = []

        for result in results:
            # Kiểm tra xem miner có đúng là miner được giao task không
            if result.miner_uid != assignment.miner_uid:
                logger.warning(
                    f"Received result for task {task_id} from unexpected miner {result.miner_uid}. Expected {assignment.miner_uid}. Skipping."
                )
                continue

            score = _calculate_score_from_result(
                assignment.task_data, result.result_data
            )
            logger.info(
                f"  Scored Miner {result.miner_uid} for task {task_id}: {score:.3f}"
            )

            val_score = ValidatorScore(
                task_id=task_id,
                miner_uid=result.miner_uid,
                validator_uid=validator_uid,
                score=score,  # Điểm P_miner,v
                # timestamp được tự động gán khi tạo ValidatorScore
            )
            validator_scores[task_id].append(val_score)

    logger.info(
        f"Finished scoring. Generated scores for {len(validator_scores)} tasks."
    )
    return validator_scores


async def broadcast_scores_logic(
    validator_node: "ValidatorNode",
    # <<< SỬA ĐỔI: Nhận dict điểm từ node, sẽ flatten sau >>>
    cycle_scores_dict: Dict[str, List["ValidatorScore"]],
):
    """
    Gửi điểm số cục bộ (local_scores) đến các validator khác (peers), có ký dữ liệu.
    Đã sửa đổi để chỉ gửi đến các validator hợp lệ và bỏ qua chính mình.
    """
    try:
        # Lấy thông tin cần thiết từ validator_node
        self_validator_info = validator_node.info
        # Cần ExtendedSigningKey để ký (hoặc PaymentSigningKey nếu node chỉ lưu key đó)
        signing_key: Union[ExtendedSigningKey, PaymentSigningKey] = validator_node.signing_key  # type: ignore
        # Lấy danh sách validator *active* từ node
        active_validator_peers = await validator_node._get_active_validators()
        current_cycle = validator_node.current_cycle
        http_client = validator_node.http_client
        settings = validator_node.settings
        self_uid = self_validator_info.uid  # UID của node hiện tại (dạng hex string)
    except AttributeError as e:
        logger.error(
            f"Missing required attribute/method on validator_node for broadcasting: {e}"
        )
        return
    except Exception as e:
        logger.error(f"Error getting attributes from validator_node: {e}")
        return

    # --- Flatten và Lọc điểm cần gửi ---
    local_scores_list: List[ValidatorScore] = []
    for task_id, scores in cycle_scores_dict.items():
        for score in scores:
            # Chỉ gửi điểm do chính validator này tạo ra
            if score.validator_uid == self_uid:
                local_scores_list.append(score)

    if not local_scores_list:
        logger.debug(
            f"[V:{self_uid}] No local scores generated by self in cycle {current_cycle} to broadcast."
        )
        return

    logger.info(
        f"[V:{self_uid}] Preparing to broadcast {len(local_scores_list)} score entries generated by self for cycle {current_cycle}."
    )

    # --- Ký Dữ liệu ---
    signature_hex: Optional[str] = None
    submitter_vkey_cbor_hex: Optional[str] = None
    try:
        # Lấy verification key (cần xử lý cả Extended và Payment)
        verification_key = signing_key.to_verification_key()

        # Chỉ lấy PaymentVerificationKey để gửi đi (vì chỉ cần payment hash để xác thực)
        payment_vkey: PaymentVerificationKey
        if isinstance(verification_key, ExtendedVerificationKey):
            # Explicitly cast the result, as from_primitive might return a base Key type
            primitive_key = verification_key.to_primitive()[:32]
            payment_vkey = cast(
                PaymentVerificationKey,
                PaymentVerificationKey.from_primitive(primitive_key),
            )
        elif isinstance(verification_key, PaymentVerificationKey):
            payment_vkey = verification_key
        else:
            raise TypeError(
                f"Unexpected verification key type derived: {type(verification_key)}"
            )

        submitter_vkey_cbor_hex = payment_vkey.to_cbor_hex()

        # Serialize list điểm ĐÃ LỌC VÀ FLATTEN
        data_to_sign_str = canonical_json_serialize(
            local_scores_list
        )  # <<<--- Dùng list đã flatten
        data_to_sign_bytes = data_to_sign_str.encode("utf-8")

        # Ký bằng signing_key (dùng to_primitive nếu là Extended)
        sk_primitive = signing_key.to_primitive()
        nacl_signing_key = nacl.signing.SigningKey(
            sk_primitive[:32]
        )  # Lấy 32 byte đầu làm seed cho PyNaCl sk
        signed_pynacl = nacl_signing_key.sign(data_to_sign_bytes)
        signature_bytes = signed_pynacl.signature  # Lấy phần signature bytes

        # signature_bytes = signing_key.sign(data_to_sign_bytes) # Cách cũ nếu dùng pycardano sign
        signature_hex = binascii.hexlify(signature_bytes).decode("utf-8")
        logger.debug(f"[V:{self_uid}] Payload signed successfully.")
    except Exception as sign_e:
        logger.exception(f"[V:{self_uid}] Failed to sign broadcast payload: {sign_e}")
        return

    # --- Tạo Payload ---
    try:
        # Chuyển đổi list ValidatorScore thành list dict để Pydantic xử lý
        # scores_as_dicts = [dataclasses.asdict(s) for s in local_scores_list] # Removed this line

        payload = ScoreSubmissionPayload(
            scores=local_scores_list,  # <<< Pass the list of objects directly
            submitter_validator_uid=self_uid,
            cycle=current_cycle,
            submitter_vkey_cbor_hex=submitter_vkey_cbor_hex,
            signature=signature_hex,
        )
        payload_dict = payload.model_dump(
            mode="json"
        )  # Dùng model_dump cho Pydantic v2
    except Exception as pydantic_e:
        logger.exception(
            f"[V:{self_uid}] Failed to create or serialize ScoreSubmissionPayload: {pydantic_e}"
        )
        return

    # --- Gửi Payload đến các Peers Hợp Lệ ---
    broadcast_tasks = []
    sent_to_validators_info: List[ValidatorInfo] = []

    # Lặp qua danh sách validator peers đã được lọc bởi _get_active_validators
    for peer_info in active_validator_peers:
        # >>> Bỏ qua chính mình <<<
        if peer_info.uid == self_uid:
            continue
        # >>> Bỏ qua nếu không có endpoint hoặc không active (dù _get_active_validators thường đã lọc) <<<
        if not peer_info.api_endpoint or not peer_info.api_endpoint.startswith(
            ("http://", "https://")
        ):
            logger.warning(
                f"[V:{self_uid}] Peer V:{peer_info.uid} has invalid API endpoint '{peer_info.api_endpoint}'. Skipping broadcast."
            )
            continue
        if getattr(peer_info, "status", STATUS_INACTIVE) != STATUS_ACTIVE:
            logger.debug(
                f"[V:{self_uid}] Peer V:{peer_info.uid} is not active (status={getattr(peer_info, 'status', 'N/A')}). Skipping broadcast."
            )
            continue

        # >>> Chỉ gửi cho VALIDATOR <<< (Không cần kiểm tra thêm vì active_validator_peers chỉ chứa validator)

        target_url = f"{peer_info.api_endpoint.rstrip('/')}/v1/consensus/receive_scores"
        logger.debug(
            f"[V:{self_uid}] Preparing to send scores to V:{peer_info.uid} at {target_url}"
        )

        try:
            request_timeout = getattr(
                settings, "CONSENSUS_NETWORK_TIMEOUT_SECONDS", 10.0
            )
            task = asyncio.create_task(
                http_client.post(target_url, json=payload_dict, timeout=request_timeout)
            )
            broadcast_tasks.append(task)
            sent_to_validators_info.append(peer_info)
        except Exception as req_e:
            logger.error(
                f"[V:{self_uid}] Error creating broadcast task for {target_url} (Peer: V:{peer_info.uid}): {req_e}"
            )

    if not broadcast_tasks:
        logger.info(
            f"[V:{self_uid}] No valid target validators found to broadcast scores to."
        )
        return

    logger.info(
        f"[V:{self_uid}] Sending scores concurrently to {len(broadcast_tasks)} validators..."
    )
    results = await asyncio.gather(*broadcast_tasks, return_exceptions=True)

    # --- Xử lý kết quả gửi (Giữ nguyên logic log chi tiết đã sửa) ---
    success_count = 0
    for i, res in enumerate(results):
        if i < len(sent_to_validators_info):
            target_validator = sent_to_validators_info[i]
            target_val_uid = target_validator.uid
            target_endpoint = target_validator.api_endpoint

            if isinstance(res, httpx.Response):
                if 200 <= res.status_code < 300:
                    success_count += 1
                    logger.debug(
                        f"[V:{self_uid}] Successfully sent scores to V:{target_val_uid} (Status: {res.status_code})"
                    )
                else:
                    response_text = res.text[:200]
                    logger.warning(
                        f"[V:{self_uid}] Failed to send scores to V:{target_val_uid} at {target_endpoint}. Status: {res.status_code}, Response: '{response_text}'"
                    )
            elif isinstance(res, Exception):
                if isinstance(res, httpx.TimeoutException):
                    logger.warning(
                        f"[V:{self_uid}] Timeout broadcasting to V:{target_val_uid} at {target_endpoint}: {res}"
                    )
                elif isinstance(res, httpx.RequestError):
                    logger.error(
                        f"[V:{self_uid}] Network error broadcasting to V:{target_val_uid} at {target_endpoint}: {type(res).__name__} - {res}"
                    )
                else:
                    logger.error(
                        f"[V:{self_uid}] Unexpected error broadcasting to V:{target_val_uid} at {target_endpoint}: {type(res).__name__} - {res}"
                    )
            else:
                logger.error(
                    f"[V:{self_uid}] Unknown result type ({type(res)}) when broadcasting to V:{target_val_uid}"
                )
        else:
            logger.error(
                f"[V:{self_uid}] Result index mismatch during broadcast result processing. Index: {i}, Sent Count: {len(sent_to_validators_info)}"
            )

    logger.info(
        f"[V:{self_uid}] Broadcast attempt finished for cycle {current_cycle}. Success: {success_count}/{len(broadcast_tasks)}."
    )

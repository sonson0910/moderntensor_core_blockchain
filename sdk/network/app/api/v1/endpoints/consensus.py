# sdk/network/app/api/v1/endpoints/consensus.py
"""
API endpoints cho việc trao đổi thông tin đồng thuận giữa các validator.
"""
from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Annotated, Optional
import logging
import asyncio
import json # Thêm json
import binascii # Thêm binascii

from pydantic import BaseModel, Field, ValidationError
from sdk.core.datatypes import ValidatorScore, ValidatorInfo
# --- Import các thành phần cần thiết ---
from pycardano import Address, VerificationKey, PaymentVerificationKey # Cần VerificationKey
# ------------------------------------
from sdk.consensus.node import ValidatorNode
from sdk.network.app.dependencies import get_validator_node
# --- Import hàm serialize ---
from sdk.consensus.p2p import canonical_json_serialize # Import helper serialize



# --- Định nghĩa Pydantic Model cho Payload ---
class ScoreSubmissionPayload(BaseModel):
    """Dữ liệu điểm số gửi qua API, bao gồm VKey và chữ ký."""
    scores: List[ValidatorScore] = Field(..., description="Danh sách điểm số chi tiết ValidatorScore")
    submitter_validator_uid: str = Field(..., description="UID (dạng hex) của validator gửi điểm")
    cycle: int = Field(..., description="Chu kỳ đồng thuận mà điểm số này thuộc về")
    # --- Thêm trường VKey của người gửi ---
    submitter_vkey_cbor_hex: Optional[str] = Field(None, description="Payment Verification Key của người gửi (CBOR hex)")
    # -------------------------------------
    signature: Optional[str] = Field(None, description="Chữ ký (dạng hex) của hash(scores) để xác thực người gửi")

# --- Router ---
router = APIRouter(
    prefix="/consensus",
    tags=["Consensus P2P"],
)

logger = logging.getLogger(__name__)

# --- Hàm xác thực chữ ký (Placeholder - Cần Verification Key) ---
async def verify_signature(
    submitter_info: ValidatorInfo, # Thông tin của người gửi
    scores_data: List[ValidatorScore], # Dữ liệu gốc đã nhận
    signature_hex: Optional[str]
) -> bool:
    """
    (Placeholder) Xác thực chữ ký của validator gửi đến.
    Cần có PaymentVerificationKey của người gửi trong submitter_info.
    """
    if not signature_hex:
        logger.warning(f"Missing signature from validator {submitter_info.uid}. Verification skipped/failed.")
        return False # Yêu cầu phải có chữ ký

    logger.debug(f"Attempting signature verification for validator {submitter_info.uid}...")

    # --- Logic xác thực thực tế (Cần VKey) ---
    # payment_vkey = submitter_info.payment_verification_key # Lấy từ property (nếu đã thêm vào datatypes.py và load được)
    # if not payment_vkey:
    #     logger.error(f"Missing Payment Verification Key for submitter {submitter_info.uid}. Cannot verify signature.")
    #     return False # Không có key thì không xác thực được

    # try:
    #     # Serialize lại dữ liệu nhận được THEO ĐÚNG CÁCH đã ký
    #     data_to_verify_str = canonical_json_serialize(scores_data)
    #     data_to_verify_bytes = data_to_verify_str.encode('utf-8')

    #     # Decode chữ ký hex
    #     signature_bytes = binascii.unhexlify(signature_hex)

    #     # Thực hiện xác minh
    #     is_valid = payment_vkey.verify(signature_bytes, data_to_verify_bytes)
    #     logger.debug(f"Signature verification result for {submitter_info.uid}: {is_valid}")
    #     return is_valid
    # except binascii.Error:
    #      logger.error(f"Invalid signature hex format from {submitter_info.uid}.")
    #      return False
    # except Exception as e:
    #     logger.error(f"Error during signature verification for {submitter_info.uid}: {e}")
    #     return False
    # ---------------------------------------------

    # --- Placeholder Logic ---
    await asyncio.sleep(0.01) # Giả lập thời gian
    logger.warning(f"Signature verification for {submitter_info.uid} is currently a placeholder and returns True.")
    return True # <<<<---- TẠM THỜI LUÔN TRUE
    # -------------------------

# --- API Endpoint ---

@router.post("/receive_scores",
             summary="Nhận điểm số từ Validator khác",
             description="Endpoint để một Validator gửi danh sách điểm số (ValidatorScore) mà nó đã chấm cho các Miner trong một chu kỳ. Yêu cầu chữ ký hợp lệ.",
             status_code=status.HTTP_202_ACCEPTED)
async def receive_scores(
    payload: ScoreSubmissionPayload,
    node: Annotated[ValidatorNode, Depends(get_validator_node)]
):
    """
    Endpoint để nhận điểm số ValidatorScore từ một validator khác.
    Thêm logic xác thực người gửi và xác minh chữ ký (placeholder).
    """
    submitter_uid = payload.submitter_validator_uid
    current_cycle = node.current_cycle
    payload_cycle = payload.cycle

    logger.info(f"API: Received scores from {submitter_uid} for cycle {payload_cycle} (Node cycle: {current_cycle})")

    # --- Xác thực người gửi ---
    submitter_info = node.validators_info.get(submitter_uid)
    if not submitter_info or getattr(submitter_info, 'status', 1) == 0: # Kiểm tra cả status nếu có
        logger.warning(f"Received scores from unknown or inactive validator UID: {submitter_uid}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown or inactive submitter validator UID: {submitter_uid}"
        )

    # Kiểm tra chu kỳ
    # Chỉ chấp nhận điểm của chu kỳ hiện tại
    if payload_cycle != current_cycle:
        logger.warning(f"Received scores for wrong cycle {payload_cycle} from {submitter_uid} (current: {current_cycle})")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid cycle: {payload_cycle}. Current cycle is {current_cycle}."
        )

    # --- Xác minh chữ ký ---
    is_signature_valid = await verify_signature(submitter_info, payload.scores, payload.signature)
    if not is_signature_valid:
        logger.warning(f"Invalid or missing signature from {submitter_uid} for cycle {payload_cycle}.")
        raise HTTPException(
            # Dùng 401 Unauthorized hoặc 403 Forbidden
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing signature."
        )
    logger.debug(f"Signature verified (placeholder) for scores from {submitter_uid}")
    # ----------------------

    # Gọi phương thức trên node để thêm điểm số nhận được
    try:
        await node.add_received_score(
            submitter_uid,
            payload_cycle,
            payload.scores
        )
        logger.info(f"Successfully processed {len(payload.scores)} scores from {submitter_uid} for cycle {payload_cycle}")
        return {"message": f"Accepted {len(payload.scores)} scores from {submitter_uid}."}
    except ValidationError as ve: # Bắt lỗi validation của Pydantic nếu add_received_score có validation
        logger.error(f"API Validation Error processing scores from {submitter_uid}: {ve}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid score data format: {ve}"
        )
    except Exception as e:
        logger.exception(f"API Error processing received scores from {submitter_uid}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error processing scores: {e}"
        )
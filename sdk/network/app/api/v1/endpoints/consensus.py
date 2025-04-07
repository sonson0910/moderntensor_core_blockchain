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
from pycardano import Address, VerificationKey, PaymentVerificationKey, VerificationKeyHash # Cần VerificationKey
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
# --- Hàm xác thực chữ ký (Triển khai thực tế) ---
async def verify_payload_signature(
    submitter_info: ValidatorInfo, # Thông tin của người gửi (chứa address)
    payload: ScoreSubmissionPayload # Payload đầy đủ đã nhận
) -> bool:
    """
    Xác thực chữ ký trong payload.
    1. Kiểm tra xem VKey được cung cấp có khớp với địa chỉ của người gửi không.
    2. Nếu khớp, dùng VKey đó để xác minh chữ ký trên dữ liệu scores.
    """
    signature_hex = payload.signature
    submitter_vkey_hex = payload.submitter_vkey_cbor_hex
    scores_data = payload.scores # Dữ liệu gốc cần xác minh

    if not signature_hex or not submitter_vkey_hex:
        logger.warning(f"Missing signature or submitter VKey from validator {submitter_info.uid}. Verification failed.")
        return False

    logger.debug(f"Verifying signature for validator {submitter_info.uid}...")

    try:
        # 1. Lấy payment hash từ địa chỉ của người gửi (đã có trong submitter_info)
        submitter_address = Address.from_primitive(submitter_info.address)
        expected_payment_hash: VerificationKeyHash = submitter_address.payment_part
        logger.debug(f"Expected payment hash from address: {expected_payment_hash.to_primitive().hex()}")

        # 2. Load VerificationKey từ CBOR hex trong payload
        try:
             received_vkey = PaymentVerificationKey.from_cbor_hex(submitter_vkey_hex)
        except Exception as key_load_e:
             logger.error(f"Failed to load submitter VKey from CBOR hex for {submitter_info.uid}: {key_load_e}")
             return False

        # 3. Xác minh VKey: Kiểm tra hash của VKey nhận được có khớp với payment_part của địa chỉ không
        received_vkey_hash: VerificationKeyHash = received_vkey.hash()
        logger.debug(f"Hash of received VKey: {received_vkey_hash.to_primitive().hex()}")

        if received_vkey_hash != expected_payment_hash:
            logger.warning(f"Verification Key hash mismatch for {submitter_info.uid}. Expected {expected_payment_hash.to_primitive().hex()}, got {received_vkey_hash.to_primitive().hex()}. Possible impersonation attempt.")
            return False
        logger.debug(f"Submitter Verification Key is valid for address {submitter_info.address}.")

        # 4. Xác minh Chữ ký: Nếu VKey hợp lệ, dùng nó để xác minh chữ ký
        # a. Serialize lại dữ liệu scores theo đúng cách đã ký
        data_to_verify_str = canonical_json_serialize(scores_data)
        data_to_verify_bytes = data_to_verify_str.encode('utf-8')

        # b. Decode chữ ký hex
        signature_bytes = binascii.unhexlify(signature_hex)

        # c. Thực hiện xác minh bằng VKey đã load
        is_valid = received_vkey.verify(signature_bytes, data_to_verify_bytes)
        logger.debug(f"Signature verification result for {submitter_info.uid}: {is_valid}")
        return is_valid

    except binascii.Error:
         logger.error(f"Invalid signature hex format received from {submitter_info.uid}.")
         return False
    except Exception as e:
        # Bắt các lỗi khác (ví dụ: lỗi parse address, lỗi verify,...)
        logger.error(f"Error during signature verification process for {submitter_info.uid}: {e}", exc_info=True)
        return False

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
    is_signature_valid = await verify_payload_signature(submitter_info, payload) # Truyền cả payload
    if not is_signature_valid:
        logger.warning(f"Invalid signature or VKey from {submitter_uid} for cycle {payload_cycle}.")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature or verification key.")
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
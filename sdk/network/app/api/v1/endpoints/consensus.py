# sdk/network/app/api/v1/endpoints/consensus.py
"""
API endpoints cho việc trao đổi thông tin đồng thuận giữa các validator.
"""
import logging
import asyncio
import json
import binascii
from typing import List, Annotated, Optional
from fastapi import APIRouter, HTTPException, Depends, status

from pydantic import BaseModel, Field, ValidationError
from sdk.core.datatypes import ValidatorScore, ValidatorInfo, ScoreSubmissionPayload

# Import các kiểu Cardano cần thiết
from pycardano import (
    Address,
    VerificationKey,
    PaymentVerificationKey,
    VerificationKeyHash,
)
from sdk.consensus.node import ValidatorNode
from sdk.network.app.dependencies import get_validator_node

# Import hàm serialize từ p2p
from sdk.consensus.p2p import canonical_json_serialize
import nacl.signing  # <<< Thêm import
import nacl.exceptions  # <<< Thêm import


# --- Router ---
router = APIRouter(
    prefix="/consensus",
    tags=["Consensus P2P"],
)

logger = logging.getLogger(__name__)


# --- Hàm xác thực chữ ký (Placeholder - Cần Verification Key) ---
# --- Hàm xác thực chữ ký (Triển khai thực tế) ---
async def verify_payload_signature(
    submitter_info: ValidatorInfo, payload: ScoreSubmissionPayload
) -> bool:
    signature_hex = payload.signature
    submitter_vkey_hex = payload.submitter_vkey_cbor_hex
    scores_data = payload.scores

    if not signature_hex or not submitter_vkey_hex:
        logger.warning(
            f"SigVerifyFail ({submitter_info.uid}): Missing signature or VKey."
        )
        return False

    logger.debug(f"Verifying signature for validator {submitter_info.uid}...")

    try:
        # 1. Lấy payment hash mong đợi từ địa chỉ người gửi
        submitter_address = Address.from_primitive(submitter_info.address)
        expected_payment_hash: VerificationKeyHash = submitter_address.payment_part  # type: ignore
        logger.debug(
            f"Expected payment hash: {expected_payment_hash.to_primitive().hex()}"
        )

        # 2. Load VKey từ payload (SỬA Ở ĐÂY)
        try:
            vkey_cbor_bytes = binascii.unhexlify(submitter_vkey_hex)
            received_pycardano_vkey = PaymentVerificationKey.from_cbor(vkey_cbor_bytes)
            received_vk_bytes = (
                received_pycardano_vkey.to_primitive()
            )  # <<< Lấy raw bytes
        except (binascii.Error, ValueError, Exception) as key_load_e:
            logger.error(
                f"SigVerifyFail ({submitter_info.uid}): Failed to load VKey from CBOR hex or get primitive: {key_load_e}"
            )
            return False

        # 3. Xác minh VKey: Hash của VKey nhận được phải khớp với hash từ địa chỉ
        received_vkey_hash: VerificationKeyHash = received_pycardano_vkey.hash()  # type: ignore
        logger.debug(f"Received VKey hash: {received_vkey_hash.to_primitive().hex()}")

        if received_vkey_hash != expected_payment_hash:
            logger.warning(
                f"SigVerifyFail ({submitter_info.uid}): VKey hash mismatch! Expected {expected_payment_hash.to_primitive().hex()}, got {received_vkey_hash.to_primitive().hex()}."
            )
            return False
        logger.debug(f"Submitter VKey matches address hash.")

        # 4. Xác minh Chữ ký
        data_str_from_payload = canonical_json_serialize(payload.scores)
        data_to_verify_bytes = data_str_from_payload.encode("utf-8")
        signature_bytes = binascii.unhexlify(signature_hex)

        nacl_vk = nacl.signing.VerifyKey(received_vk_bytes)  # type: ignore # <<< Tạo VerifyKey của PyNaCl
        try:
            nacl_vk.verify(
                data_to_verify_bytes, signature_bytes
            )  # <<< Gọi verify của PyNaCl
            is_valid = True
            logger.debug(
                f"PyNaCl Signature verification successful for {submitter_info.uid}"
            )
        except nacl.exceptions.BadSignatureError:
            is_valid = False
            logger.warning(
                f"SigVerifyFail ({submitter_info.uid}): Invalid signature (PyNaCl BadSignatureError)."
            )

        return is_valid

    except binascii.Error:
        logger.error(
            f"SigVerifyFail ({submitter_info.uid}): Invalid signature hex format."
        )
        return False
    except Exception as e:
        logger.error(
            f"SigVerifyFail ({submitter_info.uid}): Error during verification: {e}",
            exc_info=True,
        )
        return False


# ---

# --- API Endpoint ---


@router.post(
    "/receive_scores",
    summary="Nhận điểm số từ Validator khác",
    description="Endpoint để một Validator gửi danh sách điểm số (ValidatorScore) mà nó đã chấm cho các Miner trong một chu kỳ. Yêu cầu chữ ký hợp lệ.",
    status_code=status.HTTP_202_ACCEPTED,
)
async def receive_scores(
    payload: ScoreSubmissionPayload,
    node: Annotated[ValidatorNode, Depends(get_validator_node)],
):
    submitter_uid = payload.submitter_validator_uid
    current_cycle = node.current_cycle
    payload_cycle = payload.cycle

    logger.info(
        f"API: Received scores from {submitter_uid} for cycle {payload_cycle} (Node cycle: {current_cycle})"
    )

    # Xác thực người gửi (logic như cũ)
    submitter_info = node.validators_info.get(submitter_uid)
    if not submitter_info or getattr(submitter_info, "status", 1) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown/inactive submitter: {submitter_uid}",
        )

    # Kiểm tra chu kỳ (chỉ chấp nhận chu kỳ hiện tại)
    if payload_cycle != current_cycle:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid cycle: {payload_cycle}. Current: {current_cycle}.",
        )

    # Xác minh chữ ký (gọi hàm mới)
    if not await verify_payload_signature(submitter_info, payload):
        logger.warning(
            f"Rejected scores from {submitter_uid} due to invalid signature/VKey."
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature or verification key.",
        )
    logger.debug(f"Signature verified for scores from {submitter_uid}")

    # Thêm điểm số đã xác minh (logic như cũ)
    try:
        await node.add_received_score(submitter_uid, payload_cycle, payload.scores)
        logger.info(
            f"Successfully processed {len(payload.scores)} scores from {submitter_uid}"
        )
        return {
            "message": f"Accepted {len(payload.scores)} scores from {submitter_uid}."
        }
    except Exception as e:  # Bắt lỗi chung khi thêm điểm
        logger.exception(
            f"API Error processing scores from {submitter_uid} after verification: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing scores: {e}",
        )

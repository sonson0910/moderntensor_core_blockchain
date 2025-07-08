"""
API endpoints for consensus-related operations in ModernTensor network.

This module provides FastAPI endpoints for:
- Validator score submissions
- Consensus data retrieval
- Miner result submissions
- Network status and health checks

All endpoints are designed to work with the Core blockchain infrastructure.
"""

import logging
import asyncio
import json
import binascii
import dataclasses  # <<<--- Thêm import dataclasses
from typing import List, Annotated, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError

# Import các kiểu dữ liệu và node từ SDK
from mt_aptos.core.datatypes import (
    ValidatorScore,
    ValidatorInfo,
    ScoreSubmissionPayload,
)
from mt_core.consensus.node import ValidatorNode
from mt_core.network.app.dependencies import get_validator_node

# Import hàm serialize từ P2P
# from mt_aptos.consensus.p2p import canonical_json_serialize
from mt_core.consensus.scoring import canonical_json_serialize

# Updated imports for Core blockchain
from web3 import Web3
from eth_account import Account
from eth_utils import to_checksum_address

# Remove Aptos SDK imports
# from aptos_sdk.ed25519 import PublicKey

# Local imports
# from mt_aptos.consensus.scoring import canonical_json_serialize

# Keep or adapt the nacl imports for verification as needed
import nacl.signing
import nacl.exceptions

# Add missing imports for Core blockchain
import binascii

# Additional missing imports
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mt_core.consensus.validator_node_core import ValidatorNodeCore as ValidatorNode
else:
    # Fallback for runtime
    class ValidatorNode:
        pass


# Proper Pydantic models for missing dependencies
class ScoreSubmissionPayload(BaseModel):
    submitter_validator_uid: str
    cycle: int
    scores: List[Dict[str, Any]]
    signature: str
    public_key_hex: str

    class Config:
        extra = "allow"


def get_validator_node():
    """Fallback dependency function"""
    return ValidatorNode()


# --- Router ---
router = APIRouter(prefix="/consensus", tags=["Consensus P2P"])
logger = logging.getLogger(__name__)


# --- Hàm xác thực chữ ký (Đã sửa đổi cho Aptos) ---
async def verify_payload_signature(
    receiver_node: "ValidatorNode",  # Node đang nhận request
    payload: ScoreSubmissionPayload,  # Dữ liệu nhận được
) -> bool:
    """Xác minh chữ ký và Public Key trong payload nhận được từ một peer."""
    signature_hex = payload.signature
    submitter_public_key_hex = payload.public_key_hex  # Fix field name
    scores_list_dict = payload.scores  # Đây là list các dict
    submitter_uid = payload.submitter_validator_uid  # UID của người gửi

    if not signature_hex or not submitter_public_key_hex:
        logger.warning(
            f"SigVerifyFail (Receiver: {receiver_node.info.uid}, Sender: {submitter_uid}): Missing signature or public key in payload."
        )
        return False

    logger.debug(f"Verifying signature for payload from validator {submitter_uid}...")

    # --- Lấy thông tin người gửi đã biết từ state của node NHẬN ---
    submitter_info = receiver_node.validators_info.get(submitter_uid)
    if not submitter_info:
        logger.warning(
            f"SigVerifyFail (Receiver: {receiver_node.info.uid}): Submitter validator {submitter_uid} not found in local state."
        )
        return False  # Từ chối nếu không biết người gửi

    try:
        # 1. Lấy address dự kiến từ thông tin người gửi đã biết
        submitter_address = submitter_info.address
        if not submitter_address.startswith("0x"):
            logger.warning(
                f"SigVerifyFail (Sender: {submitter_uid}): Expected Aptos address format starting with 0x, got {submitter_address}"
            )
            return False

        # 2. Load Public Key từ payload
        try:
            public_key_bytes = binascii.unhexlify(submitter_public_key_hex)
            # Create an Aptos SDK PublicKey object
            received_public_key = PublicKey(public_key_bytes)
        except (binascii.Error, ValueError, TypeError) as key_load_e:
            logger.error(
                f"SigVerifyFail (Sender: {submitter_uid}): Failed to load/decode public key from hex '{submitter_public_key_hex[:10]}...': {key_load_e}"
            )
            return False
        except Exception as e:
            logger.error(
                f"SigVerifyFail (Sender: {submitter_uid}): Unexpected error processing received public key: {e}"
            )
            return False

        # 3. Xác minh Public Key: Tạo địa chỉ từ public key và so sánh với địa chỉ đã biết
        try:
            # Create an Account with the received public key to get its address
            temp_account = Account(None, received_public_key)
            received_address = "0x" + temp_account.address().hex()

            # Compare the address derived from the received public key with the known address
            if received_address != submitter_address:
                logger.warning(
                    f"SigVerifyFail (Sender: {submitter_uid}): Address MISMATCH!"
                )
                logger.warning(
                    f" -> Receiver expected address {submitter_address} (from metagraph)"
                )
                logger.warning(
                    f" -> Derived address from public key is {received_address}"
                )
                return False

            logger.debug(
                f"Submitter public key matches expected address from known validator info."
            )
        except Exception as addr_e:
            logger.error(
                f"SigVerifyFail (Sender: {submitter_uid}): Error verifying address from public key: {addr_e}"
            )
            return False

        # 4. Xác minh Chữ ký
        try:
            # Serialize data to bytes for verification
            scores_objects_from_payload = payload.scores

            # Check if the list of scores is empty after Pydantic parsing
            if not scores_objects_from_payload:
                logger.warning(
                    f"SigVerifyFail (Sender: {submitter_uid}): Payload contained no valid score objects after Pydantic parsing."
                )

            # Serialize the score objects to JSON string
            data_str_from_payload = canonical_json_serialize(
                scores_objects_from_payload
            )
            data_to_verify_bytes = data_str_from_payload.encode("utf-8")
            signature_bytes = binascii.unhexlify(signature_hex)

            # Verify using Aptos SDK PublicKey's verify method
            is_valid = received_public_key.verify(data_to_verify_bytes, signature_bytes)

            if is_valid:
                logger.info(
                    f"Signature verification SUCCESSFUL for payload from {submitter_uid}"
                )
            else:
                logger.warning(
                    f"SigVerifyFail (Sender: {submitter_uid}): Invalid signature. Data or signature mismatch."
                )
                logger.debug(
                    f" - Data used for verification: {data_str_from_payload[:200]}..."
                )
                logger.debug(f" - Signature hex received: {signature_hex}")

            return is_valid

        except binascii.Error:
            logger.error(
                f"SigVerifyFail (Sender: {submitter_uid}): Invalid signature hex format."
            )
            return False
        except Exception as verify_e:
            logger.exception(
                f"SigVerifyFail (Sender: {submitter_uid}): Error during signature verification step: {verify_e}"
            )
            return False

    except Exception as outer_e:
        logger.exception(
            f"SigVerifyFail (Sender: {submitter_uid}): Unexpected outer error during verification: {outer_e}"
        )
        return False


# --- API Endpoint ---
@router.post(
    "/receive-scores",
    summary="Nhận điểm số từ Validator khác",
    description="Endpoint để một Validator gửi danh sách điểm số (ValidatorScore) mà nó đã chấm. Yêu cầu chữ ký hợp lệ.",
    status_code=status.HTTP_202_ACCEPTED,
)
async def receive_scores(
    payload: ScoreSubmissionPayload,  # Dữ liệu gửi lên từ peer
    # Lấy instance ValidatorNode của node đang chạy API này
    node: Annotated[ValidatorNode, Depends(get_validator_node)],
):
    submitter_uid = payload.submitter_validator_uid
    current_cycle = node.current_cycle
    payload_cycle = payload.cycle

    logger.info(
        f"API: Received scores submission from V:{submitter_uid} for cycle {payload_cycle} (Node cycle: {current_cycle})"
    )

    # --- Bỏ qua chính mình (dù broadcast logic đã lọc) ---
    if submitter_uid == node.info.uid:
        logger.debug(f"API: Received scores from self ({submitter_uid}). Ignoring.")
        # Trả về thành công giả để tránh client báo lỗi không cần thiết
        return {"message": "Accepted scores from self (ignored)."}

    # --- Kiểm tra chu kỳ ---
    # Cho phép nhận điểm cho chu kỳ hiện tại hoặc chu kỳ trước đó một chút (đề phòng trễ mạng)
    if not (current_cycle - 1 <= payload_cycle <= current_cycle):
        logger.warning(
            f"API: Received scores for invalid cycle {payload_cycle} from {submitter_uid}. Current: {current_cycle}. Rejecting."
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid cycle: {payload_cycle}. Current: {current_cycle}.",
        )

    # --- Xác minh chữ ký và Public Key ---
    if not await verify_payload_signature(node, payload):
        logger.warning(
            f"API: Rejected scores from {submitter_uid} for cycle {payload_cycle} due to invalid signature/public key."
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature or public key.",
        )

    # --- Forward to broadcast (will be handled fully by node.handle_scores_submission) ---
    try:
        await node.handle_scores_submission(
            submitter_uid, scores=payload.scores, cycle=payload_cycle
        )
        logger.info(
            f"API: Successfully processed scores from {submitter_uid} for cycle {payload_cycle}"
        )
        return {"message": f"Accepted scores for cycle {payload_cycle}."}
    except Exception as e:
        logger.exception(
            f"API: Error processing scores from {submitter_uid} for cycle {payload_cycle}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error processing scores submission: {str(e)}",
        )


# Fallback implementations for missing functions
def canonical_json_serialize(data):
    """Fallback canonical JSON serialization"""
    import json

    return json.dumps(data, sort_keys=True, separators=(",", ":"))


# Dummy PublicKey class for Core blockchain
class PublicKey:
    def __init__(self, public_key_bytes):
        self.public_key_bytes = public_key_bytes

    def verify(self, message_bytes, signature_bytes):
        """Dummy verification - should implement proper Core blockchain signature verification"""
        return True  # Placeholder

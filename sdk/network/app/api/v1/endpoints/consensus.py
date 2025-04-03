# sdk/network/app/api/v1/endpoints/consensus.py
"""
API endpoints cho việc trao đổi thông tin đồng thuận giữa các validator.
"""
from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Annotated
import logging

# --- Import Pydantic model và Dataclasses ---
try:
    from pydantic import BaseModel, Field, ValidationError
    from sdk.core.datatypes import ValidatorScore # Import từ core
except ImportError:
    print("Warning: pydantic or sdk.core.datatypes not found. API models might fail.")
    # Placeholder
    class BaseModel: pass
    class Field: pass
    class ValidatorScore: pass
    class ValidationError(Exception): pass

from sdk.consensus.node import ValidatorNode # Import lớp thực tế
from sdk.network.app.api.v1.endpoints import get_validator_node # Import dependency provider


# --- Định nghĩa Pydantic Model cho Payload ---
class ScoreSubmissionPayload(BaseModel):
    """Dữ liệu điểm số gửi qua API."""
    scores: List[ValidatorScore] = Field(..., description="Danh sách điểm số chi tiết ValidatorScore")
    submitter_validator_uid: str = Field(..., description="UID của validator gửi điểm")
    cycle: int = Field(..., description="Chu kỳ đồng thuận mà điểm số này thuộc về")
    # signature: Optional[str] = Field(None, description="Chữ ký để xác thực người gửi")

    # Thêm validator nếu cần để đảm bảo dữ liệu trong ValidatorScore hợp lệ
    # @validator('scores')
    # def check_scores(cls, v):
    #     if not v:
    #         raise ValueError('Scores list cannot be empty')
    #     # Thêm các kiểm tra khác cho từng score item nếu cần
    #     return v

# --- Router ---
router = APIRouter(
    prefix="/consensus",
    tags=["Consensus P2P"],
)

logger = logging.getLogger(__name__)

# --- API Endpoint ---

@router.post("/receive_scores",
             summary="Nhận điểm số từ Validator khác",
             description="Endpoint để một Validator gửi danh sách điểm số (ValidatorScore) mà nó đã chấm cho các Miner trong một chu kỳ.",
             status_code=status.HTTP_202_ACCEPTED)
async def receive_scores(
    payload: ScoreSubmissionPayload,
    # Sử dụng Annotated và Depends để inject instance ValidatorNode
    node: Annotated[ValidatorNode, Depends(get_validator_node)]
):
    """
    Endpoint để nhận điểm số ValidatorScore từ một validator khác.
    """
    logger.info(f"API: Received scores from {payload.submitter_validator_uid} for cycle {payload.cycle}")

    # --- Logic xác thực người gửi (QUAN TRỌNG) ---
    # 1. Kiểm tra xem submitter_validator_uid có hợp lệ không (có trong danh sách validator đã biết?)
    if payload.submitter_validator_uid not in node.validators_info:
         logger.warning(f"Received scores from unknown validator UID: {payload.submitter_validator_uid}")
         raise HTTPException(
             status_code=status.HTTP_400_BAD_REQUEST,
             detail=f"Unknown submitter validator UID: {payload.submitter_validator_uid}"
         )
    # 2. Kiểm tra chữ ký (nếu có) để đảm bảo tính toàn vẹn và xác thực
    # expected_signer_address = node.validators_info[payload.submitter_validator_uid].address
    # if not payload.signature or not verify_signature(payload.signature, payload.scores, expected_signer_address):
    #     logger.warning(f"Invalid or missing signature from {payload.submitter_validator_uid}")
    #     raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing signature")

    # 3. Kiểm tra xem chu kỳ có hợp lệ không (ví dụ: có phải là chu kỳ hiện tại không?)
    if payload.cycle != node.current_cycle:
        logger.warning(f"Received scores for incorrect cycle {payload.cycle} from {payload.submitter_validator_uid} (current: {node.current_cycle})")
        # Có thể chấp nhận điểm trễ một chút, tùy logic
        # raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Incorrect cycle: {payload.cycle}")

    # Gọi phương thức trên node để thêm điểm số nhận được
    try:
        await node.add_received_score(
             payload.submitter_validator_uid,
             payload.cycle,
             payload.scores
        )
        logger.info(f"Successfully processed {len(payload.scores)} scores from {payload.submitter_validator_uid}")
        return {"message": f"Accepted {len(payload.scores)} scores from {payload.submitter_validator_uid}."}
    except ValidationError as ve: # Bắt lỗi validation Pydantic nếu có
        logger.error(f"API Validation Error processing scores from {payload.submitter_validator_uid}: {ve}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid score data format: {ve}"
        )
    except Exception as e:
        logger.exception(f"API Error processing received scores from {payload.submitter_validator_uid}: {e}")
        # Trả về lỗi server nếu xử lý thất bại
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error processing scores: {e}"
        )


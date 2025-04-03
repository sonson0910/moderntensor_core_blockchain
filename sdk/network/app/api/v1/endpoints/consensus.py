# sdk/network/app/api/v1/endpoints/consensus.py
"""
API endpoints cho việc trao đổi thông tin đồng thuận giữa các validator.
"""
from fastapi import APIRouter, HTTPException, Depends, status # Thêm status
from typing import List, Annotated

# --- Import Pydantic model và Dataclasses ---
# (Pydantic model nên được định nghĩa ở đây hoặc trong schema riêng của API)
try:
    from pydantic import BaseModel, Field
    # Di chuyển ValidatorScore vào đây hoặc tạo schema riêng nếu cần validate khác dataclass
    from sdk.core.datatypes import ValidatorScore # Import từ core

    class ScoreSubmissionPayload(BaseModel):
        """Dữ liệu điểm số gửi qua API."""
        scores: List[ValidatorScore] = Field(..., description="Danh sách điểm số chi tiết")
        submitter_validator_uid: str = Field(..., description="UID của validator gửi điểm")
        cycle: int = Field(..., description="Chu kỳ đồng thuận mà điểm số này thuộc về")
        # Có thể thêm chữ ký để xác thực
        # signature: Optional[str] = None
except ImportError:
    print("Warning: pydantic not installed. API Payload model not defined.")
    # Placeholder nếu không có Pydantic
    class ValidatorScore: pass
    class ScoreSubmissionPayload:
         scores: List[ValidatorScore]
         submitter_validator_uid: str
         cycle: int

# --- Import Node Instance (Cần cơ chế Dependency Injection thực tế) ---
# from ....consensus import ValidatorNode # Đường dẫn tương đối có thể khác
# from ..dependencies import get_validator_node # Ví dụ hàm inject dependency

# --- Router ---
router = APIRouter(
    prefix="/consensus",
    tags=["Consensus P2P"],
)

# --- Biến toàn cục hoặc Dependency Injection để truy cập Node ---
# Đây là cách đơn giản, trong ứng dụng lớn nên dùng Dependency Injection
# Cần khởi tạo validator_node_instance ở đâu đó trong ứng dụng FastAPI chính
# và inject vào đây thông qua Depends
validator_node_instance: 'ValidatorNode' = None # Kiểu dữ liệu tạm thời

# --- Dependency Function (Ví dụ) ---
async def get_validator_node_instance() -> 'ValidatorNode':
    """Lấy instance ValidatorNode (cần triển khai logic inject thực tế)."""
    if validator_node_instance is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Validator node service is not available."
        )
    return validator_node_instance

# --- API Endpoint ---

@router.post("/receive_scores", status_code=status.HTTP_202_ACCEPTED)
async def receive_scores(
    payload: ScoreSubmissionPayload,
    node: Annotated['ValidatorNode', Depends(get_validator_node_instance)] # Inject node
):
    """
    Endpoint để nhận điểm số ValidatorScore từ một validator khác.
    """
    print(f"API: Received scores from {payload.submitter_validator_uid} for cycle {payload.cycle}")

    # --- Cần thêm logic xác thực người gửi (ví dụ: kiểm tra chữ ký, IP,...) ---
    # if not verify_signature(payload.signature, ...):
    #     raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

    # Gọi phương thức trên node để thêm điểm số nhận được
    try:
        # Chạy bất đồng bộ nếu add_received_score là async
        await node.add_received_score(
             payload.submitter_validator_uid,
             payload.cycle,
             payload.scores
        )
        return {"message": f"Accepted {len(payload.scores)} scores from {payload.submitter_validator_uid}."}
    except Exception as e:
        print(f"API Error processing received scores: {e}")
        # Trả về lỗi server nếu xử lý thất bại
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing scores: {e}"
        )


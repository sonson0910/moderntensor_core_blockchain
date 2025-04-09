# File mới: sdk/network/app/api/v1/endpoints/miner_comms.py

import logging
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status

# Import các model và dependencies
from sdk.network.server import ResultModel # Model kết quả từ miner
from sdk.core.datatypes import MinerResult # Datatype nội bộ
from sdk.consensus.node import ValidatorNode
from sdk.network.app.dependencies import get_validator_node
import time

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/miner/submit_result",
             summary="Miner gửi kết quả Task",
             description="Endpoint để Miner gửi đối tượng ResultModel sau khi hoàn thành task.",
             status_code=status.HTTP_202_ACCEPTED)
async def submit_miner_result(
    result_payload: ResultModel, # Nhận payload từ miner
    node: Annotated[ValidatorNode, Depends(get_validator_node)]
):
    """
    Nhận kết quả từ Miner, chuyển đổi thành MinerResult và thêm vào node.
    """
    logger.info(f"API: Received result submission for task {result_payload.result_id} from miner {result_payload.miner_id}")
    log_task_id = getattr(result_payload, 'task_id', getattr(result_payload, 'result_id', 'N/A'))
    log_miner_id = getattr(result_payload, 'miner_id', 'N/A')
    logger.info(f"API: Received result submission - TaskID(sent): {log_task_id}, MinerID(sent): {log_miner_id}")

    # --- Chuyển đổi ResultModel (API) sang MinerResult (Core) ---
    # Cần ánh xạ các trường. Giả sử result_id chứa task_id
    # Cần kiểm tra lại ResultModel xem có đủ thông tin không
    # Giả sử result_payload.result_id thực chất là task_id
    # Giả sử result_payload.description chứa dữ liệu kết quả chính
    try:
        # --- Chuyển đổi ResultModel sang MinerResult ---
        # Ánh xạ các trường cẩn thận
        task_id_internal = getattr(result_payload, 'task_id', result_payload.result_id)
        internal_result = MinerResult(
            task_id=getattr(result_payload, 'task_id', task_id_internal), # Ưu tiên task_id nếu có
            miner_uid=log_miner_id,
            result_data={ # Tạo dict chứa các thông tin kết quả
                "description": getattr(result_payload, 'description', None),
                "processing_time": getattr(result_payload, 'processing_time', None),
                "payload_data": getattr(result_payload, 'data', None) # Lấy dữ liệu gốc nếu có
            },
            timestamp_received=time.time()
        )
        logger.debug(f"Converted to internal MinerResult: {internal_result}")

        # --- Gọi phương thức của Node ---
        # Lời gọi await nằm TRONG try
        success = await node.add_miner_result(internal_result)

        # --- Xử lý kết quả trả về ---
        if success: # Nếu trả về True
            logger.info(f"Result for task {internal_result.task_id} successfully added by node.")
            return {"message": f"Result for task {internal_result.task_id} accepted."}
        else: # Nếu trả về False hoặc None
            logger.warning(f"Result for task {internal_result.task_id} rejected by node.")
            # Trả về lỗi 400
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Result rejected by validator node.")

    except HTTPException as http_exc:
        # Raise lại HTTPException đã được tạo (ví dụ lỗi 400 ở trên)
        raise http_exc
    except Exception as e:
        # Bắt các lỗi khác (ví dụ lỗi convert hoặc lỗi từ add_miner_result side_effect)
        logger.exception(f"API: Internal error processing result submission for task {log_task_id}: {e}")
        # Trả về lỗi 500
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error processing result.")
    # ----------------------------------------------------------
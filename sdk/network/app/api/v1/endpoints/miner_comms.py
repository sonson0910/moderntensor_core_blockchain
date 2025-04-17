# File mới: sdk/network/app/api/v1/endpoints/miner_comms.py

import logging
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status

# Import các model và dependencies
from sdk.network.server import ResultModel  # Model kết quả từ miner
from sdk.core.datatypes import MinerResult  # Datatype nội bộ
from sdk.consensus.node import ValidatorNode
from sdk.network.app.dependencies import get_validator_node
import time

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/miner/submit_result",
    summary="Miner gửi kết quả Task",
    description="Endpoint để Miner gửi đối tượng ResultModel sau khi hoàn thành task.",
    status_code=status.HTTP_202_ACCEPTED,
)
async def submit_miner_result(
    result_payload: ResultModel,  # Nhận payload từ miner
    node: Annotated[ValidatorNode, Depends(get_validator_node)],
):
    """
    Nhận kết quả từ Miner (ResultModel), chuyển đổi thành MinerResult và thêm vào node.
    """
    # Đọc trực tiếp từ ResultModel đã được xác thực
    log_task_id = result_payload.task_id
    log_miner_uid = result_payload.miner_uid
    log_result_data_summary = str(result_payload.result_data)[
        :100
    ]  # Log một phần result_data

    logger.info(
        f"API: Received result submission for task [yellow]{log_task_id}[/yellow] from miner [cyan]{log_miner_uid}[/cyan]"
    )
    logger.debug(f"   Result Data Received: {log_result_data_summary}...")

    # --- Chuyển đổi ResultModel (API) sang MinerResult (Core) ---
    try:
        internal_result = MinerResult(
            task_id=log_task_id,
            miner_uid=log_miner_uid,
            # Gán trực tiếp dict result_data nhận được
            result_data=result_payload.result_data,
            timestamp_received=time.time(),
        )
        logger.debug(f"Converted to internal MinerResult: {internal_result}")

        # --- Gọi phương thức của Node ---
        success = await node.add_miner_result(internal_result)

        # --- Xử lý kết quả trả về ---
        if success:
            logger.info(
                f"✅ Result for task [yellow]{internal_result.task_id}[/yellow] successfully added by node."
            )
            return {"message": f"Result for task {internal_result.task_id} accepted."}
        else:
            logger.warning(
                f"⚠️ Result for task [yellow]{internal_result.task_id}[/yellow] rejected by node."
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Result rejected by validator node (e.g., duplicate, wrong cycle, invalid data).",
            )

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        # Log dùng task_id nhận được
        logger.exception(
            f"💥 API: Internal error processing result submission for task [yellow]{log_task_id}[/yellow]: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error processing result.",
        )
    # ----------------------------------------------------------

# sdk/api/task_exchange_service.py

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional
import uvicorn

app = FastAPI()

# Định nghĩa model cho Task với các trường bổ sung
class TaskModel(BaseModel):
    """
    Pydantic model cho dữ liệu task gửi từ validator đến miner.
    """
    task_id: str = Field(..., description="ID duy nhất của task")
    description: str = Field(..., description="Mô tả chi tiết task")
    deadline: Optional[str] = Field(None, description="Thời hạn hoàn thành task")
    priority: Optional[int] = Field(None, description="Độ ưu tiên của task (1-5)")

# Định nghĩa model cho Result với các trường bổ sung
class ResultModel(BaseModel):
    """
    Pydantic model cho dữ liệu kết quả gửi từ miner đến validator.
    """
    result_id: str = Field(..., description="ID duy nhất của kết quả")
    description: str = Field(..., description="Mô tả chi tiết kết quả")
    processing_time: Optional[float] = Field(None, description="Thời gian xử lý (giây)")
    miner_id: Optional[str] = Field(None, description="ID của miner thực hiện task")

# Endpoint để gửi task từ validator đến miner
@app.post("/send-task")
async def send_task(
    task: TaskModel,
    task_file: UploadFile = File(None)
):
    """
    Endpoint để validator gửi task cho miner.

    Args:
        task (TaskModel): Dữ liệu task chứa các thông tin chi tiết.
        task_file (UploadFile, optional): Tệp tin đính kèm (nếu có).

    Returns:
        JSONResponse: Xác nhận với thông tin chi tiết của task.
    """
    if task_file:
        file_content = await task_file.read()
        print(f"Received task file: {task_file.filename}, size: {len(file_content)} bytes")
    else:
        print("No task file provided.")

    # Log chi tiết task
    print(f"Task sent to miner: ID={task.task_id}, Description={task.description}, "
          f"Deadline={task.deadline}, Priority={task.priority}")

    return JSONResponse(content={
        "message": "Task sent to miner",
        "task_id": task.task_id,
        "description": task.description,
        "deadline": task.deadline,
        "priority": task.priority,
        "file": task_file.filename if task_file else None
    })

# Endpoint để nhận kết quả từ miner
@app.post("/submit-result")
async def submit_result(
    result: ResultModel,
    result_file: UploadFile = File(None)
):
    """
    Endpoint để miner gửi kết quả về validator.

    Args:
        result (ResultModel): Dữ liệu kết quả chứa các thông tin chi tiết.
        result_file (UploadFile, optional): Tệp tin đính kèm (nếu có).

    Returns:
        JSONResponse: Xác nhận với thông tin chi tiết của kết quả.
    """
    if result_file:
        file_content = await result_file.read()
        print(f"Received result file: {result_file.filename}, size: {len(file_content)} bytes")
    else:
        print("No result file provided.")

    # Log chi tiết kết quả
    print(f"Result received: ID={result.result_id}, Description={result.description}, "
          f"Processing Time={result.processing_time}, Miner ID={result.miner_id}")

    return JSONResponse(content={
        "message": "Result submitted to validator",
        "result_id": result.result_id,
        "description": result.description,
        "processing_time": result.processing_time,
        "miner_id": result.miner_id,
        "file": result_file.filename if result_file else None
    })

# Chạy server FastAPI
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
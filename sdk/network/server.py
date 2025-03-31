# sdk/api/task_exchange_service.py

from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError
from typing import Optional
import uvicorn
import json

app = FastAPI()

# Lưu trữ tạm thời task và result
current_task = None
current_result = None

# Định nghĩa model cho Task với các trường bổ sung
class TaskModel(BaseModel):
    """
    Pydantic model for task data sent from validator to miner.
    """
    task_id: str = Field(..., description="Unique ID of the task")
    description: str = Field(..., description="Detailed description of the task")
    deadline: Optional[str] = Field(None, description="Deadline for task completion")
    priority: Optional[int] = Field(None, description="Priority of the task (1-5)")

# Định nghĩa model cho Result với các trường bổ sung
class ResultModel(BaseModel):
    """
    Pydantic model for result data sent from miner to validator.
    """
    result_id: str = Field(..., description="Unique ID of the result")
    description: str = Field(..., description="Detailed description of the result")
    processing_time: Optional[float] = Field(None, description="Processing time in seconds")
    miner_id: Optional[str] = Field(None, description="ID of the miner who processed the task")

# Endpoint để validator gửi task cho miner
@app.post("/send-task")
async def send_task(
    task_json: str = Form(..., alias="task"),
    task_file: UploadFile = File(None)
):
    """
    Endpoint for the validator to send a task to the miner.
    Expects 'task' as a form field containing a JSON string for TaskModel,
    and an optional 'task_file'.

    Args:
        task_json (str): JSON string representing the TaskModel, sent via form field named 'task'.
        task_file (UploadFile, optional): Optional file attached to the task.

    Returns:
        JSONResponse: Confirmation with detailed task information or error message.
    """
    try:
        task_data = json.loads(task_json)
        task = TaskModel(**task_data)
    except json.JSONDecodeError:
        print(f"Error decoding JSON from task field: {task_json}")
        return JSONResponse(status_code=400, content={"message": "Invalid JSON format for task field"})
    except ValidationError as e:
        print(f"Validation error for task data: {task_data} - Errors: {e.errors()}")
        return JSONResponse(status_code=422, content={"detail": f"Validation error for task: {e.errors()}"})
    except Exception as e:
        print(f"Unexpected error processing task: {e}")
        return JSONResponse(status_code=500, content={"message": f"Internal server error: {e}"})

    global current_task
    if task_file:
        file_content = await task_file.read()
        print(f"Received task file: {task_file.filename}, size: {len(file_content)} bytes")
    else:
        print("No task file provided.")

    current_task = {
        "task_id": task.task_id,
        "description": task.description,
        "deadline": task.deadline,
        "priority": task.priority,
        "file": task_file.filename if task_file else None
    }

    print(f"Task received and stored: ID={task.task_id}, Description={task.description}, "
          f"Deadline={task.deadline}, Priority={task.priority}")

    return JSONResponse(content={
        "message": "Task sent to miner",
        "task_id": task.task_id,
        "description": task.description,
        "deadline": task.deadline,
        "priority": task.priority,
        "file": task_file.filename if task_file else None
    })

# Endpoint để miner lấy task từ validator
@app.get("/get-task")
async def get_task():
    """
    Endpoint for the miner to retrieve the latest task from the validator.

    Returns:
        JSONResponse: The latest task data or a message indicating no task is available.
    """
    global current_task
    if current_task:
        task = current_task
        # Reset current_task để tránh lấy lại task cũ
        current_task = None
        return JSONResponse(content={
            "message": "Task retrieved",
            "task": task
        })
    else:
        return JSONResponse(content={
            "message": "No task available"
        })

# Endpoint để miner gửi kết quả về validator
@app.post("/submit-result")
async def submit_result(
    # Explicitly state that 'result' comes from a form field named 'result'
    # and needs to be parsed from JSON
    result_json: str = Form(..., alias="result"),
    result_file: UploadFile = File(None)
):
    """
    Endpoint for the miner to submit the result to the validator.
    Expects 'result' as a form field containing a JSON string for ResultModel,
    and an optional 'result_file'.

    Args:
        result_json (str): JSON string representing the ResultModel, sent via form field named 'result'.
        result_file (UploadFile, optional): Optional file attached to the result.

    Returns:
        JSONResponse: Confirmation with detailed result information or error message.
    """
    try:
        # Manually parse the JSON string from the form field
        result_data = json.loads(result_json)
        # Validate the parsed data using the Pydantic model
        result = ResultModel(**result_data)
    except json.JSONDecodeError:
        print(f"Error decoding JSON from result field: {result_json}")
        return JSONResponse(status_code=400, content={"message": "Invalid JSON format for result field"})
    except ValidationError as e:
        print(f"Validation error for result data: {result_data} - Errors: {e.errors()}")
        return JSONResponse(status_code=422, content={"detail": f"Validation error for result: {e.errors()}"})
    except Exception as e:
        print(f"Unexpected error processing result: {e}")
        return JSONResponse(status_code=500, content={"message": f"Internal server error: {e}"})

    global current_result
    if result_file:
        file_content = await result_file.read()
        print(f"Received result file: {result_file.filename}, size: {len(file_content)} bytes")
    else:
        print("No result file provided.")

    # Lưu kết quả để validator có thể lấy (sử dụng dữ liệu từ đối tượng result đã được xác thực)
    current_result = {
        "result_id": result.result_id,
        "description": result.description,
        "processing_time": result.processing_time,
        "miner_id": result.miner_id,
        "file": result_file.filename if result_file else None
    }

    print(f"Result received and stored: ID={result.result_id}, Description={result.description}, "
          f"Processing Time={result.processing_time}, Miner ID={result.miner_id}")

    # Trả về thông tin từ đối tượng result đã được xác thực
    return JSONResponse(content={
        "message": "Result submitted to validator",
        "result_id": result.result_id,
        "description": result.description,
        "processing_time": result.processing_time,
        "miner_id": result.miner_id,
        "file": result_file.filename if result_file else None
    })

# Endpoint để validator lấy kết quả từ miner
@app.get("/get-result")
async def get_result():
    """
    Endpoint for the validator to retrieve the latest result from the miner.

    Returns:
        JSONResponse: The latest result data or a message indicating no result is available.
    """
    global current_result
    if current_result:
        result = current_result
        # Reset current_result để tránh lấy lại kết quả cũ
        current_result = None
        return JSONResponse(content={
            "message": "Result retrieved",
            "result": result
        })
    else:
        return JSONResponse(content={
            "message": "No result available"
        })

# Chạy server FastAPI
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
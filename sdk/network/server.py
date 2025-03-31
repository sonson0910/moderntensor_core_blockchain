from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError
from typing import Optional
import uvicorn
import json

# Initialize the FastAPI application
app = FastAPI()

# Temporary storage for task and result data
current_task = None
current_result = None

# Define the Pydantic model for Task data structure
class TaskModel(BaseModel):
    """
    Pydantic model for task data sent from validator to miner.
    This model defines the structure and validation rules for task-related data.
    """
    task_id: str = Field(..., description="Unique identifier for the task, must be provided")
    description: str = Field(..., description="Detailed description of the task, must be provided")
    deadline: Optional[str] = Field(None, description="Deadline for task completion, optional (e.g., '2024-12-31')")
    priority: Optional[int] = Field(None, description="Priority level of the task (1-5), optional")

# Define the Pydantic model for Result data structure
class ResultModel(BaseModel):
    """
    Pydantic model for result data sent from miner to validator.
    This model defines the structure and validation rules for result-related data.
    """
    result_id: str = Field(..., description="Unique identifier for the result, must be provided")
    description: str = Field(..., description="Detailed description of the result, must be provided")
    processing_time: Optional[float] = Field(None, description="Time taken to process the task in seconds, optional")
    miner_id: Optional[str] = Field(None, description="Identifier of the miner who processed the task, optional")

# Endpoint for the validator to send a task to the miner
@app.post("/send-task")
async def send_task(
    task_json: str = Form(..., alias="task"),
    task_file: UploadFile = File(None)
):
    """
    Endpoint for the validator to send a task to the miner.
    Expects 'task' as a form field containing a JSON string representing the TaskModel,
    and an optional 'task_file' for additional file data.

    Args:
        task_json (str): JSON string representing the TaskModel, sent via form field named 'task'.
        task_file (UploadFile, optional): Optional file attached to the task (e.g., a dataset or document).

    Returns:
        JSONResponse: Confirmation with detailed task information or an error message if validation fails.
    """
    try:
        # Parse the JSON string from the form field into a Python dictionary
        task_data = json.loads(task_json)
        # Validate the task data against the TaskModel
        task = TaskModel(**task_data)
    except json.JSONDecodeError:
        # Handle invalid JSON format in the task field
        print(f"Error decoding JSON from task field: {task_json}")
        return JSONResponse(status_code=400, content={"message": "Invalid JSON format for task field"})
    except ValidationError as e:
        # Handle validation errors if task data doesn't match TaskModel
        print(f"Validation error for task data: {task_data} - Errors: {e.errors()}")
        return JSONResponse(status_code=422, content={"detail": f"Validation error for task: {e.errors()}"})
    except Exception as e:
        # Handle any other unexpected errors
        print(f"Unexpected error processing task: {e}")
        return JSONResponse(status_code=500, content={"message": f"Internal server error: {e}"})

    global current_task
    if task_file:
        # Read the content of the uploaded file (if provided)
        file_content = await task_file.read()
        print(f"Received task file: {task_file.filename}, size: {len(file_content)} bytes")
    else:
        print("No task file provided.")

    # Store the task data in the global variable for later retrieval
    current_task = {
        "task_id": task.task_id,
        "description": task.description,
        "deadline": task.deadline,
        "priority": task.priority,
        "file": task_file.filename if task_file else None
    }

    # Log the received task details
    print(f"Task received and stored: ID={task.task_id}, Description={task.description}, "
          f"Deadline={task.deadline}, Priority={task.priority}")

    # Return a success response with task details
    return JSONResponse(content={
        "message": "Task sent to miner",
        "task_id": task.task_id,
        "description": task.description,
        "deadline": task.deadline,
        "priority": task.priority,
        "file": task_file.filename if task_file else None
    })

# Endpoint for the miner to retrieve the latest task
@app.get("/get-task")
async def get_task():
    """
    Endpoint for the miner to retrieve the latest task from the validator.

    Returns:
        JSONResponse: The latest task data if available, or a message indicating no task is available.
    """
    global current_task
    if current_task:
        # Retrieve and clear the current task to prevent duplicate retrieval
        task = current_task
        current_task = None
        return JSONResponse(content={
            "message": "Task retrieved",
            "task": task
        })
    else:
        # Return a message if no task is available
        return JSONResponse(content={
            "message": "No task available"
        })

# Endpoint for the miner to submit a result to the validator
@app.post("/submit-result")
async def submit_result(
    result_json: str = Form(..., alias="result"),
    result_file: UploadFile = File(None)
):
    """
    Endpoint for the miner to submit the result to the validator.
    Expects 'result' as a form field containing a JSON string representing the ResultModel,
    and an optional 'result_file' for additional file data.

    Args:
        result_json (str): JSON string representing the ResultModel, sent via form field named 'result'.
        result_file (UploadFile, optional): Optional file attached to the result (e.g., output data).

    Returns:
        JSONResponse: Confirmation with detailed result information or an error message if validation fails.
    """
    try:
        # Parse the JSON string from the form field into a Python dictionary
        result_data = json.loads(result_json)
        # Validate the result data against the ResultModel
        result = ResultModel(**result_data)
    except json.JSONDecodeError:
        # Handle invalid JSON format in the result field
        print(f"Error decoding JSON from result field: {result_json}")
        return JSONResponse(status_code=400, content={"message": "Invalid JSON format for result field"})
    except ValidationError as e:
        # Handle validation errors if result data doesn't match ResultModel
        print(f"Validation error for result data: {result_data} - Errors: {e.errors()}")
        return JSONResponse(status_code=422, content={"detail": f"Validation error for result: {e.errors()}"})
    except Exception as e:
        # Handle any other unexpected errors
        print(f"Unexpected error processing result: {e}")
        return JSONResponse(status_code=500, content={"message": f"Internal server error: {e}"})

    global current_result
    if result_file:
        # Read the content of the uploaded file (if provided)
        file_content = await result_file.read()
        print(f"Received result file: {result_file.filename}, size: {len(file_content)} bytes")
    else:
        print("No result file provided.")

    # Store the result data in the global variable for later retrieval
    current_result = {
        "result_id": result.result_id,
        "description": result.description,
        "processing_time": result.processing_time,
        "miner_id": result.miner_id,
        "file": result_file.filename if result_file else None
    }

    # Log the received result details
    print(f"Result received and stored: ID={result.result_id}, Description={result.description}, "
          f"Processing Time={result.processing_time}, Miner ID={result.miner_id}")

    # Return a success response with result details
    return JSONResponse(content={
        "message": "Result submitted to validator",
        "result_id": result.result_id,
        "description": result.description,
        "processing_time": result.processing_time,
        "miner_id": result.miner_id,
        "file": result_file.filename if result_file else None
    })

# Endpoint for the validator to retrieve the latest result
@app.get("/get-result")
async def get_result():
    """
    Endpoint for the validator to retrieve the latest result from the miner.

    Returns:
        JSONResponse: The latest result data if available, or a message indicating no result is available.
    """
    global current_result
    if current_result:
        # Retrieve and clear the current result to prevent duplicate retrieval
        result = current_result
        current_result = None
        return JSONResponse(content={
            "message": "Result retrieved",
            "result": result
        })
    else:
        # Return a message if no result is available
        return JSONResponse(content={
            "message": "No result available"
        })

# Run the FastAPI server
if __name__ == "__main__":
    # Start the server on host 0.0.0.0 and port 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)
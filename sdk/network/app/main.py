# sdk/network/app/main.py
from fastapi import FastAPI
import asyncio
import logging
import time
import Optional

# Import các thành phần cần thiết
from .api.v1.routes import api_router
from .dependencies import set_validator_node_instance # Hàm để inject instance
# Import lớp ValidatorNode và ValidatorInfo
from sdk.consensus.node import ValidatorNode # Đường dẫn tương đối có thể khác
from sdk.core.datatypes import ValidatorInfo

# --- Cấu hình logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# --- Khởi tạo FastAPI app ---
app = FastAPI(
    title="Moderntensor Network API",
    description="API endpoints for Moderntensor network communication, including P2P consensus.",
    version="0.1.0"
)

# --- Biến toàn cục hoặc đối tượng quản lý state ---
# Giữ instance node validator chính chạy trong tiến trình này
main_validator_node_instance: Optional[ValidatorNode] = None

# --- Sự kiện Startup ---
@app.on_event("startup")
async def startup_event():
    """Khởi tạo các tài nguyên cần thiết khi ứng dụng bắt đầu."""
    global main_validator_node_instance
    logger.info("FastAPI application starting up...")

    # --- Khởi tạo Validator Node ---
    # Cần logic để load thông tin validator (UID, keys,...) và context Cardano
    # Ví dụ:
    if ValidatorInfo and ValidatorNode:
        try:
            # Load thông tin từ file cấu hình hoặc key file
            validator_uid = "V_THIS_NODE" # Lấy từ config/key
            validator_address = "addr_this_node..." # Lấy từ config/key
            api_endpoint = "http://127.0.0.1:8000" # Địa chỉ API của chính node này, lấy từ config
            # cardano_ctx = await initialize_cardano_context() # Hàm khởi tạo context
            # node_config = load_app_config() # Hàm load config

            my_validator_info = ValidatorInfo(
                uid=validator_uid,
                address=validator_address,
                api_endpoint=api_endpoint
                # Load các thông tin khác như stake, trust, weight nếu cần khởi tạo ban đầu
            )

            main_validator_node_instance = ValidatorNode(
                validator_info=my_validator_info,
                cardano_context=None, # Thay bằng cardano_ctx thực tế
                config=None # Thay bằng node_config thực tế
            )

            # Inject instance vào dependency provider cho API endpoints sử dụng
            set_validator_node_instance(main_validator_node_instance)
            logger.info(f"ValidatorNode instance '{validator_uid}' initialized and injected.")

            # --- Khởi chạy vòng lặp chính của Validator Node ---
            # Chạy trong một background task của asyncio
            logger.info("Starting main consensus loop...")
            asyncio.create_task(run_main_node_loop(main_validator_node_instance))

        except Exception as e:
            logger.exception(f"Failed to initialize ValidatorNode: {e}")
            # Có thể quyết định dừng ứng dụng nếu node không khởi tạo được
            # raise SystemExit("ValidatorNode initialization failed.")
    else:
        logger.error("ValidatorNode or ValidatorInfo not available. Cannot initialize node.")


# --- Sự kiện Shutdown ---
@app.on_event("shutdown")
async def shutdown_event():
    """Dọn dẹp tài nguyên khi ứng dụng tắt."""
    logger.info("FastAPI application shutting down...")
    if main_validator_node_instance and hasattr(main_validator_node_instance, 'http_client'):
        await main_validator_node_instance.http_client.aclose()
        logger.info("HTTP client closed.")
    # Thêm các bước dọn dẹp khác nếu cần


# --- Hàm chạy vòng lặp chính của Node ---
async def run_main_node_loop(node: ValidatorNode):
    """Hàm chạy vòng lặp đồng thuận chính trong background."""
    if not node: return
    try:
        while True:
            cycle_start_time = time.time()
            await node.run_cycle()
            cycle_duration = time.time() - cycle_start_time
            # Lấy cycle_interval từ config hoặc node
            cycle_interval_seconds = METAGRAPH_UPDATE_INTERVAL_MINUTES * 60
            wait_time = max(10, cycle_interval_seconds - cycle_duration) # Đợi ít nhất 10s
            logger.info(f"Cycle duration: {cycle_duration:.1f}s. Waiting {wait_time:.1f}s for next cycle...")
            await asyncio.sleep(wait_time)
    except asyncio.CancelledError:
        logger.info("Main node loop cancelled.")
    except Exception as e:
        logger.exception(f"Exception in main node loop: {e}")
    finally:
        logger.info("Main node loop finished.")


# --- Include Routers ---
# Đảm bảo include router sau khi các dependency có thể đã sẵn sàng (nếu cần)
app.include_router(api_router)


# --- Điểm chạy chính (sử dụng uvicorn) ---
# if __name__ == "__main__":
#     import uvicorn
#     # Port này là port chính của FastAPI app, nơi nhận request từ bên ngoài
#     # và cũng là nơi các validator khác gửi điểm số đến (/v1/consensus/receive_scores)
#     uvicorn.run(app, host="0.0.0.0", port=8000)

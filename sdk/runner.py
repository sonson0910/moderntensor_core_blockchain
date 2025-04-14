import uvicorn
import asyncio
import logging
import os
import sys
import time
from typing import Type, Optional, Dict, Any
from fastapi import FastAPI
from pathlib import Path

# Import các thành phần cần thiết từ SDK
# Lưu ý: Các đường dẫn import này là tương đối trong SDK
from .network.app.api.v1.routes import api_router
from .network.app.dependencies import set_validator_node_instance
from .consensus.node import ValidatorNode  # Import lớp base
from .core.datatypes import ValidatorInfo
from .keymanager.decryption_utils import decode_hotkey_skey
from .service.context import get_chain_context
from .config.settings import (
    settings as sdk_settings,
)  # Dùng settings SDK cho giá trị mặc định
from pycardano import ExtendedSigningKey, BlockFrostChainContext, Network

logger = logging.getLogger(__name__)


class ValidatorRunner:
    """
    Lớp đóng gói việc khởi tạo và chạy một Validator Node tích hợp (Logic + API).
    Nó nhận vào lớp Validator cụ thể của subnet và các cấu hình.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Khởi tạo Runner.

        Args:
            config (Dict[str, Any]): Dictionary chứa các cấu hình cần thiết:
                - validator_class (Type[ValidatorNode]): Lớp validator cụ thể (vd: Subnet1Validator).
                - host (str): Host IP để API server lắng nghe (vd: "127.0.0.1").
                - port (int): Cổng để API server lắng nghe (vd: 8001).
                - validator_uid (str): UID của validator.
                - validator_address (str): Địa chỉ Cardano của validator.
                - validator_api_endpoint (str): URL công khai của API.
                - hotkey_base_dir (str): Đường dẫn thư mục chứa coldkeys.
                - coldkey_name (str): Tên coldkey.
                - hotkey_name (str): Tên hotkey.
                - password (str): Mật khẩu hotkey.
                - blockfrost_project_id (str): ID dự án Blockfrost.
                - network (Network): Mạng Cardano (Testnet/Mainnet).
                # Thêm các cấu hình khác nếu lớp validator cụ thể yêu cầu
        """
        self.config = config
        self.validator_class: Type[ValidatorNode] = config.get(
            "validator_class", ValidatorNode
        )  # Lấy lớp validator, mặc định là base
        self.app = FastAPI(
            title=f"Moderntensor Validator API - {self.validator_class.__name__}",
            description=f"API server and consensus node runner for {self.validator_class.__name__}.",
            # version= # Có thể lấy version từ SDK
        )
        self.validator_node_instance: Optional[ValidatorNode] = None
        self.main_loop_task: Optional[asyncio.Task] = None

        self._setup_app()

    def _setup_app(self):
        """Thiết lập ứng dụng FastAPI, bao gồm sự kiện startup/shutdown và router."""

        @self.app.on_event("startup")
        async def startup_event():
            logger.info(
                f"Runner: FastAPI application startup for {self.validator_class.__name__}..."
            )
            try:
                # --- Load Config & Components ---
                cfg = self.config
                base_dir = cfg["hotkey_base_dir"]
                coldkey_name = cfg["coldkey_name"]
                hotkey_name = cfg["hotkey_name"]
                password = cfg["password"]
                validator_uid = cfg["validator_uid"]
                validator_address = cfg["validator_address"]
                api_endpoint = cfg["validator_api_endpoint"]
                bf_project_id = cfg["blockfrost_project_id"]
                network = cfg["network"]

                # --- Load Keys ---
                logger.info(f"Runner: Loading keys for hotkey '{hotkey_name}'...")
                payment_esk, stake_esk = decode_hotkey_skey(
                    base_dir, coldkey_name, hotkey_name, password
                )
                if not payment_esk:
                    raise ValueError("Failed to decode payment signing key.")
                logger.info("Runner: Signing keys loaded.")

                # --- Get Context ---
                logger.info(
                    f"Runner: Initializing Cardano context (Network: {network.name})..."
                )
                # Cần đảm bảo get_chain_context sử dụng đúng project_id
                # Có thể cần sửa get_chain_context hoặc truyền project_id vào đây
                cardano_context = get_chain_context(method="blockfrost")
                if not cardano_context:
                    raise RuntimeError("get_chain_context returned None.")
                # cardano_context.network = network # Đảm bảo đúng network
                logger.info("Runner: Cardano context initialized.")

                # --- Create ValidatorInfo ---
                validator_info = ValidatorInfo(
                    uid=validator_uid,
                    address=validator_address,
                    api_endpoint=api_endpoint,
                )

                # --- Instantiate the SPECIFIC Validator Class ---
                logger.info(
                    f"Runner: Instantiating {self.validator_class.__name__} '{validator_uid}'..."
                )
                self.validator_node_instance = self.validator_class(
                    validator_info=validator_info,
                    cardano_context=cardano_context,
                    signing_key=payment_esk,  # type: ignore
                    stake_signing_key=stake_esk,  # type: ignore
                    # Truyền thêm config vào validator nếu lớp đó yêu cầu
                )
                # --- Inject instance for API endpoints ---
                set_validator_node_instance(self.validator_node_instance)
                logger.info("Runner: Validator instance initialized and injected.")

                # --- Start Background Consensus Loop ---
                logger.info(
                    "Runner: Starting main consensus loop as background task..."
                )
                self.main_loop_task = asyncio.create_task(self._run_main_node_loop())
                logger.info("Runner: Consensus loop background task started.")

            except Exception as e:
                logger.exception(f"Runner: FATAL ERROR during validator startup: {e}")
                # Cân nhắc dừng hẳn server nếu khởi tạo lỗi
                # raise SystemExit("Failed to start validator node.") from e

        @self.app.on_event("shutdown")
        async def shutdown_event():
            logger.info(
                f"Runner: FastAPI application shutting down for {self.validator_class.__name__}..."
            )
            if self.main_loop_task and not self.main_loop_task.done():
                logger.info("Runner: Cancelling main node loop task...")
                self.main_loop_task.cancel()
                try:
                    await self.main_loop_task
                except asyncio.CancelledError:
                    logger.info("Runner: Main node loop task cancelled successfully.")
            # Đóng http client của node instance
            if self.validator_node_instance and hasattr(
                self.validator_node_instance, "http_client"
            ):
                if self.validator_node_instance.http_client:
                    try:
                        await self.validator_node_instance.http_client.aclose()
                        logger.info("Runner: Node HTTP client closed.")
                    except Exception as e_close:
                        logger.error(
                            f"Runner: Error closing node HTTP client: {e_close}"
                        )

        # Include API routes từ SDK
        self.app.include_router(api_router)


    async def _run_main_node_loop(
        self,
    ):  # Hoặc async def run_main_node_loop(node: ValidatorNode):
        """Chạy vòng lặp đồng thuận chính trong background."""
        node = self.validator_node_instance  # Hoặc dùng node từ tham số
        if not node:
            logger.error("Runner: Validator node instance not available for main loop.")
            return

        node_settings = getattr(node, "settings", sdk_settings)

        try:
            await asyncio.sleep(5)  # Chờ API sẵn sàng (có thể giữ lại)
            while True:
                # >>> BỎ PHẦN TÍNH TOÁN THỜI GIAN VÀ SLEEP Ở ĐÂY <<<
                # cycle_start_time = time.time()
                await node.run_cycle()  # Chỉ cần gọi run_cycle
                # cycle_duration = time.time() - cycle_start_time
                # cycle_interval_minutes = getattr(...)
                # cycle_interval_seconds = ...
                # min_wait = getattr(...)
                # wait_time = max(min_wait, cycle_interval_seconds - cycle_duration)
                # logger.info(f"Cycle {node.current_cycle -1} duration: {cycle_duration:.1f}s. Waiting {wait_time:.1f}s for next cycle...")
                # await asyncio.sleep(wait_time) # <<< BỎ DÒNG NÀY >>>
        except asyncio.CancelledError:
            logger.info("Runner: Main node loop cancelled.")
        except Exception as e:
            logger.exception(f"Runner: Exception in main node loop: {e}")
        finally:
            logger.info("Runner: Main node loop finished.")

    def run(self):
        """Khởi động Uvicorn server."""
        host = self.config.get("host", "127.0.0.1")
        port = self.config.get("port", 8001)
        log_level = self.config.get(
            "log_level", "info"
        ).lower()  # Lấy log level từ config

        logger.info(
            f"Runner: Starting Uvicorn server on {host}:{port} with log level {log_level}"
        )
        try:
            # Sử dụng app instance của class này
            uvicorn.run(self.app, host=host, port=port, log_level=log_level)
        except Exception as e:
            logger.exception(f"Runner: Failed to run Uvicorn: {e}")

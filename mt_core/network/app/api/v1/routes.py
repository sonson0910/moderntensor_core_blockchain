# Sửa file: sdk/network/app/api/v1/routes.py

from fastapi import APIRouter

# Import các router từ endpoints
from .endpoints import user
from .endpoints import consensus
from .endpoints import miner_comms  # <<<--- Import router mới
from .endpoints import validator_health  # <<<--- Import health endpoints

# Khởi tạo router chính cho API v1
api_router = APIRouter(prefix="/v1")

# Include các router con
api_router.include_router(user.router, tags=["Users"])
api_router.include_router(consensus.router, tags=["Consensus P2P"])
api_router.include_router(
    miner_comms.router, tags=["Miner Communication"]
)
api_router.include_router(
    validator_health.router, tags=["Validator Health"]
)  # <<<--- Include router mới

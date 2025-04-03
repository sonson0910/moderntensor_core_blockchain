# sdk/network/app/api/v1/routes.py
from fastapi import APIRouter

# Import các router từ endpoints
from .endpoints import user
from .endpoints import consensus # <<<--- Import router mới

# Khởi tạo router chính cho API v1
api_router = APIRouter(prefix="/v1")

# Include các router con
api_router.include_router(user.router, tags=["Users"])
api_router.include_router(consensus.router, tags=["Consensus P2P"]) # <<<--- Include router mới

# Có thể thêm các router khác ở đây
# api_router.include_router(other_endpoint.router, tags=["Other"])


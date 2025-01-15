from fastapi import FastAPI, Request
from starlette.middleware.cors import CORSMiddleware

from app.api.v1.routes import routers as v1_routers
from app.core.config import configs
from app.core.container import Container
from app.util.class_object import singleton

import asyncio
import time
from starlette.status import HTTP_504_GATEWAY_TIMEOUT
from fastapi.responses import JSONResponse


@singleton
class AppCreator:
    def __init__(self):
        # set app default
        self.app = FastAPI(
            title=configs.PROJECT_NAME,
            openapi_url=f"{configs.API}/openapi.json",
            version="0.0.1",
        )

        # set container
        self.container = Container()

        #time request
        REQUEST_TIMEOUT_ERROR = 1  # Threshold
        @self.app.middleware("http")
        async def timeout_middleware(request: Request, call_next):
            try:
                start_time = time.time()
                return await asyncio.wait_for(call_next(request), timeout=REQUEST_TIMEOUT_ERROR)

            except asyncio.TimeoutError:
                process_time = time.time() - start_time
                return JSONResponse({'detail': 'Request processing time excedeed limit',
                                'processing_time': process_time},
                                status_code=HTTP_504_GATEWAY_TIMEOUT)


        # set cors
        if configs.BACKEND_CORS_ORIGINS:
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=[str(origin) for origin in configs.BACKEND_CORS_ORIGINS],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )

        # set routes
        @self.app.get("/")
        def root():
            return "service is working"

        self.app.include_router(v1_routers, prefix=configs.API_V1_STR)
        # self.app.include_router(v2_routers, prefix=configs.API_V2_STR)


app_creator = AppCreator()
app = app_creator.app
container = app_creator.container

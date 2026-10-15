""" 应用启动入口文件 """
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.api.error_handlers import register_error_handlers
from app.api.routes import health, documents, chat, evaluations
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.core.observbility import configure_observability


def create_app() -> FastAPI:
    configure_logging()
    configure_observability()
    logger = get_logger(__name__)

    app = FastAPI(title=settings.app_name)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_error_handlers(app)
    app.include_router(health.router, prefix="/api")
    app.include_router(documents.router, prefix="/api")
    app.include_router(chat.router, prefix="/api")
    app.include_router(evaluations.router, prefix="/api")

    logger.info("APP初始化: %s", settings.app_name)
    return app

app = create_app()
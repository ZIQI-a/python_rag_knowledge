""" 应用启动入口文件 """
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.api.error_handlers import register_error_handlers
from app.api.routes import health, documents, chat, evaluations, auth, roles, users
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.core.observbility import configure_observability
from app.db.seed import seed_default_admin
from app.mcp_server import knowledge_mcp

logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """ 应用生命周期钩子启动时做初始化，启动期间维护 MCP session manager。 """
    # 这里在启动时，如果没有数据库内容，创建角色和用户
    if not settings.jwt_secret:
        logger.warning("JWT_SECRET未配置，请在生产环境中配置")
    try:
        await seed_default_admin()
    except Exception:
        logger.exception("初始化失败")

    """ 启动MCP Session Manager，在这里进行维护 """
    async with knowledge_mcp.session_manager.run():
        yield

def create_app() -> FastAPI:
    configure_logging()
    configure_observability()
    logger = get_logger(__name__)

    app = FastAPI(title=settings.app_name, lifespan=lifespan)

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
    app.include_router(auth.router, prefix="/api")
    app.include_router(roles.router, prefix="/api")
    app.include_router(users.router, prefix="/api")
    # MCP Server 同进程挂载到 /mcp：外部 Agent 用 Streamable HTTP transport 调用
    app.mount("/mcp", knowledge_mcp.streamable_http_app(), name="mcp")

    logger.info("APP初始化: %s", settings.app_name)
    return app

app = create_app()
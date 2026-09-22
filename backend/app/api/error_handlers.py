""" 统一异常到HTTP的响应转换 """
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.core.logging import get_logger
from app.core.exceptions import AppException

logger = get_logger(__name__)

# 根据异常类型，选择不同的响应状态码
async def _app_exception_handler(_: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.http_status,
        content={"code": exc.code, "message": exc.message},
    )

# 未处理的异常，返回500
async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("未处理的异常 -> %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"code": "internal_error", "message": "服务内部错误"},
    )

# 注册异常处理器
def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppException, _app_exception_handler) # type: ignore[arg-type]
    app.add_exception_handler(Exception, _unhandled_exception_handler)

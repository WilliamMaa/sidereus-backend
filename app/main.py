import logging
import sys
import time
import traceback

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.routers import health, match, resume

# FC / 容器日志读 stdout；强制打到控制台，带时间与模块名
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True,
)
logger = logging.getLogger("sidereus")

app = FastAPI(
    title="Sidereus Resume Analyzer",
    description="AI 赋能的智能简历分析系统",
    version="1.0.0",
)

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    path = request.url.path
    method = request.method
    logger.info("→ %s %s", method, path)
    try:
        response = await call_next(request)
    except Exception:
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.exception("✗ %s %s crashed after %.0fms", method, path, elapsed_ms)
        raise
    elapsed_ms = (time.perf_counter() - start) * 1000
    level = logging.WARNING if response.status_code >= 400 else logging.INFO
    logger.log(level, "← %s %s %s %.0fms", method, path, response.status_code, elapsed_ms)
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning("validation error on %s %s: %s", request.method, request.url.path, exc.errors())
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.warning(
        "http error on %s %s status=%s detail=%s",
        request.method,
        request.url.path,
        exc.status_code,
        exc.detail,
    )
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, (HTTPException, StarletteHTTPException, RequestValidationError)):
        raise exc
    logger.error(
        "unhandled exception on %s %s: %s\n%s",
        request.method,
        request.url.path,
        exc,
        traceback.format_exc(),
    )
    return JSONResponse(
        status_code=500,
        content={"detail": f"服务器内部错误: {exc}"},
    )


app.include_router(health.router)
app.include_router(resume.router)
app.include_router(match.router)


@app.on_event("startup")
async def on_startup() -> None:
    key_ok = bool(settings.dashscope_api_key)
    logger.info(
        "startup: model=%s cache_enabled=%s dashscope_key=%s cors=%s",
        settings.qwen_model,
        settings.cache_enabled,
        "set" if key_ok else "MISSING",
        settings.cors_origins,
    )


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "sidereus-backend", "docs": "/docs"}

from fastapi import APIRouter

from app.schemas.resume import HealthResponse
from app.services.cache import cache_service

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    backend = cache_service.backend
    if backend == "redis":
        redis_status = "ok" if cache_service.ping() else "unavailable"
    else:
        redis_status = "memory"
    return HealthResponse(status="ok", redis=redis_status)

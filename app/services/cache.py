import json
import logging
from typing import Any, Optional

import redis
from redis.exceptions import RedisError

from app.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    def __init__(self) -> None:
        self._client: Optional[redis.Redis] = None
        self._memory: dict[str, dict[str, Any]] = {}
        if settings.cache_enabled:
            try:
                self._client = redis.from_url(
                    settings.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=2,
                )
                self._client.ping()
            except RedisError as exc:
                logger.warning("Redis unavailable, using in-memory cache: %s", exc)
                self._client = None

    @property
    def available(self) -> bool:
        return self._client is not None

    @property
    def backend(self) -> str:
        if self._client:
            return "redis"
        return "memory"

    def ping(self) -> bool:
        if self._client:
            try:
                return bool(self._client.ping())
            except RedisError:
                return False
        return True

    def get(self, key: str) -> Optional[dict[str, Any]]:
        if self._client:
            try:
                raw = self._client.get(key)
                if raw is None:
                    return None
                return json.loads(raw)
            except (RedisError, json.JSONDecodeError) as exc:
                logger.warning("Cache get failed for %s: %s", key, exc)
                return None
        return self._memory.get(key)

    def set(self, key: str, value: dict[str, Any]) -> None:
        if self._client:
            try:
                self._client.setex(key, settings.cache_ttl_seconds, json.dumps(value, ensure_ascii=False))
                return
            except RedisError as exc:
                logger.warning("Cache set failed for %s: %s", key, exc)
        self._memory[key] = value


cache_service = CacheService()

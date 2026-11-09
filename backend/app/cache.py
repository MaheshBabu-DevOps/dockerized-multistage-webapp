"""Redis cache that never takes the API down: if Redis fails, requests go to the database."""

import logging
from typing import Any

import redis

logger = logging.getLogger(__name__)

NOTES_KEY = "notes:all"


class Cache:
    def __init__(self, client: Any, ttl_seconds: int) -> None:
        self._client = client
        self._ttl = ttl_seconds

    def get(self, key: str) -> str | None:
        try:
            return self._client.get(key)
        except redis.RedisError:
            logger.warning("Redis unavailable on GET; using the database")
            return None

    def set(self, key: str, value: str) -> None:
        try:
            self._client.set(key, value, ex=self._ttl)
        except redis.RedisError:
            logger.warning("Redis unavailable on SET; skipping cache")

    def invalidate(self, key: str) -> None:
        try:
            self._client.delete(key)
        except redis.RedisError:
            logger.warning("Redis unavailable on DELETE; cache may be stale until it expires")

    def ping(self) -> bool:
        try:
            return bool(self._client.ping())
        except redis.RedisError:
            return False

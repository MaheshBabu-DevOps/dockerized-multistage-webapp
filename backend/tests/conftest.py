import fakeredis
import pytest
import redis
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


class BrokenRedis:
    """A Redis client where every call fails, to prove the API still works."""

    def __getattr__(self, name):
        def fail(*args, **kwargs):
            raise redis.ConnectionError("redis is down")

        return fail


@pytest.fixture
def settings(tmp_path):
    return Settings(database_url=f"sqlite:///{tmp_path / 'test.db'}", cache_ttl_seconds=30)


@pytest.fixture
def client(settings):
    with TestClient(
        create_app(settings, redis_client=fakeredis.FakeRedis(decode_responses=True))
    ) as c:
        yield c


@pytest.fixture
def client_without_redis(settings):
    with TestClient(create_app(settings, redis_client=BrokenRedis())) as c:
        yield c

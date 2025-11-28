"""
Enhanced test fixtures with testcontainers support for MongoDB and Redis.

Provides fixtures for:
- MongoDB testcontainers
- Redis testcontainers
- FastAPI TestClient
- Mock LLM clients
- Test data helpers
"""

from __future__ import annotations

import os
import asyncio
from typing import AsyncGenerator, Generator
import pytest
from testcontainers.mongodb import MongoDbContainer
from testcontainers.redis import RedisContainer
from fastapi.testclient import TestClient

# Import app and dependencies
try:
    from app import app
    from mongo import MongoClient
    from backend.cache import _get_redis
except ImportError:
    # Fallback for test environments
    app = None
    MongoClient = None
    _get_redis = None


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def mongo_container() -> Generator[MongoDbContainer, None, None]:
    """Start MongoDB testcontainer for the test session."""
    if os.getenv("TEST_USE_CONTAINERS", "true").lower() == "false":
        # Use external MongoDB if containers disabled
        yield None
        return
    
    with MongoDbContainer("mongo:7.0") as mongo:
        yield mongo


@pytest.fixture(scope="session")
def redis_container() -> Generator[RedisContainer, None, None]:
    """Start Redis testcontainer for the test session."""
    if os.getenv("TEST_USE_CONTAINERS", "true").lower() == "false":
        # Use external Redis if containers disabled
        yield None
        return
    
    with RedisContainer("redis:7-alpine") as redis:
        yield redis


@pytest.fixture(scope="session")
async def mongo_client(mongo_container: MongoDbContainer | None) -> AsyncGenerator[MongoClient, None]:
    """Create MongoDB client connected to testcontainer."""
    if mongo_container:
        connection_string = mongo_container.get_connection_url()
    else:
        # Use external MongoDB
        connection_string = os.getenv("MONGO_URI", "mongodb://root:changeme@localhost:27017")
    
    client = MongoClient(
        uri=connection_string,
        host="localhost",
        port=27017,
        username="root",
        password="changeme",
        database="test",
        auth_database="admin",
    )
    
    yield client
    
    # Cleanup
    try:
        await client.client.close()
    except Exception:  # noqa: BLE001
        pass


@pytest.fixture(scope="session")
async def redis_client(redis_container: RedisContainer | None):
    """Create Redis client connected to testcontainer."""
    if redis_container:
        connection_string = redis_container.get_container_host_ip()
        port = redis_container.get_exposed_port(6379)
        redis_url = f"redis://{connection_string}:{port}"
    else:
        # Use external Redis
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # Set environment variable for cache module
    os.environ["REDIS_URL"] = redis_url
    
    # Get Redis client
    if _get_redis:
        redis = _get_redis()
        yield redis
        try:
            await redis.close()
        except Exception:  # noqa: BLE001
            pass
    else:
        yield None


@pytest.fixture
def client() -> TestClient:
    """Create FastAPI TestClient for testing endpoints."""
    if app is None:
        pytest.skip("app not available in test environment")
    
    return TestClient(app)


@pytest.fixture(autouse=True)
async def cleanup_redis(redis_client):
    """Clean up Redis keys after each test."""
    yield
    if redis_client:
        try:
            # Clear test keys
            keys = await redis_client.keys("test:*")
            if keys:
                await redis_client.delete(*keys)
        except Exception:  # noqa: BLE001
            pass


@pytest.fixture(autouse=True)
async def cleanup_mongo(mongo_client: MongoClient):
    """Clean up MongoDB collections after each test."""
    yield
    if mongo_client:
        try:
            # Clear test collections
            collections = await mongo_client.db.list_collection_names()
            for coll in collections:
                if coll.startswith("test_") or coll.endswith("_test"):
                    await mongo_client.db[coll].delete_many({})
        except Exception:  # noqa: BLE001
            pass






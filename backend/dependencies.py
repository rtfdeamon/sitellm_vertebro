"""FastAPI dependencies."""

from fastapi import HTTPException
from starlette.requests import Request

from mongo import MongoClient


def get_mongo_client(request: Request) -> MongoClient:
    """Get MongoDB client from request state."""
    mongo_client: MongoClient | None = getattr(request.state, "mongo", None)
    if mongo_client is None:
        mongo_client = getattr(request.app.state, "mongo", None)
        if mongo_client is None:
            raise HTTPException(status_code=500, detail="Mongo client is unavailable")
        request.state.mongo = mongo_client
    return mongo_client

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import llm_router
from mongo import MongoClient
from vectors import DocumentsParser
from yallm import YaLLM, YaLLMEmbeddings
from settings import Settings

settings = Settings()


@asynccontextmanager
async def lifespan(_) -> AsyncGenerator[dict[str, Any], None]:
    llm = YaLLM()
    embeddings = YaLLMEmbeddings()

    mongo_client = MongoClient(
        settings.mongo.host,
        settings.mongo.port,
        settings.mongo.username,
        settings.mongo.password,
        settings.mongo.database,
        settings.mongo.auth,
    )
    contexts_collection = settings.mongo.contexts
    context_presets_collection = settings.mongo.presets

    vector_store = DocumentsParser(
        embeddings.get_embeddings_model(),
        settings.redis.vector,
        settings.redis.host,
        settings.redis.port,
        0,
        settings.redis.password,
        settings.redis.secure,
    )

    yield {
        "llm": llm,
        "mongo": mongo_client,
        "contexts_collection": contexts_collection,
        "context_presets_collection": context_presets_collection,
        "vector_store": vector_store,
    }

    del llm
    await mongo_client.client.close()


app = FastAPI(lifespan=lifespan, debug=settings.debug)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"])
app.include_router(
    llm_router,
    prefix="/api/v1",
)

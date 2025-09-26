"""Celery worker tasks for updating the Qdrant vector store."""

import json
import os
import re
import time
from collections.abc import Generator
from typing import Dict
from urllib.parse import quote_plus

from bson import ObjectId
from gridfs import GridFS
from pymongo import MongoClient
from celery import Celery
from celery.schedules import crontab
from celery.signals import worker_ready

import requests
try:  # Optional detailed error type from ollama client
    from ollama import ResponseError as _OllamaResponseError  # type: ignore
except Exception:  # pragma: no cover - gracefully handle missing symbol
    _OllamaResponseError = None
import structlog

from models import Document
from settings import Settings
from vectors import DocumentsParser
try:  # Prefer the dedicated langchain-ollama provider
    from langchain_ollama import OllamaEmbeddings as _OllamaEmbeddings
    _OLLAMA_PROVIDER = "langchain_ollama"
except ImportError:  # Fallback to the legacy implementation if package missing
    from langchain_community.embeddings import OllamaEmbeddings as _OllamaEmbeddings
    _OLLAMA_PROVIDER = "langchain_community"
_OLLAMA_FALLBACK_WARNED = False

try:  # Prefer modern huggingface integration
    from langchain_huggingface import HuggingFaceEmbeddings as _HFEmbeddings
    _HF_PROVIDER = "langchain_huggingface"
except ImportError:  # pragma: no cover - fallback to community
    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings as _HFEmbeddings
        _HF_PROVIDER = "langchain_community"
    except ImportError:  # pragma: no cover - last resort
        try:
            from langchain_community.embeddings import SentenceTransformerEmbeddings as _HFEmbeddings
            _HF_PROVIDER = "langchain_community"
        except ImportError:  # pragma: no cover - no huggingface support
            _HFEmbeddings = None  # type: ignore[assignment]
            _HF_PROVIDER = None

from yallm import YaLLMEmbeddings
from core.status import status_dict
from observability.logging import configure_logging



configure_logging()

settings = Settings()

logger = structlog.get_logger(__name__)

celery = Celery(__name__)
celery.conf.broker_url = settings.celery.broker
celery.conf.result_backend = settings.celery.result
celery.autodiscover_tasks(["crawler", "knowledge"])
celery.conf.beat_schedule = {
    "update-vector-store-biweekly": {
        "task": "worker.periodic_update",
        "schedule": crontab(day_of_week=[3, 6]),
    },
    "status-report-every-30s": {
        "task": "status.report",
        "schedule": 30.0,
    },
}


def update_vector_store():
    """Parse new or updated documents from MongoDB into the vector store."""

    logger.info("updating vector store")
    vector_store = get_document_parser()
    mongo_client = get_mongo_client()
    try:
        db = mongo_client[settings.mongo.database]
        documents_collection = db[settings.mongo.documents]
        settings_collection = db[settings.mongo.settings]

        cleanup_stats = prune_knowledge_collection(db, documents_collection)
        if cleanup_stats["removed"]:
            logger.info(
                "knowledge_pruned",
                removed=cleanup_stats["removed"],
                duplicates=cleanup_stats["duplicates"],
                low_value=cleanup_stats["low_value"],
            )

        try:
            documents_collection.create_index("ts", name="documents_ts")
        except Exception as exc:
            logger.debug(
                "mongo_index_create_failed",
                collection=settings.mongo.documents,
                index="documents_ts",
                error=str(exc),
            )

        state_key = "vector_store_state"
        state = settings_collection.find_one({"_id": state_key}) or {}
        last_ts_raw = state.get("last_ts")
        try:
            last_ts = float(last_ts_raw)
        except (TypeError, ValueError):
            last_ts = 0.0

        filter_query: Dict[str, object] | None = None
        mode = "incremental"
        if last_ts > 0:
            filter_query = {"ts": {"$gt": last_ts}}
            logger.info("vector store incremental", since=last_ts)
        else:
            mode = "full"
            logger.info("vector store full rebuild")

        processed = 0
        latest_ts = last_ts

        for document, data in get_documents_sync(
            mongo_client, filter_query=filter_query
        ):
            logger.info("embedding", document=document.name)
            try:
                vector_store.parse_document(document, data)
            except ValueError as exc:
                logger.warning(
                    "vector_store_skip_document",
                    document=document.fileId,
                    error=str(exc),
                )
                continue
            processed += 1
            if document.ts is not None:
                try:
                    latest_ts = max(latest_ts, float(document.ts))
                except (TypeError, ValueError):
                    pass

        state_payload = {
            "last_ts": latest_ts if processed else last_ts,
            "updated_at": time.time(),
            "last_processed": processed,
            "mode": mode,
        }
        settings_collection.update_one(
            {"_id": state_key},
            {"$set": state_payload},
            upsert=True,
        )
        logger.info(
            "vector store update complete",
            processed=processed,
            since=last_ts if last_ts > 0 else None,
        )
    finally:
        mongo_client.close()
        try:
            vector_store.close()
        except AttributeError:
            pass


def get_documents_sync(
    mongo_client: MongoClient,
    *,
    filter_query: Dict[str, object] | None = None,
) -> Generator[tuple[Document, bytes], None]:
    """Yield documents and their data from GridFS synchronously.

    Parameters
    ----------
    mongo_client:
        Active connection to MongoDB used to fetch documents and files.

    Yields
    ------
    tuple[Document, bytes]
        Parsed ``Document`` metadata along with the binary file contents.
    """
    db = mongo_client[settings.mongo.database]
    collection = db[settings.mongo.documents]
    gridfs = GridFS(db)
    query = filter_query or {}
    cursor = collection.find(query, {"_id": False}).sort("ts", 1).batch_size(50)

    for raw_doc in cursor:
        document = Document(**raw_doc)
        try:
            file = gridfs.get(ObjectId(document.fileId))
        except Exception as exc:
            logger.warning("gridfs_fetch_failed", file_id=document.fileId, error=str(exc))
            continue

        yield document, file.read()


def get_mongo_client() -> MongoClient:
    """Return a synchronous MongoDB client.

    Uses credentials from :class:`Settings` to construct the connection URL.
    """
    url = f"mongodb://{quote_plus(settings.mongo.username)}:{quote_plus(settings.mongo.password)}@{settings.mongo.host}:{settings.mongo.port}/{settings.mongo.auth}"
    logger.info("connect mongo", host=settings.mongo.host)
    return MongoClient(url)


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _pull_ollama_model(base_url: str, model: str) -> None:
    url = f"{base_url.rstrip('/')}/api/pull"
    logger.info("ollama_pull_start", base_url=base_url, model=model)
    try:
        with requests.post(url, json={"name": model}, stream=True, timeout=600) as response:
            response.raise_for_status()
            for raw in response.iter_lines(decode_unicode=True):
                if not raw:
                    continue
                try:
                    payload = json.loads(raw)
                except json.JSONDecodeError:
                    logger.debug("ollama_pull_parse_failed", chunk=raw)
                    continue
                status = payload.get("status")
                if status:
                    logger.debug("ollama_pull_status", status=status, model=model)
                if payload.get("error"):
                    raise RuntimeError(str(payload["error"]))
                if status == "success":
                    logger.info("ollama_pull_success", model=model)
                    return
    except requests.RequestException as exc:
        raise RuntimeError(f"HTTP error pulling model: {exc}") from exc
    raise RuntimeError("Unexpected end of pull stream")


def _ensure_embedding_ready(instance, base_url: str, model: str) -> None:
    sample_text = "ping"
    try:
        instance.embed_query(sample_text)
        return
    except Exception as exc:  # noqa: BLE001
        status = getattr(exc, "status_code", None)
        message = str(exc)
        missing = False
        if status == 404:
            missing = True
        elif "not found" in message.lower():
            missing = True
        elif _OllamaResponseError is not None and isinstance(exc, _OllamaResponseError):
            missing = True
        if not missing:
            raise
        logger.warning(
            "embeddings_ollama_missing_model_embed",
            base_url=base_url,
            model=model,
            error=message,
        )
    _pull_ollama_model(base_url, model)
    instance.embed_query(sample_text)
    logger.info("embeddings_ollama_ready", base_url=base_url, model=model)


def _get_embeddings_model():
    model_name = (
        os.getenv("SENTENCE_TRANSFORMERS_MODEL")
        or os.getenv("EMB_MODEL_NAME")
        or settings.emb_model_name
    )

    if (
        _HFEmbeddings is not None
        and not _env_flag("DISABLE_SENTENCE_TRANSFORMERS", False)
    ):
        try:
            logger.info(
                "embeddings_select",
                backend="sentence-transformers",
                provider=_HF_PROVIDER,
                model=model_name,
            )
            return _HFEmbeddings(model_name=model_name)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "embeddings_sentence_transformers_failed",
                model=model_name,
                provider=_HF_PROVIDER,
                error=str(exc),
            )

    prefer_local = _env_flag("LOCAL_LLM_ENABLED", True)

    if prefer_local:
        try:
            logger.info("embeddings_select", backend="local")
            return YaLLMEmbeddings().get_embeddings_model()
        except ImportError as exc:
            logger.warning("embeddings_local_missing", error=str(exc))
        except Exception as exc:  # noqa: BLE001
            logger.error("embeddings_local_failed", error=str(exc))

    base_url = os.getenv("OLLAMA_BASE_URL")
    if base_url:
        model_name = (
            os.getenv("OLLAMA_EMBED_MODEL")
            or model_name
            or os.getenv("LLM_MODEL")
            or settings.llm_model
            or "nomic-embed-text"
        )
        attempt_pull = True
        try:
            logger.info(
                "embeddings_select",
                backend="ollama",
                base_url=base_url,
                model=model_name,
                provider=_OLLAMA_PROVIDER,
            )
            instance = _OllamaEmbeddings(
                model=model_name,
                base_url=base_url.rstrip("/"),
            )
            global _OLLAMA_FALLBACK_WARNED  # noqa: PLW0603
            if _OLLAMA_PROVIDER != "langchain_ollama" and not _OLLAMA_FALLBACK_WARNED:
                logger.warning(
                    "embeddings_ollama_legacy_provider",
                    provider=_OLLAMA_PROVIDER,
                )
                _OLLAMA_FALLBACK_WARNED = True
            try:
                _ensure_embedding_ready(instance, base_url, model_name)
            except Exception as exc:  # noqa: BLE001
                if attempt_pull:
                    attempt_pull = False
                    try:
                        _pull_ollama_model(base_url, model_name)
                        _ensure_embedding_ready(instance, base_url, model_name)
                    except Exception as pull_exc:  # noqa: BLE001
                        logger.error(
                            "embeddings_ollama_pull_failed",
                            model=model_name,
                            base_url=base_url,
                            error=str(pull_exc),
                        )
                        raise RuntimeError("Failed to pull Ollama model") from pull_exc
                else:
                    logger.error(
                        "embeddings_ollama_ready_failed",
                        model=model_name,
                        base_url=base_url,
                        error=str(exc),
                    )
                    raise
            return instance
        except Exception as exc:  # noqa: BLE001
            if attempt_pull:
                logger.warning(
                    "embeddings_ollama_missing_model",
                    model=model_name,
                    base_url=base_url,
                    error=str(exc),
                )
                attempt_pull = False
                try:
                    _pull_ollama_model(base_url, model_name)
                    instance = _OllamaEmbeddings(
                        model=model_name,
                        base_url=base_url.rstrip("/"),
                    )
                    return instance
                except Exception as pull_exc:  # noqa: BLE001
                    logger.error(
                        "embeddings_ollama_pull_failed",
                        model=model_name,
                        base_url=base_url,
                        error=str(pull_exc),
                    )
                    if "manifest" in str(pull_exc).lower() or "does not exist" in str(pull_exc).lower():
                        raise RuntimeError(
                            "Ollama embedding model not found; set OLLAMA_EMBED_MODEL to an installed model"
                        ) from pull_exc
                    raise RuntimeError("Failed to pull Ollama model") from pull_exc
                try:
                    instance = _OllamaEmbeddings(
                        model=model_name,
                        base_url=base_url.rstrip("/"),
                    )
                    _ensure_embedding_ready(instance, base_url, model_name)
                    return instance
                except Exception as second_exc:  # noqa: BLE001
                    logger.error(
                        "embeddings_ollama_ready_failed",
                        model=model_name,
                        base_url=base_url,
                        error=str(second_exc),
                    )
                    if "manifest" in str(second_exc).lower() or "does not exist" in str(second_exc).lower():
                        raise RuntimeError(
                            "Ollama embedding model not found; set OLLAMA_EMBED_MODEL to an installed model"
                        ) from second_exc
                    raise RuntimeError("Failed to initialize Ollama embeddings") from second_exc
            logger.error(
                "embeddings_ollama_failed",
                base_url=base_url,
                model=model_name,
                error=str(exc),
            )
            raise RuntimeError("Failed to initialize Ollama embeddings") from exc

    raise RuntimeError(
        "No embeddings backend available. Configure LOCAL_LLM_ENABLED=true or provide OLLAMA_BASE_URL."
    )


def get_document_parser() -> DocumentsParser:
    """Construct a ``DocumentsParser`` using available embeddings."""

    logger.info("create document parser")
    embeddings = _get_embeddings_model()
    qdrant_url = str(getattr(settings, "qdrant_url", "http://qdrant:6333"))
    collection = getattr(settings, "qdrant_collection", None) or "documents"
    return DocumentsParser(embeddings, collection, qdrant_url)


BREADCRUMB_SEPARATORS = re.compile(r"\s*[>/\\»|-]+\s*")
NAV_KEYWORDS = {
    "главная",
    "контакты",
    "о компании",
    "о нас",
    "услуги",
    "партнёры",
    "клиенты",
    "новости",
    "карта сайта",
    "help",
    "support",
    "docs",
    "documentation",
    "download",
}
FOOTER_KEYWORDS = {
    "все права защищены",
    "all rights reserved",
    "политика конфиденциальности",
    "privacy policy",
    "terms of use",
    "соглашение",
    "copyright",
    "©",
}


def _looks_like_navigation_snippet(text: str) -> bool:
    candidate = text.strip().lower()
    if not candidate:
        return True
    parts = [part.strip() for part in BREADCRUMB_SEPARATORS.split(candidate) if part.strip()]
    if parts and all(part in NAV_KEYWORDS for part in parts):
        return True
    if len(candidate) <= 60 and candidate.count(" ") <= 6:
        tokens = [token for token in re.split(r"\W+", candidate) if token]
        if tokens and all(token in NAV_KEYWORDS for token in tokens):
            return True
    for marker in FOOTER_KEYWORDS:
        if marker in candidate and len(candidate) <= 160:
            return True
    return False


def _delete_document(collection, gridfs: GridFS, file_id: str) -> None:
    collection.delete_one({"fileId": file_id})
    try:
        gridfs.delete(ObjectId(file_id))
    except Exception:
        logger.debug("gridfs_delete_skip", file_id=file_id)


def prune_knowledge_collection(db, collection) -> dict[str, int]:
    """Remove duplicate and low-value knowledge documents before processing."""

    gridfs = GridFS(db)
    seen_hashes: dict[str, set[str]] = {}
    removed = duplicates = low_value = 0
    try:
        cursor = collection.find(
            {},
            {
                "fileId": 1,
                "content_hash": 1,
                "description": 1,
                "project": 1,
            },
        )
        for doc in cursor:
            file_id = doc.get("fileId")
            if not file_id:
                continue
            project_key = (doc.get("project") or "default").strip().lower()
            bucket = seen_hashes.setdefault(project_key, set())
            content_hash = doc.get("content_hash")
            description = (doc.get("description") or "").strip()

            if content_hash and content_hash in bucket:
                _delete_document(collection, gridfs, file_id)
                duplicates += 1
                removed += 1
                continue

            skip_low_value = False
            if description:
                if len(description) < 60 or _looks_like_navigation_snippet(description):
                    skip_low_value = True
            else:
                skip_low_value = True

            if skip_low_value:
                _delete_document(collection, gridfs, file_id)
                low_value += 1
                removed += 1
                continue

            if content_hash:
                bucket.add(content_hash)
    except Exception as exc:  # noqa: BLE001
        logger.warning("knowledge_prune_failed", error=str(exc))

    return {"removed": removed, "duplicates": duplicates, "low_value": low_value}

@worker_ready.connect
def on_startup(*args, **kwargs):
    """Update the vector store when the worker starts.

    This hook ensures that the latest documents are embedded as soon as the
    worker process is ready to accept tasks.
    """
    logger.info("worker ready")
    update_vector_store()


@celery.task
def periodic_update():
    """Celery beat task that updates the vector store.

    Scheduled twice a week via ``beat_schedule`` to keep the Redis index in
    sync with MongoDB.
    """
    logger.info("scheduled update")
    update_vector_store()


@celery.task(name="status.report")
def status_report():
    """Log a short status summary."""
    s = status_dict()
    logger.info(
        "status",
        fill=s["fill_percent"],
        mongo=s["db"]["mongo_docs"],
        qdrant=s["db"]["qdrant_points"],
        queued=s["crawler"]["queued"],
        in_progress=s["crawler"]["in_progress"],
        done=s["crawler"]["done"],
        failed=s["crawler"]["failed"],
        last=s["crawler"]["last_url"],
    )

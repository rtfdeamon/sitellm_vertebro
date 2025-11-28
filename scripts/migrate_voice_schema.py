#!/usr/bin/env python3
"""
Database migration script for voice assistant collections.

Creates MongoDB collections and indexes required for the voice assistant feature.
Run this script before deploying the voice assistant functionality.

Usage:
    python scripts/migrate_voice_schema.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import CollectionInvalid
import structlog

logger = structlog.get_logger()

# Collection names (matching mongo.py defaults)
VOICE_SESSIONS_COLLECTION = os.getenv("MONGO_VOICE_SESSIONS", "voice_sessions")
VOICE_INTERACTIONS_COLLECTION = os.getenv("MONGO_VOICE_INTERACTIONS", "voice_interactions")
VOICE_AUDIO_CACHE_COLLECTION = os.getenv("MONGO_VOICE_AUDIO_CACHE", "voice_audio_cache")
VOICE_ANALYTICS_COLLECTION = os.getenv("MONGO_VOICE_ANALYTICS", "voice_analytics")


async def create_voice_collections_and_indexes(client: AsyncIOMotorClient, database_name: str) -> bool:
    """Create voice collections and indexes."""
    db = client[database_name]
    collections_created = []
    indexes_created = []

    try:
        # 1. Voice Sessions Collection
        try:
            await db.create_collection(VOICE_SESSIONS_COLLECTION)
            collections_created.append(VOICE_SESSIONS_COLLECTION)
            logger.info("voice_collection_created", collection=VOICE_SESSIONS_COLLECTION)
        except CollectionInvalid:
            logger.info("voice_collection_exists", collection=VOICE_SESSIONS_COLLECTION)

        # Indexes for voice_sessions
        await db[VOICE_SESSIONS_COLLECTION].create_index("session_id", unique=True)
        indexes_created.append(f"{VOICE_SESSIONS_COLLECTION}.session_id")

        await db[VOICE_SESSIONS_COLLECTION].create_index([("project", 1), ("created_at", -1)])
        indexes_created.append(f"{VOICE_SESSIONS_COLLECTION}.project+created_at")

        # TTL index for automatic expiry
        await db[VOICE_SESSIONS_COLLECTION].create_index(
            "expires_at", expireAfterSeconds=0
        )
        indexes_created.append(f"{VOICE_SESSIONS_COLLECTION}.expires_at (TTL)")

        # 2. Voice Interactions Collection
        try:
            await db.create_collection(VOICE_INTERACTIONS_COLLECTION)
            collections_created.append(VOICE_INTERACTIONS_COLLECTION)
            logger.info("voice_collection_created", collection=VOICE_INTERACTIONS_COLLECTION)
        except CollectionInvalid:
            logger.info("voice_collection_exists", collection=VOICE_INTERACTIONS_COLLECTION)

        # Indexes for voice_interactions
        await db[VOICE_INTERACTIONS_COLLECTION].create_index(
            [("session_id", 1), ("timestamp", 1)]
        )
        indexes_created.append(f"{VOICE_INTERACTIONS_COLLECTION}.session_id+timestamp")

        await db[VOICE_INTERACTIONS_COLLECTION].create_index(
            [("project", 1), ("timestamp", -1)]
        )
        indexes_created.append(f"{VOICE_INTERACTIONS_COLLECTION}.project+timestamp")

        # TTL index (30 days)
        await db[VOICE_INTERACTIONS_COLLECTION].create_index(
            "timestamp", expireAfterSeconds=2592000
        )
        indexes_created.append(f"{VOICE_INTERACTIONS_COLLECTION}.timestamp (TTL 30d)")

        # 3. Voice Audio Cache Collection
        try:
            await db.create_collection(VOICE_AUDIO_CACHE_COLLECTION)
            collections_created.append(VOICE_AUDIO_CACHE_COLLECTION)
            logger.info("voice_collection_created", collection=VOICE_AUDIO_CACHE_COLLECTION)
        except CollectionInvalid:
            logger.info("voice_collection_exists", collection=VOICE_AUDIO_CACHE_COLLECTION)

        # Indexes for voice_audio_cache
        await db[VOICE_AUDIO_CACHE_COLLECTION].create_index("audio_id", unique=True)
        indexes_created.append(f"{VOICE_AUDIO_CACHE_COLLECTION}.audio_id")

        await db[VOICE_AUDIO_CACHE_COLLECTION].create_index(
            [("text_hash", 1), ("voice", 1), ("language", 1)]
        )
        indexes_created.append(f"{VOICE_AUDIO_CACHE_COLLECTION}.text_hash+voice+language")

        # TTL index (7 days for accessed_at)
        await db[VOICE_AUDIO_CACHE_COLLECTION].create_index(
            "accessed_at", expireAfterSeconds=604800
        )
        indexes_created.append(f"{VOICE_AUDIO_CACHE_COLLECTION}.accessed_at (TTL 7d)")

        # 4. Voice Analytics Collection (optional, for future use)
        try:
            await db.create_collection(VOICE_ANALYTICS_COLLECTION)
            collections_created.append(VOICE_ANALYTICS_COLLECTION)
            logger.info("voice_collection_created", collection=VOICE_ANALYTICS_COLLECTION)
        except CollectionInvalid:
            logger.info("voice_collection_exists", collection=VOICE_ANALYTICS_COLLECTION)

        logger.info(
            "voice_migration_completed",
            collections_created=len(collections_created),
            indexes_created=len(indexes_created),
            collections=collections_created,
            indexes=indexes_created,
        )
        return True

    except Exception as exc:
        logger.error("voice_migration_failed", error=str(exc), exc_info=True)
        return False


async def verify_migration(client: AsyncIOMotorClient, database_name: str) -> bool:
    """Verify that all collections and indexes exist."""
    db = client[database_name]
    required_collections = [
        VOICE_SESSIONS_COLLECTION,
        VOICE_INTERACTIONS_COLLECTION,
        VOICE_AUDIO_CACHE_COLLECTION,
    ]

    try:
        existing_collections = await db.list_collection_names()
        missing = [c for c in required_collections if c not in existing_collections]

        if missing:
            logger.error("voice_migration_verification_failed", missing_collections=missing)
            return False

        # Check critical indexes
        session_indexes = await db[VOICE_SESSIONS_COLLECTION].list_indexes().to_list(length=10)
        session_index_names = [idx["name"] for idx in session_indexes]
        if "session_id_1" not in session_index_names:
            logger.error("voice_migration_missing_index", index="voice_sessions.session_id")
            return False

        logger.info("voice_migration_verified", collections=required_collections)
        return True

    except Exception as exc:
        logger.error("voice_migration_verification_error", error=str(exc))
        return False


async def main() -> int:
    """Main migration entry point."""
    from settings import MongoSettings

    mongo_settings = MongoSettings()
    uri = mongo_settings.uri or (
        f"mongodb://{mongo_settings.username}:{mongo_settings.password}"
        f"@{mongo_settings.host}:{mongo_settings.port}/{mongo_settings.database}"
        f"?authSource={mongo_settings.auth}"
    )

    logger.info("voice_migration_starting", database=mongo_settings.database, uri=uri.split("@")[-1])

    try:
        client = AsyncIOMotorClient(uri)
        # Verify connection
        await client.admin.command("ping")

        success = await create_voice_collections_and_indexes(client, mongo_settings.database)
        if not success:
            return 1

        verified = await verify_migration(client, mongo_settings.database)
        if not verified:
            return 1

        logger.info("voice_migration_success")
        return 0

    except Exception as exc:
        logger.error("voice_migration_error", error=str(exc), exc_info=True)
        return 1
    finally:
        if "client" in locals():
            client.close()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)


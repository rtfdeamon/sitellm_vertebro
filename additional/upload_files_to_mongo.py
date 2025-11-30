"""Script to upload documents from the ``knowledge_base`` directory to MongoDB.

The script iterates over all files located in the ``knowledge_base`` folder
and stores them in GridFS while also creating metadata entries in the
``documents`` collection.
"""

import asyncio
from pathlib import Path

from packages.core.mongo import MongoClient
from packages.core.settings import Settings


settings = Settings()


async def main():
    """Upload all files from the ``knowledge_base`` directory into GridFS.

    A single ``MongoClient`` is created using settings from :class:`Settings`.
    Every file is read in binary mode and passed to
    :func:`mongo.MongoClient.upload_document`.
    """
    mongo_client = MongoClient(
        settings.mongo.host,
        settings.mongo.port,
        settings.mongo.username,
        settings.mongo.password,
        settings.mongo.database,
        settings.mongo.auth,
    )

    base = Path(__file__).parent.parent / "knowledge_base"
    if not base.is_dir():
        return
    for file in base.iterdir():
        with file.open("rb") as f:
            await mongo_client.upload_document(
                file.name,
                f.read(),
                settings.mongo.documents,
                project=(settings.project_name or settings.domain or "default"),
            )


asyncio.run(main())

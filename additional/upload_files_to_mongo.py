""Script to upload documents from ``files`` directory to MongoDB.

The script iterates over all files located in the ``files`` subfolder and
stores them in GridFS while also creating metadata entries in the ``documents``
collection.
"""

import asyncio
from pathlib import Path

from mongo import MongoClient
from settings import Settings


settings = Settings()


async def main():
    """Upload all files from the ``files`` directory into GridFS.

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

    for file in (Path(__file__).parent / "files").iterdir():
        with file.open("rb") as f:
            await mongo_client.upload_document(
                file.name, f.read(), settings.mongo.documents
            )


asyncio.run(main())

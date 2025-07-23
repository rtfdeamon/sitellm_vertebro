import asyncio
from pathlib import Path

from mongo import MongoClient
from settings import Settings


settings = Settings()


async def main():
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

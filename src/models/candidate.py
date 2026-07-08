import motor.motor_asyncio
from src.config import get_settings

_client = None


def get_client() -> motor.motor_asyncio.AsyncIOMotorClient:
    global _client
    if _client is None:
        settings = get_settings()
        _client = motor.motor_asyncio.AsyncIOMotorClient(settings.mongo_uri)
    return _client


def get_db():
    settings = get_settings()
    return get_client()[settings.mongo_db]


def get_candidates_collection():
    return get_db()["candidates"]


async def ensure_indexes():
    col = get_candidates_collection()
    await col.create_index("id", unique=True)
    await col.create_index("status")
    await col.create_index("linkedin_url")

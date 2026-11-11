from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings

mongo_client = AsyncIOMotorClient(settings.MONGODB_URL)
db = mongo_client[settings.MONGODB_DB]


def get_db():
    return db

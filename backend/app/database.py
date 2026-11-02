import os

from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings

mongo_client = AsyncIOMotorClient(
    os.environ.get('MONGODB_URL', 'mongodb://localhost:27017')
)
db = mongo_client[settings.MONGODB_DB]


def get_db():
    return db

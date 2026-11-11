from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings

mongo_client = AsyncIOMotorClient(settings.MONGODB_URL)
db = mongo_client[settings.MONGODB_DB]


def get_db():
    return db


async def ensure_indexes() -> None:
    """Создаёт индексы, требуемые SPEC (идемпотентно)."""
    await db.users.create_index('email', unique=True)
    await db.bookings.create_index([('resource_id', 1), ('start_at', 1)])
    await db.bookings.create_index([('user_id', 1), ('start_at', 1)])
    await db.status_logs.create_index([('booking_id', 1), ('changed_at', 1)])
    await db.refresh_tokens.create_index('expires_at')
    await db.booking_participants.create_index([('booking_id', 1)])

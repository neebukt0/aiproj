"""Dev-сервер FastAPI + mongomock — backend без реальной MongoDB.

Нужен для локального запуска frontend и E2E-тестов Playwright:
данные живут в памяти и пересоздаются при каждом старте.

Запуск из каталога backend:
    .venv\\Scripts\\python.exe scripts\\mock_server.py
"""
import asyncio
import os
import sys

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND)
os.chdir(BACKEND)

from mongomock_motor import AsyncMongoMockClient

import app.database as database

mock_db = AsyncMongoMockClient()['booking']
database.db = mock_db

from app import auth, bookings, logs, reports, resources, users

auth.users_col = mock_db.users
auth.refresh_col = mock_db.refresh_tokens
bookings.bookings_col = mock_db.bookings
bookings.resources_col = mock_db.resources
bookings.status_logs_col = mock_db.status_logs
bookings.locks_col = mock_db.bookings_locks
bookings.participants_col = mock_db.booking_participants
bookings.users_col = mock_db.users
reports.db = mock_db
resources.resources_col = mock_db.resources
resources.bookings_col = mock_db.bookings
users.users_col = mock_db.users
logs.status_logs_col = mock_db.status_logs

import scripts.seed as seed

seed.db = mock_db
seed.ensure_indexes = database.ensure_indexes

import uvicorn

HOST = os.getenv('MOCK_HOST', '127.0.0.1')
PORT = int(os.getenv('MOCK_PORT', '8000'))

config = uvicorn.Config(
    'app.main:app',
    host=HOST,
    port=PORT,
    log_level='warning',
)
server = uvicorn.Server(config)


async def main() -> None:
    await seed.main()
    print(f'mock backend ready on http://{HOST}:{PORT}', flush=True)
    await server.serve()


if __name__ == '__main__':
    asyncio.run(main())

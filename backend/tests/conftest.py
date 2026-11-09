import pytest
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

from app import auth as auth_module
from app import bookings as bookings_module
from app import resources as resources_module
from app.main import app


@pytest.fixture
async def mock_db():
    client = AsyncMongoMockClient()
    db = client['booking']
    auth_module.users_col = db.users
    auth_module.refresh_col = db.refresh_tokens
    bookings_module.bookings_col = db.bookings
    bookings_module.resources_col = db.resources
    bookings_module.status_logs_col = db.status_logs
    bookings_module.locks_col = db.bookings_locks
    resources_module.resources_col = db.resources
    return db


@pytest.fixture
async def client(mock_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as ac:
        yield ac


async def register_user(ac: AsyncClient, email: str, password: str = 'Pass1234!', role: str = 'client') -> dict:
    resp = await ac.post('/api/auth/register', json={'email': email, 'password': password, 'role': role})
    return resp


async def login_user(ac: AsyncClient, email: str, password: str = 'Pass1234!') -> dict:
    return await ac.post('/api/auth/login', json={'email': email, 'password': password})


def bearer(token: str) -> dict:
    return {'Authorization': f'Bearer {token}'}

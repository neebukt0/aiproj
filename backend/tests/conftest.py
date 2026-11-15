import pytest
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

from app import auth as auth_module
from app import bookings as bookings_module
from app import logs as logs_module
from app import reports as reports_module
from app import resources as resources_module
from app import users as users_module
from app.main import app


@pytest.fixture
async def mock_db():
    client = AsyncMongoMockClient()
    db = client['booking']
    reports_module.db = db
    logs_module.status_logs_col = db.status_logs
    users_module.users_col = db.users
    auth_module.users_col = db.users
    auth_module.refresh_col = db.refresh_tokens
    bookings_module.bookings_col = db.bookings
    bookings_module.resources_col = db.resources
    bookings_module.status_logs_col = db.status_logs
    bookings_module.locks_col = db.bookings_locks
    bookings_module.participants_col = db.booking_participants
    bookings_module.users_col = db.users
    resources_module.resources_col = db.resources
    resources_module.bookings_col = db.bookings
    return db


@pytest.fixture
async def client(mock_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as ac:
        yield ac


async def register_user(ac: AsyncClient, email: str, password: str = 'Pass1234!'):
    return await ac.post('/api/auth/register', json={'email': email, 'password': password})


async def login_user(ac: AsyncClient, email: str, password: str = 'Pass1234!'):
    return await ac.post('/api/auth/login', json={'email': email, 'password': password})


async def register_and_login(
    ac: AsyncClient,
    email: str,
    role: str = 'client',
    password: str = 'Pass1234!',
) -> dict:
    """Регистрирует client и при необходимости повышает роль напрямую в БД.

    Публичная регистрация намеренно не принимает role (защита от privilege
    escalation), поэтому staff-пользователи в тестах создаются через БД.
    """
    resp = await register_user(ac, email, password)
    assert resp.status_code == 200, resp.text
    if role != 'client':
        await auth_module.users_col.update_one({'email': email}, {'$set': {'role': role}})
    login = await login_user(ac, email, password)
    assert login.status_code == 200, login.text
    return login.json()


def bearer(token: str) -> dict:
    return {'Authorization': f'Bearer {token}'}

from datetime import datetime, timedelta, timezone

import pytest

from app.auth import decode_token
from tests.conftest import bearer, login_user, register_user


async def test_auth_flow_register_login_me(client):
    resp = await register_user(client, 'client@example.com')
    assert resp.status_code == 200
    data = resp.json()
    assert 'access' in data and 'refresh' in data

    me = await client.get('/api/auth/me', headers=bearer(data['access']))
    assert me.status_code == 200
    assert me.json()['email'] == 'client@example.com'
    assert me.json()['role'] == 'client'


async def test_auth_me_requires_token(client):
    resp = await client.get('/api/auth/me')
    assert resp.status_code == 401


async def test_register_duplicate_email_returns_409(client):
    first = await register_user(client, 'dup@example.com')
    assert first.status_code == 200
    second = await register_user(client, 'dup@example.com')
    assert second.status_code == 409


async def test_login_wrong_password_returns_401(client):
    await register_user(client, 'user@example.com')
    resp = await login_user(client, 'user@example.com', password='WrongPass123!')
    assert resp.status_code == 401


async def test_login_ok_returns_tokens(client):
    await register_user(client, 'user@example.com')
    resp = await login_user(client, 'user@example.com')
    assert resp.status_code == 200
    assert 'access' in resp.json() and 'refresh' in resp.json()


async def test_refresh_and_logout_flow(client):
    await register_user(client, 'user@example.com')
    login_resp = await login_user(client, 'user@example.com')
    refresh = login_resp.json()['refresh']

    refreshed = await client.post('/api/auth/refresh', json={'refresh': refresh})
    assert refreshed.status_code == 200
    assert set(refreshed.json()) == {'access'}
    new_access = refreshed.json()['access']

    me = await client.get('/api/auth/me', headers=bearer(new_access))
    assert me.status_code == 200
    assert me.json()['role'] == 'client'

    # Новый access-токен выпущен для того же пользователя и с тем же сроком.
    payload = decode_token(new_access)
    assert payload['sub'] == me.json()['id']
    assert payload['role'] == 'client'
    assert payload['exp'] > payload['iat']
    assert payload['jti']
    assert new_access != login_resp.json()['access']

    out = await client.post(
        '/api/auth/logout',
        json={'refresh': refresh},
        headers=bearer(login_resp.json()['access']),
    )
    assert out.status_code == 200

    reuse = await client.post('/api/auth/refresh', json={'refresh': refresh})
    assert reuse.status_code == 401


# --- Безопасность после аудита ---


async def test_register_ignores_requested_role(client):
    """Публичная регистрация не должна позволять стать админом."""
    resp = await client.post('/api/auth/register', json={
        'email': 'sneaky@example.com',
        'password': 'Pass1234!',
        'role': 'admin',
    })
    assert resp.status_code == 200

    me = await client.get('/api/auth/me', headers=bearer(resp.json()['access']))
    assert me.status_code == 200
    assert me.json()['role'] == 'client'


async def test_invalid_access_token_returns_401(client):
    resp = await client.get('/api/auth/me', headers=bearer('not-a-real-token'))
    assert resp.status_code == 401


async def test_expired_access_token_returns_401(client):
    from jose import jwt

    from app.config import settings

    now = datetime.now(timezone.utc)
    expired = jwt.encode(
        {
            'sub': 'someone',
            'role': 'client',
            'iat': int((now - timedelta(hours=2)).timestamp()),
            'exp': int((now - timedelta(hours=1)).timestamp()),
        },
        settings.SECRET_KEY,
        algorithm='HS256',
    )
    resp = await client.get('/api/auth/me', headers=bearer(expired))
    assert resp.status_code == 401


async def test_expired_refresh_token_returns_401(client):
    from app import auth as auth_module

    await register_user(client, 'user@example.com')
    login_resp = await login_user(client, 'user@example.com')
    refresh = login_resp.json()['refresh']

    past = datetime.now(timezone.utc) - timedelta(days=1)
    await auth_module.refresh_col.update_one(
        {'jti': refresh},
        {'$set': {'expires_at': past}},
    )

    resp = await client.post('/api/auth/refresh', json={'refresh': refresh})
    assert resp.status_code == 401


async def test_inactive_user_cannot_login_or_use_token(client):
    from app import auth as auth_module

    await register_user(client, 'blocked@example.com')
    login_resp = await login_user(client, 'blocked@example.com')
    access = login_resp.json()['access']

    await auth_module.users_col.update_one(
        {'email': 'blocked@example.com'},
        {'$set': {'is_active': False}},
    )

    login_again = await login_user(client, 'blocked@example.com')
    assert login_again.status_code == 403

    me = await client.get('/api/auth/me', headers=bearer(access))
    assert me.status_code == 403


async def test_logout_with_foreign_refresh_token_returns_403(client):
    await register_user(client, 'first@example.com')
    await register_user(client, 'second@example.com')

    first_login = await login_user(client, 'first@example.com')
    second_login = await login_user(client, 'second@example.com')

    resp = await client.post(
        '/api/auth/logout',
        json={'refresh': second_login.json()['refresh']},
        headers=bearer(first_login.json()['access']),
    )
    assert resp.status_code == 403


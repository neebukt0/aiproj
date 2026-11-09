from datetime import datetime, timedelta, timezone

import pytest

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
    new_access = refreshed.json()['access']

    me = await client.get('/api/auth/me', headers=bearer(new_access))
    assert me.status_code == 200

    out = await client.post(
        '/api/auth/logout',
        json={'refresh': refresh},
        headers=bearer(login_resp.json()['access']),
    )
    assert out.status_code == 200

    reuse = await client.post('/api/auth/refresh', json={'refresh': refresh})
    assert reuse.status_code == 401

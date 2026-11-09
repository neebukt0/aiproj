import pytest

from tests.conftest import bearer, login_user, register_user


async def create_resource(client, token: dict, name: str = 'Тестовая переговорная') -> str:
    resp = await client.post('/api/resources', json={
        'name': name,
        'resource_type': 'private_room',
        'capacity': 6,
        'description': 'Тестовый ресурс',
        'image': None,
    }, headers=bearer(token['access']))
    return resp.json()['id']


async def register_and_login(client, email: str, role: str = 'client') -> dict:
    await register_user(client, email, role=role)
    resp = await login_user(client, email)
    return resp.json()


async def create_booking(client, token: str, resource_id: str, start_hour: int = 10, end_hour: int = 12) -> dict:
    start = f'2026-11-20T{start_hour:02d}:00:00Z'
    end = f'2026-11-20T{end_hour:02d}:00:00Z'
    resp = await client.post('/api/bookings', json={
        'resource_id': resource_id,
        'start_at': start,
        'end_at': end,
    }, headers=bearer(token))
    return resp


async def test_booking_requires_auth(client):
    resp = await client.post('/api/bookings', json={
        'resource_id': 'some-id',
        'start_at': '2026-11-20T10:00:00Z',
        'end_at': '2026-11-20T12:00:00Z',
    })
    assert resp.status_code == 401


async def test_create_booking_success(client):
    tokens = await register_and_login(client, 'client@example.com')
    employee_token = await register_and_login(client, 'employee@example.com', role='employee')
    resource_id = await create_resource(client, employee_token)

    resp = await create_booking(client, tokens['access'], resource_id)
    assert resp.status_code == 200
    data = resp.json()
    assert data['status'] == 'created'
    assert data['user_id']
    assert data['resource_id'] == resource_id


async def test_create_booking_conflict_returns_409(client):
    tokens = await register_and_login(client, 'client@example.com')
    employee_token = await register_and_login(client, 'employee@example.com', role='employee')
    resource_id = await create_resource(client, employee_token)

    payload = {
        'resource_id': resource_id,
        'start_at': '2026-11-20T10:00:00Z',
        'end_at': '2026-11-20T12:00:00Z',
    }
    first = await client.post('/api/bookings', json=payload, headers=bearer(tokens['access']))
    assert first.status_code == 200

    second = await client.post('/api/bookings', json=payload, headers=bearer(tokens['access']))
    assert second.status_code == 409


async def test_create_booking_no_conflict_for_disjoint_time(client):
    tokens = await register_and_login(client, 'client@example.com')
    employee_token = await register_and_login(client, 'employee@example.com', role='employee')
    resource_id = await create_resource(client, employee_token)

    payload = {
        'resource_id': resource_id,
        'start_at': '2026-11-20T10:00:00Z',
        'end_at': '2026-11-20T12:00:00Z',
    }
    first = await client.post('/api/bookings', json=payload, headers=bearer(tokens['access']))
    assert first.status_code == 200

    payload2 = {
        'resource_id': resource_id,
        'start_at': '2026-11-20T12:00:00Z',
        'end_at': '2026-11-20T14:00:00Z',
    }
    second = await client.post('/api/bookings', json=payload2, headers=bearer(tokens['access']))
    assert second.status_code == 200


async def test_create_booking_nonexistent_resource_returns_404(client):
    tokens = await register_and_login(client, 'client@example.com')
    resp = await client.post('/api/bookings', json={
        'resource_id': '00000000-0000-0000-0000-000000000000',
        'start_at': '2026-11-20T10:00:00Z',
        'end_at': '2026-11-20T12:00:00Z',
    }, headers=bearer(tokens['access']))
    assert resp.status_code == 404


# --- Статусы брони ---


async def _setup_booking_with_token(client):
    client_token = await register_and_login(client, 'client@example.com')
    employee_token = await register_and_login(client, 'employee@example.com', role='employee')
    resource_id = await create_resource(client, employee_token)
    resp = await create_booking(client, client_token['access'], resource_id)
    assert resp.status_code == 200
    booking_id = resp.json()['id']
    return client_token, employee_token, resource_id, booking_id


async def test_status_created_to_confirmed_by_employee(client):
    client_token, employee_token, resource_id, booking_id = await _setup_booking_with_token(client)
    confirm = await client.post(
        f'/api/bookings/{booking_id}/status',
        json={'status': 'confirmed'},
        headers=bearer(employee_token['access']),
    )
    assert confirm.status_code == 200


async def test_status_confirmed_to_completed_by_employee(client):
    client_token, employee_token, resource_id, booking_id = await _setup_booking_with_token(client)
    await client.post(
        f'/api/bookings/{booking_id}/status',
        json={'status': 'confirmed'},
        headers=bearer(employee_token['access']),
    )
    complete = await client.post(
        f'/api/bookings/{booking_id}/status',
        json={'status': 'completed'},
        headers=bearer(employee_token['access']),
    )
    assert complete.status_code == 200


async def test_status_invalid_transition_returns_409(client):
    client_token, employee_token, resource_id, booking_id = await _setup_booking_with_token(client)
    invalid = await client.post(
        f'/api/bookings/{booking_id}/status',
        json={'status': 'completed'},
        headers=bearer(employee_token['access']),
    )
    assert invalid.status_code == 409


async def test_status_terminal_state_cannot_change(client):
    client_token, employee_token, resource_id, booking_id = await _setup_booking_with_token(client)
    await client.post(
        f'/api/bookings/{booking_id}/status',
        json={'status': 'confirmed'},
        headers=bearer(employee_token['access']),
    )
    await client.post(
        f'/api/bookings/{booking_id}/status',
        json={'status': 'completed'},
        headers=bearer(employee_token['access']),
    )
    cancel = await client.post(
        f'/api/bookings/{booking_id}/status',
        json={'status': 'cancelled'},
        headers=bearer(employee_token['access']),
    )
    assert cancel.status_code == 409


async def test_client_cannot_confirm_booking(client):
    client_token, employee_token, resource_id, booking_id = await _setup_booking_with_token(client)
    confirm = await client.post(
        f'/api/bookings/{booking_id}/status',
        json={'status': 'confirmed'},
        headers=bearer(client_token['access']),
    )
    assert confirm.status_code == 403


async def test_client_can_cancel_own_booking(client):
    client_token, employee_token, resource_id, booking_id = await _setup_booking_with_token(client)
    cancel = await client.post(
        f'/api/bookings/{booking_id}/status',
        json={'status': 'cancelled'},
        headers=bearer(client_token['access']),
    )
    assert cancel.status_code == 200
    cancel_resp = await client.post(
        f'/api/bookings/{booking_id}/status',
        json={'status': 'cancelled'},
        headers=bearer(client_token['access']),
    )
    assert cancel_resp.status_code == 409


async def test_concurrent_booking_only_one_succeeds(client):
    """10 параллельных запросов на одно место → ровно 1 бронь, остальные 409."""
    import asyncio

    tokens = await register_and_login(client, 'client@example.com')
    employee_token = await register_and_login(client, 'employee@example.com', role='employee')
    resource_id = await create_resource(client, employee_token)

    payload = {
        'resource_id': resource_id,
        'start_at': '2026-11-20T10:00:00Z',
        'end_at': '2026-11-20T12:00:00Z',
    }

    responses = await asyncio.gather(
        *[
            client.post('/api/bookings', json=payload, headers=bearer(tokens['access']))
            for _ in range(10)
        ]
    )

    ok = [r for r in responses if r.status_code == 200]
    conflicts = [r for r in responses if r.status_code == 409]
    assert len(ok) == 1
    assert len(conflicts) == 9


async def test_expired_hold_releases_resource(client):
    """После истечения held_until место можно забронировать повторно."""
    from datetime import datetime, timedelta, timezone

    from app import bookings as bookings_module

    tokens = await register_and_login(client, 'client@example.com')
    employee_token = await register_and_login(client, 'employee@example.com', role='employee')
    resource_id = await create_resource(client, employee_token)

    bookings_col = bookings_module.bookings_col
    past = datetime.now(timezone.utc) - timedelta(minutes=20)
    future = datetime.now(timezone.utc) + timedelta(hours=2)
    await bookings_col.insert_one({
        '_id': 'expired-hold-booking',
        'user_id': tokens['access'],
        'resource_id': resource_id,
        'status': 'created',
        'start_at': future,
        'end_at': future + timedelta(hours=2),
        'held_until': past,
        'created_at': past,
        'updated_at': past,
    })

    resp = await create_booking(client, tokens['access'], resource_id, start_hour=14, end_hour=16)
    assert resp.status_code == 200


async def test_expired_hold_releases_resource(client):
    """После истечения held_until место можно забронировать повторно."""
    from datetime import datetime, timedelta, timezone
    from mongomock_motor import AsyncMongoMockClient
    from app import bookings as bookings_module

    tokens = await register_and_login(client, 'client@example.com')
    employee_token = await register_and_login(client, 'employee@example.com', role='employee')
    resource_id = await create_resource(client, employee_token)

    # создадим бронь с прошедшим held_until напрямую в mongomock
    bookings_col = bookings_module.bookings_col
    past = datetime.now(timezone.utc) - timedelta(minutes=20)
    future = datetime.now(timezone.utc) + timedelta(hours=2)
    await bookings_col.insert_one({
        '_id': 'expired-hold-booking',
        'user_id': tokens['user_id'] if 'user_id' in tokens else tokens['access'],
        'resource_id': resource_id,
        'status': 'created',
        'start_at': future,
        'end_at': future + timedelta(hours=2),
        'held_until': past,
        'created_at': past,
        'updated_at': past,
    })

    resp = await create_booking(client, tokens['access'], resource_id, start_hour=14, end_hour=16)
    assert resp.status_code == 200

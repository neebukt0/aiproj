from datetime import datetime, timedelta, timezone

import pytest

from tests.conftest import bearer, register_and_login


async def create_resource(client, token: dict, name: str = 'Тестовая переговорная') -> str:
    resp = await client.post('/api/resources', json={
        'name': name,
        'resource_type': 'private_room',
        'capacity': 6,
        'description': 'Тестовый ресурс',
        'image': None,
    }, headers=bearer(token['access']))
    return resp.json()['id']


async def create_booking(client, token: str, resource_id: str, start_hour: int = 10, end_hour: int = 12, date: str = '2026-11-20') -> dict:
    start = f'{date}T{start_hour:02d}:00:00Z'
    end = f'{date}T{end_hour:02d}:00:00Z'
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


async def _setup_booking_with_token(client, date: str = '2026-11-20'):
    client_token = await register_and_login(client, 'client@example.com')
    employee_token = await register_and_login(client, 'employee@example.com', role='employee')
    resource_id = await create_resource(client, employee_token)
    resp = await create_booking(client, client_token['access'], resource_id, date=date)
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


async def test_staff_panel_lists_bookings(client):
    """Сотрудник видит брони на день через панель."""
    client_token = await register_and_login(client, 'client@example.com')
    employee_token = await register_and_login(client, 'employee@example.com', role='employee')
    resource_id = await create_resource(client, employee_token)
    await create_booking(client, client_token['access'], resource_id)

    resp = await client.get(
        '/api/bookings?date=2026-11-20',
        headers=bearer(employee_token['access']),
    )
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


async def test_client_cannot_access_staff_panel(client):
    client_token = await register_and_login(client, 'client@example.com')
    resp = await client.get('/api/bookings', headers=bearer(client_token['access']))
    assert resp.status_code == 403


async def test_booking_logs_returned(client):
    client_token, employee_token, resource_id, booking_id = await _setup_booking_with_token(client)
    await client.post(
        f'/api/bookings/{booking_id}/status',
        json={'status': 'confirmed'},
        headers=bearer(employee_token['access']),
    )
    resp = await client.get(
        f'/api/bookings/{booking_id}/logs',
        headers=bearer(employee_token['access']),
    )
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


async def test_report_requires_staff(client):
    client_token = await register_and_login(client, 'client@example.com')
    resp = await client.post('/api/reports', json={
        'start_at': '2026-11-01T00:00:00Z',
        'end_at': '2026-12-01T00:00:00Z',
    }, headers=bearer(client_token['access']))
    assert resp.status_code == 403


async def test_report_returns_aggregation(client):
    client_token = await register_and_login(client, 'client@example.com')
    employee_token = await register_and_login(client, 'employee@example.com', role='employee')
    resource_id = await create_resource(client, employee_token)
    await create_booking(client, client_token['access'], resource_id)

    resp = await client.post('/api/reports', json={
        'start_at': '2026-11-01T00:00:00Z',
        'end_at': '2026-12-31T00:00:00Z',
    }, headers=bearer(employee_token['access']))
    assert resp.status_code == 200
    data = resp.json()
    assert data['period_start'] < data['period_end']
    assert any(r['resource_id'] == resource_id for r in data['rows'])


async def test_report_csv_export(client):
    client_token = await register_and_login(client, 'client@example.com')
    employee_token = await register_and_login(client, 'employee@example.com', role='employee')
    resource_id = await create_resource(client, employee_token)
    await create_booking(client, client_token['access'], resource_id)

    resp = await client.post('/api/reports/csv', json={
        'start_at': '2026-11-01T00:00:00Z',
        'end_at': '2026-12-31T00:00:00Z',
    }, headers=bearer(employee_token['access']))
    assert resp.status_code == 200
    assert 'resource_name' in resp.text


async def test_logs_list_requires_staff(client):
    client_token = await register_and_login(client, 'client@example.com')
    resp = await client.get('/api/logs', headers=bearer(client_token['access']))
    assert resp.status_code == 403


async def test_admin_can_list_users(client):
    admin_token = await register_and_login(client, 'admin@example.com', role='admin')
    resp = await client.get('/api/admin/users', headers=bearer(admin_token['access']))
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


async def test_admin_can_delete_resource(client):
    admin_token = await register_and_login(client, 'admin@example.com', role='admin')
    resource_id = await create_resource(client, admin_token)
    resp = await client.delete(
        f'/api/resources/{resource_id}',
        headers=bearer(admin_token['access']),
    )
    assert resp.status_code == 200


# --- Новые проверки после аудита ---


async def test_admin_can_create_staff_user(client):
    admin_token = await register_and_login(client, 'admin@example.com', role='admin')
    resp = await client.post('/api/admin/users', json={
        'email': 'new-employee@example.com',
        'password': 'EmpPass123!',
        'role': 'employee',
    }, headers=bearer(admin_token['access']))
    assert resp.status_code == 200
    assert resp.json()['role'] == 'employee'

    login = await client.post('/api/auth/login', json={
        'email': 'new-employee@example.com',
        'password': 'EmpPass123!',
    })
    assert login.status_code == 200


async def test_client_cannot_create_staff_user(client):
    client_token = await register_and_login(client, 'client@example.com')
    resp = await client.post('/api/admin/users', json={
        'email': 'fake-admin@example.com',
        'password': 'AdminPass123!',
        'role': 'admin',
    }, headers=bearer(client_token['access']))
    assert resp.status_code == 403


async def test_booking_participants_roundtrip(client):
    client_token = await register_and_login(client, 'client@example.com')
    employee_token = await register_and_login(client, 'employee@example.com', role='employee')
    resource_id = await create_resource(client, employee_token)

    participants = await client.get('/api/admin/users', headers=bearer(employee_token['access']))
    assert participants.status_code == 403

    me = await client.get('/api/auth/me', headers=bearer(employee_token['access']))
    employee_id = me.json()['id']

    resp = await client.post('/api/bookings', json={
        'resource_id': resource_id,
        'start_at': '2026-11-20T10:00:00Z',
        'end_at': '2026-11-20T12:00:00Z',
        'participant_ids': [employee_id],
    }, headers=bearer(client_token['access']))
    assert resp.status_code == 200
    booking_id = resp.json()['id']

    listed = await client.get(
        f'/api/bookings/{booking_id}/participants',
        headers=bearer(client_token['access']),
    )
    assert listed.status_code == 200
    assert [p['user_id'] for p in listed.json()] == [employee_id]


async def test_booking_participants_hidden_from_strangers(client):
    client_token = await register_and_login(client, 'client@example.com')
    employee_token = await register_and_login(client, 'employee@example.com', role='employee')
    stranger_token = await register_and_login(client, 'stranger@example.com')
    resource_id = await create_resource(client, employee_token)
    booking = await create_booking(client, client_token['access'], resource_id)
    booking_id = booking.json()['id']

    resp = await client.get(
        f'/api/bookings/{booking_id}/participants',
        headers=bearer(stranger_token['access']),
    )
    assert resp.status_code == 403


async def test_booking_rejects_end_before_start(client):
    client_token = await register_and_login(client, 'client@example.com')
    employee_token = await register_and_login(client, 'employee@example.com', role='employee')
    resource_id = await create_resource(client, employee_token)

    resp = await client.post('/api/bookings', json={
        'resource_id': resource_id,
        'start_at': '2026-11-20T12:00:00Z',
        'end_at': '2026-11-20T10:00:00Z',
    }, headers=bearer(client_token['access']))
    assert resp.status_code == 400


async def test_booking_rejects_unknown_participant(client):
    client_token = await register_and_login(client, 'client@example.com')
    employee_token = await register_and_login(client, 'employee@example.com', role='employee')
    resource_id = await create_resource(client, employee_token)

    resp = await client.post('/api/bookings', json={
        'resource_id': resource_id,
        'start_at': '2026-11-20T10:00:00Z',
        'end_at': '2026-11-20T12:00:00Z',
        'participant_ids': ['00000000-0000-0000-0000-000000000000'],
    }, headers=bearer(client_token['access']))
    assert resp.status_code == 400


async def test_concurrent_confirm_only_one_succeeds(client):
    """Два параллельных подтверждения: одно 200, второе 409."""
    import asyncio

    client_token, employee_token, resource_id, booking_id = await _setup_booking_with_token(client)

    responses = await asyncio.gather(
        *[
            client.post(
                f'/api/bookings/{booking_id}/status',
                json={'status': 'confirmed'},
                headers=bearer(employee_token['access']),
            )
            for _ in range(2)
        ]
    )
    codes = sorted(r.status_code for r in responses)
    assert codes == [200, 409]


async def test_report_rejects_inverted_period(client):
    employee_token = await register_and_login(client, 'employee@example.com', role='employee')
    resp = await client.post('/api/reports', json={
        'start_at': '2026-12-01T00:00:00Z',
        'end_at': '2026-11-01T00:00:00Z',
    }, headers=bearer(employee_token['access']))
    assert resp.status_code == 400


# --- Проверка после повторного аудита ---


async def test_confirm_extends_hold_until_end(client):
    """Подтверждённая бронь держит место до конца интервала, а не 10 минут."""
    from app import bookings as bookings_module
    from app.utils import as_utc

    # Дата должна быть в будущем: иначе held_until = end_at уже прошел
    # и проверка пересечения ($gt: now) перестаёт что-либо ловить.
    future_date = (datetime.now(timezone.utc) + timedelta(days=7)).strftime('%Y-%m-%d')
    client_token, employee_token, resource_id, booking_id = await _setup_booking_with_token(client, date=future_date)
    confirm = await client.post(
        f'/api/bookings/{booking_id}/status',
        json={'status': 'confirmed'},
        headers=bearer(employee_token['access']),
    )
    assert confirm.status_code == 200

    doc = await bookings_module.bookings_col.find_one({'_id': booking_id})
    assert as_utc(doc['held_until']) == as_utc(doc['end_at'])

    # Пересекающаяся бронь по-прежнему должна получать 409.
    overlap = await create_booking(client, client_token['access'], resource_id, start_hour=11, end_hour=13, date=future_date)
    assert overlap.status_code == 409


async def test_client_can_cancel_confirmed_booking(client):
    """Клиент может отменить и уже подтверждённую бронь (SPEC: «отменяет»)."""
    client_token, employee_token, resource_id, booking_id = await _setup_booking_with_token(client)
    await client.post(
        f'/api/bookings/{booking_id}/status',
        json={'status': 'confirmed'},
        headers=bearer(employee_token['access']),
    )
    cancel = await client.post(
        f'/api/bookings/{booking_id}/status',
        json={'status': 'cancelled'},
        headers=bearer(client_token['access']),
    )
    assert cancel.status_code == 200


async def test_resource_search_handles_special_characters(client):
    """Символы regex в поиске не должны ломать запрос."""
    employee_token = await register_and_login(client, 'employee@example.com', role='employee')
    await create_resource(client, employee_token, name='Зал (большой)')

    resp = await client.get('/api/resources', params={'search': '('})
    assert resp.status_code == 200
    assert any('(' in item['name'] for item in resp.json())

    bracket = await client.get('/api/resources', params={'search': '['})
    assert bracket.status_code == 200


async def test_availability_lists_busy_intervals(client):
    client_token = await register_and_login(client, 'client@example.com')
    employee_token = await register_and_login(client, 'employee@example.com', role='employee')
    resource_id = await create_resource(client, employee_token)
    await create_booking(client, client_token['access'], resource_id)

    resp = await client.get(
        f'/api/resources/{resource_id}/availability',
        params={'date': '2026-11-20'},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data['date'] == '2026-11-20'
    assert len(data['busy']) == 1
    assert data['busy'][0]['status'] == 'created'


async def test_availability_ignores_expired_hold(client):
    from datetime import datetime, timedelta, timezone

    from app import bookings as bookings_module

    employee_token = await register_and_login(client, 'employee@example.com', role='employee')
    resource_id = await create_resource(client, employee_token)
    past = datetime.now(timezone.utc) - timedelta(minutes=20)
    await bookings_module.bookings_col.insert_one({
        '_id': 'expired-availability-booking',
        'user_id': 'someone',
        'resource_id': resource_id,
        'status': 'created',
        'start_at': datetime(2026, 11, 20, 10, tzinfo=timezone.utc),
        'end_at': datetime(2026, 11, 20, 12, tzinfo=timezone.utc),
        'held_until': past,
        'created_at': past,
        'updated_at': past,
    })

    resp = await client.get(
        f'/api/resources/{resource_id}/availability',
        params={'date': '2026-11-20'},
    )
    assert resp.status_code == 200
    assert resp.json()['busy'] == []


async def test_availability_validates_resource_and_date(client):
    employee_token = await register_and_login(client, 'employee@example.com', role='employee')
    resource_id = await create_resource(client, employee_token)

    missing = await client.get('/api/resources/unknown-id/availability')
    assert missing.status_code == 404

    bad_date = await client.get(
        f'/api/resources/{resource_id}/availability',
        params={'date': '20.11.2026'},
    )
    assert bad_date.status_code == 400


async def test_foreign_booking_is_not_accessible(client):
    """Клиент A не должен получать бронь клиента B по прямому URL."""
    owner_token = await register_and_login(client, 'owner@example.com')
    stranger_token = await register_and_login(client, 'stranger@example.com')
    employee_token = await register_and_login(client, 'employee@example.com', role='employee')
    resource_id = await create_resource(client, employee_token)
    booking = await create_booking(client, owner_token['access'], resource_id)
    booking_id = booking.json()['id']

    resp = await client.get(
        f'/api/bookings/{booking_id}',
        headers=bearer(stranger_token['access']),
    )
    assert resp.status_code == 403

    # Владелец и staff по-прежнему имеют доступ.
    owner = await client.get(
        f'/api/bookings/{booking_id}',
        headers=bearer(owner_token['access']),
    )
    assert owner.status_code == 200
    staff = await client.get(
        f'/api/bookings/{booking_id}',
        headers=bearer(employee_token['access']),
    )
    assert staff.status_code == 200



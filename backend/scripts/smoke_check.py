"""Сквозной smoke-тест API на живом сервере.

37 проверок: health, авторизация и роли, каталог, занятость, бронирование,
конфликт 409, подтверждение, недопустимый переход, отмена, панель, журнал,
отчёты и CSV, админ-операции, refresh/logout/blacklist.

Нужен запущенный backend с демо-данными (python scripts/seed.py).

Пример:
    python scripts/smoke_check.py
    python scripts/smoke_check.py --base-url http://127.0.0.1:8000
"""

import argparse
import asyncio
import sys
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from httpx import AsyncClient

ACTIVE_STATUSES = ('created', 'confirmed')


def parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


async def run(
    base_url: str,
    client_email: str,
    client_password: str,
    employee_email: str,
    employee_password: str,
    admin_email: str,
    admin_password: str,
) -> int:
    ok = True
    passed = 0
    failed = 0

    def check(name: str, condition: bool, detail: str = '') -> None:
        nonlocal ok, passed, failed
        ok = ok and condition
        if condition:
            passed += 1
            print(f'OK   {name}')
        else:
            failed += 1
            print(f'FAIL {name}{(" — " + detail) if detail else ""}')

    def headers(token: str) -> dict:
        return {'Authorization': f'Bearer {token}'}

    async def login(ac: AsyncClient, email: str, password: str):
        response = await ac.post('/api/auth/login', json={'email': email, 'password': password})
        if response.status_code != 200:
            return None
        return response.json()

    now = datetime.now(timezone.utc)
    tomorrow_dt = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = tomorrow_dt.strftime('%Y-%m-%d')

    async with AsyncClient(base_url=base_url, timeout=20) as ac:
        print('health')
        health = await ac.get('/health')
        check(
            'GET /health',
            health.status_code == 200 and health.json().get('status') == 'ok',
            f'status={health.status_code}',
        )

        print('auth')
        client = await login(ac, client_email, client_password)
        employee = await login(ac, employee_email, employee_password)
        admin = await login(ac, admin_email, admin_password)
        check(
            'login all roles',
            all(tokens and tokens.get('access') and tokens.get('refresh')
                for tokens in (client, employee, admin)),
            'client/employee/admin',
        )
        if not (client and employee and admin):
            print('\nRESULT: FAILED')
            return 1

        client_h = headers(client['access'])
        employee_h = headers(employee['access'])
        admin_h = headers(admin['access'])

        me = await ac.get('/api/auth/me', headers=client_h)
        check(
            'GET /me',
            me.status_code == 200 and me.json().get('role') == 'client',
            f'status={me.status_code}',
        )

        bad = await ac.get('/api/auth/me', headers=headers('broken-token'))
        check('invalid token -> 401', bad.status_code == 401, f'status={bad.status_code}')

        print('catalog')
        page = await ac.get('/api/resources', params={'limit': 5, 'skip': 0})
        check(
            'catalog page size',
            page.status_code == 200 and len(page.json()) == 5,
            f'status={page.status_code}, len={len(page.json()) if page.status_code == 200 else "-"}',
        )

        all_resources = await ac.get('/api/resources', params={'limit': 100})
        check(
            'catalog total 20',
            all_resources.status_code == 200 and len(all_resources.json()) == 20,
            f'status={all_resources.status_code}, '
            f'len={len(all_resources.json()) if all_resources.status_code == 200 else "-"}',
        )

        halls = await ac.get('/api/resources', params={'resource_type': 'hall', 'limit': 100})
        check(
            'filter by type',
            halls.status_code == 200
            and bool(halls.json())
            and all(item['resource_type'] == 'hall' for item in halls.json()),
            f'status={halls.status_code}',
        )

        found = await ac.get('/api/resources', params={'search': 'альфа'})
        check(
            'search case-insensitive',
            found.status_code == 200 and any('Альфа' in item['name'] for item in found.json()),
            f'status={found.status_code}',
        )

        paren = await ac.get('/api/resources', params={'search': '('})
        check('search special char -> 200', paren.status_code == 200, f'status={paren.status_code}')

        resource = found.json()[0] if found.status_code == 200 and found.json() else None
        rid = resource['id'] if resource else None
        detail = await ac.get(f'/api/resources/{rid}') if rid else None
        missing = await ac.get('/api/resources/00000000-0000-0000-0000-000000000000')
        check(
            'resource card',
            detail is not None
            and detail.status_code == 200
            and detail.json().get('id') == rid
            and missing.status_code == 404,
            f'detail={detail.status_code if detail else "-"}, missing={missing.status_code}',
        )

        print('availability')
        panel_seed = await ac.get(
            '/api/bookings',
            params={'date': tomorrow},
            headers=employee_h,
        )
        seed_active = None
        if panel_seed.status_code == 200:
            seed_active = next(
                (
                    booking
                    for booking in panel_seed.json()
                    if booking.get('status') in ACTIVE_STATUSES
                    and parse_dt(booking['held_until']) > now
                ),
                None,
            )
        seed_rid = seed_active['resource_id'] if seed_active else rid

        availability = await ac.get(
            f'/api/resources/{seed_rid}/availability',
            params={'date': tomorrow},
        )
        check(
            'availability 200',
            availability.status_code == 200
            and availability.json().get('resource_id') == seed_rid
            and availability.json().get('date') == tomorrow,
            f'status={availability.status_code}',
        )
        check(
            'seed busy shown',
            availability.status_code == 200 and len(availability.json().get('busy', [])) >= 1,
            f'busy={len(availability.json().get("busy", [])) if availability.status_code == 200 else "-"}',
        )

        print('booking')
        start = f'{tomorrow}T17:00:00Z'
        end = f'{tomorrow}T18:00:00Z'
        payload = {'resource_id': rid, 'start_at': start, 'end_at': end}

        first = await ac.post('/api/bookings', json=payload, headers=client_h)
        booking_id = first.json().get('id') if first.status_code == 200 else None
        check(
            'create booking',
            first.status_code == 200
            and booking_id is not None
            and first.json().get('status') == 'created'
            and parse_dt(first.json()['held_until']) > now,
            f'status={first.status_code}',
        )

        conflict = await ac.post('/api/bookings', json=payload, headers=client_h)
        check('double booking -> 409', conflict.status_code == 409, f'status={conflict.status_code}')

        noauth = await ac.post('/api/bookings', json=payload)
        check('booking without token -> 401', noauth.status_code == 401, f'status={noauth.status_code}')

        mine = await ac.get('/api/bookings/mine', headers=client_h)
        check(
            'my bookings',
            mine.status_code == 200
            and booking_id is not None
            and any(item['id'] == booking_id for item in mine.json()),
            f'status={mine.status_code}',
        )

        print('statuses + hold')
        forbidden = await ac.post(
            f'/api/bookings/{booking_id}/status',
            json={'status': 'confirmed'},
            headers=client_h,
        )
        check('client cannot confirm -> 403', forbidden.status_code == 403, f'status={forbidden.status_code}')

        confirm = await ac.post(
            f'/api/bookings/{booking_id}/status',
            json={'status': 'confirmed'},
            headers=employee_h,
        )
        check('employee confirms', confirm.status_code == 200, f'status={confirm.status_code}')

        full = await ac.get(f'/api/bookings/{booking_id}', headers=employee_h)
        check(
            'confirmed hold == end',
            full.status_code == 200
            and abs((parse_dt(full.json()['held_until']) - parse_dt(full.json()['end_at'])).total_seconds()) < 1,
            f'status={full.status_code}',
        )

        availability_confirmed = await ac.get(
            f'/api/resources/{rid}/availability',
            params={'date': tomorrow},
        )
        check(
            'confirmed visible in availability',
            availability_confirmed.status_code == 200
            and any(
                'T17:00' in item['start_at'] and item.get('status') == 'confirmed'
                for item in availability_confirmed.json().get('busy', [])
            ),
            f'status={availability_confirmed.status_code}',
        )

        invalid = await ac.post(
            f'/api/bookings/{booking_id}/status',
            json={'status': 'created'},
            headers=employee_h,
        )
        check('invalid transition -> 409', invalid.status_code == 409, f'status={invalid.status_code}')

        cancel = await ac.post(
            f'/api/bookings/{booking_id}/status',
            json={'status': 'cancelled'},
            headers=client_h,
        )
        check('client cancels confirmed', cancel.status_code == 200, f'status={cancel.status_code}')

        availability_cancelled = await ac.get(
            f'/api/resources/{rid}/availability',
            params={'date': tomorrow},
        )
        check(
            'cancelled slot freed',
            availability_cancelled.status_code == 200
            and not any(
                'T17:00' in item['start_at']
                for item in availability_cancelled.json().get('busy', [])
            ),
            f'status={availability_cancelled.status_code}',
        )

        print('staff panels')
        panel = await ac.get(
            '/api/bookings',
            params={'date': tomorrow},
            headers=employee_h,
        )
        check(
            'panel by date',
            panel.status_code == 200
            and booking_id is not None
            and any(item['id'] == booking_id for item in panel.json()),
            f'status={panel.status_code}',
        )

        client_panel = await ac.get('/api/bookings', headers=client_h)
        check('client panel -> 403', client_panel.status_code == 403, f'status={client_panel.status_code}')

        blog = await ac.get(f'/api/bookings/{booking_id}/logs', headers=employee_h)
        check(
            'booking logs',
            blog.status_code == 200 and len(blog.json()) >= 1,
            f'status={blog.status_code}',
        )

        alllogs = await ac.get('/api/logs', headers=employee_h)
        check(
            'global logs',
            alllogs.status_code == 200 and len(alllogs.json()) >= 1,
            f'status={alllogs.status_code}',
        )

        print('reports')
        period = {
            'start_at': f'{tomorrow}T00:00:00Z',
            'end_at': (now + timedelta(days=4)).strftime('%Y-%m-%dT00:00:00Z'),
        }
        rep = await ac.post('/api/reports', json=period, headers=employee_h)
        check(
            'report',
            rep.status_code == 200 and len(rep.json().get('rows', [])) >= 1,
            f'status={rep.status_code}',
        )

        client_rep = await ac.post('/api/reports', json=period, headers=client_h)
        check('client report -> 403', client_rep.status_code == 403, f'status={client_rep.status_code}')

        csv = await ac.post('/api/reports/csv', json=period, headers=employee_h)
        check(
            'csv export',
            csv.status_code == 200
            and 'resource_name' in csv.text
            and csv.headers.get('content-type', '').startswith('text/csv'),
            f'status={csv.status_code}',
        )

        print('admin')
        users = await ac.get('/api/admin/users', headers=admin_h)
        check(
            'admin users',
            users.status_code == 200 and len(users.json()) >= 3,
            f'status={users.status_code}',
        )

        staff_email = f'smoke-staff-{uuid4().hex[:8]}@example.com'
        staff_password = 'SmokePass123!'
        created = await ac.post(
            '/api/admin/users',
            json={'email': staff_email, 'password': staff_password, 'role': 'employee'},
            headers=admin_h,
        )
        staff_id = created.json().get('id') if created.status_code == 200 else None
        check(
            'admin creates employee',
            created.status_code == 200 and created.json().get('role') == 'employee',
            f'status={created.status_code}',
        )

        patched = await ac.patch(
            f'/api/admin/users/{staff_id}',
            json={'is_active': False},
            headers=admin_h,
        ) if staff_id else None
        check(
            'admin deactivates user',
            patched is not None
            and patched.status_code == 200
            and patched.json().get('is_active') is False,
            f'status={patched.status_code if patched else "-"}',
        )

        deleted = await ac.delete(f'/api/admin/users/{staff_id}', headers=admin_h) if staff_id else None
        deleted_login = (
            await ac.post('/api/auth/login', json={'email': staff_email, 'password': staff_password})
            if staff_id else None
        )
        check(
            'admin deletes user',
            deleted is not None
            and deleted.status_code == 200
            and deleted_login is not None
            and deleted_login.status_code == 401,
            f'delete={deleted.status_code if deleted else "-"}, '
            f'login={deleted_login.status_code if deleted_login else "-"}',
        )

        print('token lifecycle')
        refreshed = await ac.post('/api/auth/refresh', json={'refresh': client['refresh']})
        new_access = refreshed.json().get('access') if refreshed.status_code == 200 else None
        check(
            'refresh',
            refreshed.status_code == 200 and bool(new_access) and new_access != client['access'],
            f'status={refreshed.status_code}',
        )

        logout = await ac.post(
            '/api/auth/logout',
            json={'refresh': client['refresh']},
            headers=headers(new_access) if new_access else client_h,
        )
        check('logout', logout.status_code == 200, f'status={logout.status_code}')

        reuse = await ac.post('/api/auth/refresh', json={'refresh': client['refresh']})
        check('revoked refresh -> 401', reuse.status_code == 401, f'status={reuse.status_code}')

    print(f'\nchecks: {passed} passed, {failed} failed')
    print('RESULT:', 'OK' if ok else 'FAILED')
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:8000')
    parser.add_argument('--client-email', default='client@example.com')
    parser.add_argument('--client-password', default='ClientPass123!')
    parser.add_argument('--employee-email', default='employee@example.com')
    parser.add_argument('--employee-password', default='EmpPass123!')
    parser.add_argument('--admin-email', default='admin@example.com')
    parser.add_argument('--admin-password', default='AdminPass123!')
    args = parser.parse_args()
    return asyncio.run(run(
        args.base_url,
        args.client_email,
        args.client_password,
        args.employee_email,
        args.employee_password,
        args.admin_email,
        args.admin_password,
    ))


if __name__ == '__main__':
    sys.exit(main())

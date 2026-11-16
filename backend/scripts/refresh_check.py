"""Проверка обновления access-токена на живом сервере.

Сценарий:
1. Вход по email/паролю → access + refresh.
2. Защищённый запрос со старым access → 200.
3. POST /api/auth/refresh с refresh → новый access.
4. Защищённый запрос с новым access → 200.
5. Выход: refresh помечается отозванным.
6. Повторный /refresh с тем же refresh → 401.

Пример:
    python scripts/refresh_check.py --email client@example.com --password ClientPass123!
"""

import argparse
import asyncio
import sys

from httpx import AsyncClient


async def run(base_url: str, email: str, password: str) -> int:
    ok = True

    def check(name: str, condition: bool, detail: str = '') -> None:
        nonlocal ok
        ok = ok and condition
        print(f"{'OK  ' if condition else 'FAIL'} {name}{(' — ' + detail) if detail else ''}")

    async with AsyncClient(base_url=base_url, timeout=15) as ac:
        login = await ac.post('/api/auth/login', json={'email': email, 'password': password})
        check('login', login.status_code == 200, f'status={login.status_code}')
        if login.status_code != 200:
            return 1
        tokens = login.json()
        access, refresh = tokens['access'], tokens['refresh']
        check('login returns access+refresh', bool(access) and bool(refresh))

        me_old = await ac.get('/api/auth/me', headers={'Authorization': f'Bearer {access}'})
        check('protected call with old access', me_old.status_code == 200, f'status={me_old.status_code}')
        user_id = me_old.json().get('id') if me_old.status_code == 200 else None

        refreshed = await ac.post('/api/auth/refresh', json={'refresh': refresh})
        check('refresh', refreshed.status_code == 200, f'status={refreshed.status_code}')
        if refreshed.status_code != 200:
            return 1
        new_access = refreshed.json().get('access')
        check('refresh returns new access', bool(new_access))
        check('access token actually changed', new_access != access)

        me_new = await ac.get('/api/auth/me', headers={'Authorization': f'Bearer {new_access}'})
        check('protected call with new access', me_new.status_code == 200, f'status={me_new.status_code}')
        if me_new.status_code == 200:
            check('same user after refresh', me_new.json().get('id') == user_id)

        bad = await ac.get('/api/auth/me', headers={'Authorization': 'Bearer not-a-token'})
        check('garbage access rejected', bad.status_code == 401, f'status={bad.status_code}')

        logout = await ac.post(
            '/api/auth/logout',
            json={'refresh': refresh},
            headers={'Authorization': f'Bearer {new_access}'},
        )
        check('logout', logout.status_code == 200, f'status={logout.status_code}')

        reuse = await ac.post('/api/auth/refresh', json={'refresh': refresh})
        check('refresh after logout rejected', reuse.status_code == 401, f'status={reuse.status_code}')

    print('RESULT:', 'OK' if ok else 'FAILED')
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:8000')
    parser.add_argument('--email', default='client@example.com')
    parser.add_argument('--password', default='ClientPass123!')
    args = parser.parse_args()
    return asyncio.run(run(args.base_url, args.email, args.password))


if __name__ == '__main__':
    sys.exit(main())

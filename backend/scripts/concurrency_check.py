"""Проверка защиты от двойного бронирования на живом сервере.

Отправляет 10 параллельных запросов на один ресурс и проверяет, что ровно один
прошёл, а остальные получили 409. Нужен запущенный backend с загруженными
демо-данными (python scripts/seed.py).

Пример:
    python scripts/concurrency_check.py \
        --resource-id <id> --date 2026-11-20 \
        --email client@example.com --password ClientPass123!
"""

import argparse
import asyncio
import sys
from datetime import datetime, timedelta, timezone

from httpx import AsyncClient


async def run(base_url: str, email: str, password: str, resource_id: str, date: str) -> int:
    async with AsyncClient(base_url=base_url, timeout=15) as ac:
        login = await ac.post('/api/auth/login', json={'email': email, 'password': password})
        login.raise_for_status()
        headers = {'Authorization': f"Bearer {login.json()['access']}"}

        payload = {
            'resource_id': resource_id,
            'start_at': f'{date}T15:00:00Z',
            'end_at': f'{date}T16:00:00Z',
        }
        responses = await asyncio.gather(*[
            ac.post('/api/bookings', json=payload, headers=headers) for _ in range(10)
        ])

    codes = sorted(response.status_code for response in responses)
    created = codes.count(200)
    conflicts = codes.count(409)
    print(f'codes={codes}')
    print(f'created={created}, conflicts={conflicts}')

    ok = codes == [200] + [409] * 9
    print('RESULT:', 'OK' if ok else 'FAILED')
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:8000')
    parser.add_argument('--email', default='client@example.com')
    parser.add_argument('--password', default='ClientPass123!')
    parser.add_argument('--resource-id', required=True)
    parser.add_argument(
        '--date',
        default=(datetime.now(timezone.utc) + timedelta(days=2)).strftime('%Y-%m-%d'),
    )
    args = parser.parse_args()
    return asyncio.run(run(args.base_url, args.email, args.password, args.resource_id, args.date))


if __name__ == '__main__':
    sys.exit(main())

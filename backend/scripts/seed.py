from datetime import datetime, timedelta, timezone
from uuid import uuid4

from passlib.context import CryptContext

from app.database import db

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


async def main() -> None:
    users_col = db.users
    resources_col = db.resources
    bookings_col = db.bookings
    status_logs_col = db.status_logs
    refresh_col = db.refresh_tokens
    participants_col = db.booking_participants

    # Clean collections
    await users_col.delete_many({})
    await resources_col.delete_many({})
    await bookings_col.delete_many({})
    await status_logs_col.delete_many({})
    await refresh_col.delete_many({})
    await participants_col.delete_many({})

    now = datetime.now(timezone.utc)

    demo_users = [
        ('client@example.com', 'client', 'ClientPass123!'),
        ('employee@example.com', 'employee', 'EmpPass123!'),
        ('admin@example.com', 'admin', 'AdminPass123!'),
    ]
    user_ids = {}
    for email, role, password in demo_users:
        user_id = str(uuid4())
        await users_col.insert_one({
            '_id': user_id,
            'email': email,
            'password_hash': pwd_context.hash(password),
            'role': role,
            'is_active': True,
            'created_at': now,
            'updated_at': now,
        })
        user_ids[role] = user_id

    resource_names = [
        ('Зал «Альфа»', 'hall', 80),
        ('Зал «Бета»', 'hall', 60),
        ('Зал «Вторая линия»', 'hall', 40),
        ('Переговорная «Организатор»', 'private_room', 12),
        ('Переговорная «Инвестор»', 'private_room', 8),
        ('Переговорная «Стартап»', 'private_room', 6),
        ('Переговорная «Клуб»', 'private_room', 10),
        ('Лофт «Кузница»', 'hall', 50),
        ('Библиотека зала', 'hall', 30),
        ('Коворкинг-зал «Точка»', 'hall', 35),
        ('Выставочный зал «Меридиан»', 'hall', 70),
        ('Коворкинг-зал «Вектор»', 'hall', 45),
        ('Переговорная «Север»', 'private_room', 8),
        ('Переговорная «Юг»', 'private_room', 8),
        ('Мини-зал «Комната»', 'private_room', 4),
        ('Гостевая зона «Встреча»', 'hall', 20),
        ('Коворкинг-зал «Горизонт»', 'hall', 55),
        ('Коворкинг-зал «Вертикаль»', 'hall', 50),
        ('Зал «Форсаж»', 'hall', 90),
    ]
    resource_ids = []
    for i, (name, rtype, capacity) in enumerate(resource_names):
        rid = str(uuid4())
        resource_ids.append(rid)
        await resources_col.insert_one({
            '_id': rid,
            'name': name,
            'resource_type': rtype,
            'capacity': capacity,
            'image': None,
            'description': f'Объект {i + 1} — {name}',
            'created_at': now,
            'updated_at': now,
        })

    statuses = ['created', 'confirmed', 'completed', 'cancelled']
    bookings = []
    for i in range(30):
        rid = resource_ids[i % len(resource_ids)]
        start = now + timedelta(days=(i // 10) + 1, hours=10 + (i % 5), minutes=0)
        end = start + timedelta(hours=2)
        status_value = statuses[i % 4]
        user_id = user_ids['client'] if i % 3 != 2 else user_ids['client']
        bookings.append({
            '_id': str(uuid4()),
            'user_id': user_id,
            'resource_id': rid,
            'status': status_value,
            'start_at': start,
            'end_at': end,
            'held_until': start + timedelta(minutes=10),
            'created_at': start - timedelta(days=1),
            'updated_at': start - timedelta(days=1) + timedelta(hours=1),
            'confirmed_at': start + timedelta(hours=1) if status_value == 'confirmed' else None,
            'confirmed_by': user_ids['employee'] if status_value == 'confirmed' else None,
            'cancelled_at': start + timedelta(hours=2) if status_value == 'cancelled' else None,
            'cancel_reason': 'not_needed' if status_value == 'cancelled' else '',
        })
    if bookings:
        await bookings_col.insert_many(bookings)

    # status logs for a few bookings
    logs = []
    for i, b in enumerate(bookings[:5]):
        logs.append({
            'booking_id': b['_id'],
            'from_status': 'created',
            'to_status': b['status'],
            'changed_by': user_ids['employee'] if b['status'] in ('confirmed', 'completed', 'cancelled') else None,
            'changed_at': b.get('updated_at') or now,
            'note': f'seed log {i}',
        })
    if logs:
        await status_logs_col.insert_many(logs)


if __name__ == '__main__':
    import asyncio
    import os
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    asyncio.run(main())

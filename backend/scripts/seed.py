import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from uuid import uuid4

# Позволяет запускать скрипт как `python scripts/seed.py` из каталога backend.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from passlib.context import CryptContext

from app.database import db, ensure_indexes

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


async def main() -> None:
    users_col = db.users
    resources_col = db.resources
    bookings_col = db.bookings
    status_logs_col = db.status_logs
    refresh_col = db.refresh_tokens
    participants_col = db.booking_participants
    locks_col = db.bookings_locks

    # Чистим коллекции перед наполнением.
    for collection in (
        users_col,
        resources_col,
        bookings_col,
        status_logs_col,
        refresh_col,
        participants_col,
        locks_col,
    ):
        await collection.delete_many({})

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
        ('Зал «Орбита»', 'hall', 100),
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
        bookings.append({
            '_id': str(uuid4()),
            'user_id': user_ids['client'],
            'resource_id': rid,
            'status': status_value,
            'start_at': start,
            'end_at': end,
            'held_until': start + timedelta(minutes=10),
            'created_at': start - timedelta(days=1),
            'updated_at': start - timedelta(days=1) + timedelta(hours=1),
            'confirmed_at': start + timedelta(hours=1) if status_value in ('confirmed', 'completed') else None,
            'confirmed_by': user_ids['employee'] if status_value in ('confirmed', 'completed') else None,
            'cancelled_at': start + timedelta(hours=2) if status_value == 'cancelled' else None,
            'cancel_reason': 'not_needed' if status_value == 'cancelled' else '',
        })
    await bookings_col.insert_many(bookings)

    # Журнал статусов: для каждого перехода создаём запись.
    logs = []
    for i, booking in enumerate(bookings):
        status_value = booking['status']
        if status_value == 'created':
            continue
        logs.append({
            'booking_id': booking['_id'],
            'from_status': 'created',
            'to_status': 'confirmed' if status_value == 'completed' else status_value,
            'changed_by': user_ids['employee'],
            'changed_at': booking['updated_at'],
            'note': f'seed log {i}',
        })
        if status_value == 'completed':
            logs.append({
                'booking_id': booking['_id'],
                'from_status': 'confirmed',
                'to_status': 'completed',
                'changed_by': user_ids['employee'],
                'changed_at': booking['updated_at'] + timedelta(minutes=30),
                'note': f'seed log {i} (completed)',
            })
    if logs:
        await status_logs_col.insert_many(logs)

    # Участники мероприятий (коллекция booking_participants).
    participants = []
    for booking in bookings[:15]:
        for participant_id in (user_ids['employee'], user_ids['admin']):
            participants.append({
                '_id': str(uuid4()),
                'booking_id': booking['_id'],
                'user_id': participant_id,
                'created_at': now,
            })
    if participants:
        await participants_col.insert_many(participants)

    await ensure_indexes()

    print(
        f'Seed завершён: users={len(demo_users)}, resources={len(resource_ids)}, '
        f'bookings={len(bookings)}, logs={len(logs)}, participants={len(participants)}'
    )


if __name__ == '__main__':
    asyncio.run(main())

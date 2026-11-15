from datetime import datetime, timezone

from app.utils import as_utc
from scripts import seed


async def _run_seed(mock_db):
    seed.db = mock_db

    async def noop():
        return None

    seed.ensure_indexes = noop
    await seed.main()


async def test_seed_creates_demo_data(mock_db):
    """Одна команда создаёт по пользователю на роль, 20 объектов и 30 броней."""
    await _run_seed(mock_db)

    users = await mock_db.users.find({}).to_list(None)
    assert len(users) == 3
    assert {u['role'] for u in users} == {'client', 'employee', 'admin'}
    assert len({u['email'] for u in users}) == 3

    assert await mock_db.resources.count_documents({}) == 20
    assert await mock_db.bookings.count_documents({}) == 30
    assert await mock_db.status_logs.count_documents({}) > 0
    assert await mock_db.booking_participants.count_documents({}) > 0


async def test_seed_hold_semantics(mock_db):
    """created держит место 10 минут, confirmed — до конца интервала."""
    await _run_seed(mock_db)
    now = datetime.now(timezone.utc)

    created = await mock_db.bookings.find({'status': 'created'}).to_list(None)
    confirmed = await mock_db.bookings.find({'status': 'confirmed'}).to_list(None)

    assert created and confirmed
    assert all(as_utc(b['held_until']) > now for b in created)
    assert all(as_utc(b['held_until']) == as_utc(b['end_at']) for b in confirmed)

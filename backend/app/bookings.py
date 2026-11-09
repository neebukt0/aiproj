from datetime import datetime, timedelta, timezone
from typing import List
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.errors import DuplicateKeyError

from app import schemas
from app.auth import get_current_user
from app.database import db

router = APIRouter(prefix='/api/bookings', tags=['Bookings'])

bookings_col = db.bookings
resources_col = db.resources
status_logs_col = db.status_logs
locks_col = db.bookings_locks

ACTIVE_STATUSES = ('created', 'confirmed')
VALID_TRANSITIONS = {
    'created': {'confirmed', 'cancelled'},
    'confirmed': {'completed', 'cancelled'},
}
TERMINAL_STATUSES = ('completed', 'cancelled')

LOCK_TIMEOUT = timedelta(minutes=10)


def _aware(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


async def acquire_lock(resource_id: str) -> bool:
    """Атомарно захватывает блокировку для ресурса.

    Возвращает True при успехе, False если блокировка занята.
    Истёкшие блокировки (>10 мин) освобождаются повторной попыткой.
    """
    now = datetime.now(timezone.utc)
    stale = now - LOCK_TIMEOUT
    for attempt in range(2):
        try:
            await locks_col.find_one_and_update(
                {'_id': resource_id, 'locked': {'$ne': True}},
                {'$set': {'locked': True, 'locked_at': now}},
                upsert=True,
            )
            return True
        except DuplicateKeyError:
            holder = await locks_col.find_one({'_id': resource_id})
            locked_at = _aware(holder.get('locked_at')) if holder else None
            if holder and locked_at and locked_at < stale:
                await locks_col.update_one(
                    {'_id': holder['_id'], 'locked_at': holder['locked_at']},
                    {'$set': {'locked': False}},
                )
                continue
            return False
    return False


async def release_lock(resource_id: str) -> None:
    await locks_col.update_one(
        {'_id': resource_id},
        {'$set': {'locked': False}},
    )


def _to_booking_out(doc) -> schemas.BookingOut:
    return schemas.BookingOut(
        id=str(doc['_id']),
        user_id=str(doc['user_id']),
        resource_id=str(doc['resource_id']),
        status=doc.get('status') or 'created',
        start_at=doc['start_at'],
        end_at=doc['end_at'],
        held_until=doc['held_until'],
        created_at=doc.get('created_at'),
        updated_at=doc.get('updated_at'),
    )


@router.post('', response_model=schemas.BookingOut)
async def create_booking(
    payload: schemas.BookingIn,
    user: dict = Depends(get_current_user),
):
    resource_id = payload.resource_id
    resource = await resources_col.find_one({'_id': resource_id})
    if resource is None:
        raise HTTPException(status_code=404, detail='Resource not found')

    if payload.end_at <= payload.start_at:
        raise HTTPException(status_code=400, detail='end_at must be after start_at')

    locked = await acquire_lock(resource_id)
    if not locked:
        raise HTTPException(status_code=409, detail='Resource already booked')

    try:
        now = datetime.now(timezone.utc)
        conflict = await bookings_col.find_one({
            'resource_id': resource_id,
            'status': {'$in': list(ACTIVE_STATUSES)},
            'held_until': {'$gt': now},
            'start_at': {'$lt': payload.end_at},
            'end_at': {'$gt': payload.start_at},
        })
        if conflict is not None:
            raise HTTPException(status_code=409, detail='Resource already booked')

        booking_id = str(uuid4())
        booking_doc = {
            '_id': booking_id,
            'user_id': str(user['_id']),
            'resource_id': resource_id,
            'status': 'created',
            'start_at': payload.start_at,
            'end_at': payload.end_at,
            'held_until': now + timedelta(minutes=10),
            'created_at': now,
            'updated_at': now,
        }
        await bookings_col.insert_one(booking_doc)
        return _to_booking_out(booking_doc)
    finally:
        await release_lock(resource_id)


@router.get('/mine', response_model=List[schemas.BookingOut])
async def list_my_bookings(user: dict = Depends(get_current_user)):
    cursor = bookings_col.find({'user_id': str(user['_id'])}).sort('start_at', 1)
    bookings = []
    async for doc in cursor:
        bookings.append(_to_booking_out(doc))
    return bookings


@router.post('/{booking_id}/status')
async def change_status(
    booking_id: str,
    payload: schemas.BookingStatusRequest,
    user: dict = Depends(get_current_user),
):
    booking = await bookings_col.find_one({'_id': booking_id})
    if booking is None:
        raise HTTPException(status_code=404, detail='Booking not found')

    from_status = booking.get('status') or 'created'
    to_status = payload.status

    allowed = VALID_TRANSITIONS.get(from_status, set())
    if to_status not in allowed:
        raise HTTPException(status_code=409, detail='Invalid status transition')

    owner_id = str(booking.get('user_id'))
    is_owner = owner_id == str(user['_id'])
    is_staff = user.get('role') in ('employee', 'admin')

    if to_status == 'cancelled':
        if not (is_owner or is_staff):
            raise HTTPException(status_code=403, detail='Not allowed')
    elif to_status in ('confirmed', 'completed') and not is_staff:
        raise HTTPException(status_code=403, detail='Not allowed')

    now = datetime.now(timezone.utc)
    updated = dict(booking)
    updated['status'] = to_status
    updated['updated_at'] = now
    if to_status == 'confirmed':
        updated['confirmed_at'] = now
        updated['confirmed_by'] = str(user['_id'])
    if to_status == 'cancelled':
        updated['cancelled_at'] = now
        updated['cancel_reason'] = 'cancelled'
    await bookings_col.replace_one({'_id': booking_id}, updated)
    await status_logs_col.insert_one({
        'booking_id': booking_id,
        'from_status': from_status,
        'to_status': to_status,
        'changed_by': str(user['_id']),
        'changed_at': now,
    })
    return {'ok': True, 'status': to_status}

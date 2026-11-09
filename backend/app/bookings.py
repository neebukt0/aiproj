from datetime import datetime, timedelta, timezone
from typing import List, Optional
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


@router.get('', response_model=List[schemas.BookingFullOut])
async def list_bookings(
    date: Optional[str] = None,
    resource_id: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    """Панель сотрудника/администратора: брони на день (по умолчанию — сегодня)."""
    if user.get('role') not in ('employee', 'admin'):
        raise HTTPException(status_code=403, detail='Staff only')

    query = {}
    if date:
        day_start = datetime.fromisoformat(date)
        day_end = day_start + timedelta(days=1)
        query['start_at'] = {'$gte': day_start, '$lt': day_end}
    if resource_id:
        query['resource_id'] = resource_id

    cursor = bookings_col.find(query).sort('start_at', 1)
    out = []
    async for doc in cursor:
        out.append(_to_full_out(doc))
    return out


@router.get('/{booking_id}/logs', response_model=List[schemas.StatusLogOut])
async def booking_logs(
    booking_id: str,
    user: dict = Depends(get_current_user),
):
    if user.get('role') not in ('employee', 'admin'):
        raise HTTPException(status_code=403, detail='Staff only')
    cursor = status_logs_col.find({'booking_id': booking_id}).sort('changed_at', 1)
    out = []
    async for doc in cursor:
        out.append(schemas.StatusLogOut(
            id=str(doc['_id']),
            booking_id=doc['booking_id'],
            from_status=doc.get('from_status'),
            to_status=doc['to_status'],
            changed_by=doc.get('changed_by'),
            changed_at=doc['changed_at'],
            note=doc.get('note'),
        ))
    return out


def _to_full_out(doc) -> schemas.BookingFullOut:
    base = _to_booking_out(doc)
    return schemas.BookingFullOut(
        id=base.id,
        user_id=base.user_id,
        resource_id=base.resource_id,
        status=base.status,
        start_at=base.start_at,
        end_at=base.end_at,
        held_until=base.held_until,
        created_at=base.created_at,
        updated_at=base.updated_at,
        confirmed_at=doc.get('confirmed_at'),
        confirmed_by=doc.get('confirmed_by'),
        cancelled_at=doc.get('cancelled_at'),
        cancel_reason=doc.get('cancel_reason'),
    )

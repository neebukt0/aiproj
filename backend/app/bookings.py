from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app import schemas
from app.auth import get_current_user
from app.database import db
from app.utils import as_utc

router = APIRouter(prefix='/api/bookings', tags=['Bookings'])

bookings_col = db.bookings
resources_col = db.resources
status_logs_col = db.status_logs
locks_col = db.bookings_locks
participants_col = db.booking_participants
users_col = db.users

ACTIVE_STATUSES = ('created', 'confirmed')
VALID_TRANSITIONS = {
    'created': {'confirmed', 'cancelled'},
    'confirmed': {'completed', 'cancelled'},
}
TERMINAL_STATUSES = ('completed', 'cancelled')

LOCK_TIMEOUT = timedelta(minutes=10)


async def acquire_lock(resource_id: str) -> bool:
    """Атомарно захватывает блокировку для ресурса.

    Возвращает True при успехе, False если блокировка занята.
    Истёкшие блокировки (>10 мин) освобождаются повторной попыткой.
    """
    now = datetime.now(timezone.utc)
    stale = now - LOCK_TIMEOUT
    for _ in range(2):
        try:
            await locks_col.find_one_and_update(
                {'_id': resource_id, 'locked': {'$ne': True}},
                {'$set': {'locked': True, 'locked_at': now}},
                upsert=True,
            )
            return True
        except DuplicateKeyError:
            holder = await locks_col.find_one({'_id': resource_id})
            locked_at = as_utc(holder.get('locked_at')) if holder else None
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
        start_at=as_utc(doc['start_at']),
        end_at=as_utc(doc['end_at']),
        held_until=as_utc(doc['held_until']),
        created_at=as_utc(doc.get('created_at')),
        updated_at=as_utc(doc.get('updated_at')),
    )


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
        confirmed_at=as_utc(doc.get('confirmed_at')),
        confirmed_by=doc.get('confirmed_by'),
        cancelled_at=as_utc(doc.get('cancelled_at')),
        cancel_reason=doc.get('cancel_reason'),
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

    start_at = as_utc(payload.start_at)
    end_at = as_utc(payload.end_at)
    if end_at <= start_at:
        raise HTTPException(status_code=400, detail='end_at must be after start_at')

    participant_ids = list(dict.fromkeys(payload.participant_ids or []))
    if participant_ids:
        found = await users_col.count_documents({'_id': {'$in': participant_ids}})
        if found != len(participant_ids):
            raise HTTPException(status_code=400, detail='Participant not found')

    locked = await acquire_lock(resource_id)
    if not locked:
        raise HTTPException(status_code=409, detail='Resource already booked')

    try:
        now = datetime.now(timezone.utc)
        conflict = await bookings_col.find_one({
            'resource_id': resource_id,
            'status': {'$in': list(ACTIVE_STATUSES)},
            'held_until': {'$gt': now},
            'start_at': {'$lt': end_at},
            'end_at': {'$gt': start_at},
        })
        if conflict is not None:
            raise HTTPException(status_code=409, detail='Resource already booked')

        booking_id = str(uuid4())
        booking_doc = {
            '_id': booking_id,
            'user_id': str(user['_id']),
            'resource_id': resource_id,
            'status': 'created',
            'start_at': start_at,
            'end_at': end_at,
            'held_until': now + timedelta(minutes=10),
            'created_at': now,
            'updated_at': now,
        }
        try:
            await bookings_col.insert_one(booking_doc)
            if participant_ids:
                await participants_col.insert_many([
                    {
                        '_id': str(uuid4()),
                        'booking_id': booking_id,
                        'user_id': participant_id,
                        'created_at': now,
                    }
                    for participant_id in participant_ids
                ])
        except Exception:
            await participants_col.delete_many({'booking_id': booking_id})
            await bookings_col.delete_one({'_id': booking_id})
            raise
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
    update_fields = {'status': to_status, 'updated_at': now}
    if to_status == 'confirmed':
        update_fields['confirmed_at'] = now
        update_fields['confirmed_by'] = str(user['_id'])
        # Подтверждённая бронь держит место до конца интервала, а не 10 минут:
        # иначе после истечения начального hold слот снова стал бы доступен.
        end_at = as_utc(booking.get('end_at'))
        if end_at is not None:
            update_fields['held_until'] = end_at
    if to_status == 'cancelled':
        update_fields['cancelled_at'] = now
        update_fields['cancel_reason'] = payload.note or 'cancelled'

    # Атомарный переход: параллельный запрос с тем же from_status получит 409.
    updated = await bookings_col.find_one_and_update(
        {'_id': booking_id, 'status': from_status},
        {'$set': update_fields},
        return_document=ReturnDocument.AFTER,
    )
    if updated is None:
        raise HTTPException(status_code=409, detail='Booking status changed concurrently')

    try:
        await status_logs_col.insert_one({
            'booking_id': booking_id,
            'from_status': from_status,
            'to_status': to_status,
            'changed_by': str(user['_id']),
            'changed_at': now,
            'note': payload.note,
        })
    except Exception:
        # Компенсирующая операция: возвращаем статус, если журнал не записался.
        rollback = {'$set': {
            'status': from_status,
            'updated_at': booking.get('updated_at'),
            'held_until': booking.get('held_until'),
        }}
        unset = {}
        if to_status == 'confirmed':
            unset = {'confirmed_at': '', 'confirmed_by': ''}
        if to_status == 'cancelled':
            unset = {'cancelled_at': '', 'cancel_reason': ''}
        if unset:
            rollback['$unset'] = unset
        await bookings_col.update_one({'_id': booking_id, 'status': to_status}, rollback)
        raise HTTPException(status_code=500, detail='Failed to write status log')

    return {'ok': True, 'status': to_status}


@router.get('', response_model=List[schemas.BookingFullOut])
async def list_bookings(
    date: Optional[str] = None,
    resource_id: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    """Панель сотрудника/администратора: брони на день или все брони."""
    if user.get('role') not in ('employee', 'admin'):
        raise HTTPException(status_code=403, detail='Staff only')

    query = {}
    if date:
        try:
            day_start = as_utc(datetime.fromisoformat(date))
        except ValueError:
            raise HTTPException(status_code=400, detail='Invalid date format')
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
            changed_at=as_utc(doc['changed_at']),
            note=doc.get('note'),
        ))
    return out


@router.get('/{booking_id}/participants', response_model=List[schemas.ParticipantOut])
async def booking_participants(
    booking_id: str,
    user: dict = Depends(get_current_user),
):
    booking = await bookings_col.find_one({'_id': booking_id})
    if booking is None:
        raise HTTPException(status_code=404, detail='Booking not found')

    is_owner = str(booking.get('user_id')) == str(user['_id'])
    is_staff = user.get('role') in ('employee', 'admin')
    if not (is_owner or is_staff):
        raise HTTPException(status_code=403, detail='Not allowed')

    cursor = participants_col.find({'booking_id': booking_id}).sort('created_at', 1)
    out = []
    async for doc in cursor:
        out.append(schemas.ParticipantOut(
            id=str(doc['_id']),
            booking_id=doc['booking_id'],
            user_id=doc['user_id'],
            created_at=as_utc(doc['created_at']),
        ))
    return out

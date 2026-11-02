from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from app import schemas
from app.auth import get_current_user
from app.database import db

router = APIRouter(prefix='/api/bookings', tags=['Bookings'])

bookings_col = db.bookings
resources_col = db.resources
status_logs_col = db.status_logs

ACTIVE_STATUSES = ('created', 'confirmed')


def _to_booking_out(doc) -> schemas.BookingOut:
    return schemas.BookingOut(
        id=str(doc['_id']),
        user_id=str(doc['user_id']),
        resource_id=str(doc['resource_id']),
        status=doc.get('status', 'created'),
        start_at=doc['start_at'],
        end_at=doc['end_at'],
        held_until=doc['held_until'],
        created_at=doc.get('created_at'),
        updated_at=doc.get('updated_at'),
    )


@router.post('/', response_model=schemas.BookingOut)
async def create_booking(
    payload: schemas.BookingIn,
    user: dict = Depends(get_current_user),
):
    resource_id = payload.resource_id
    resource = await resources_col.find_one({'_id': resource_id})
    if resource is None:
        raise HTTPException(status_code=404, detail='Resource not found')

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


@router.post('/{booking_id}/status')
async def change_status(booking_id: str, status_value: str, user: dict = Depends(get_current_user)):
    booking = await bookings_col.find_one({'_id': booking_id})
    if booking is None:
        raise HTTPException(status_code=404, detail='Booking not found')
    booking['status'] = status_value
    booking['updated_at'] = datetime.now(timezone.utc)
    await bookings_col.replace_one({'_id': booking_id}, booking)
    await status_logs_col.insert_one({
        'booking_id': booking_id,
        'from_status': booking.get('from_status'),
        'to_status': status_value,
        'changed_by': str(user['_id']),
        'changed_at': datetime.now(timezone.utc),
    })
    return {'ok': True}

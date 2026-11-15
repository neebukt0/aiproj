import re
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pymongo import ASCENDING

from app import schemas
from app.auth import get_current_user
from app.database import db
from app.utils import as_utc

router = APIRouter(prefix='/api/resources', tags=['Resources'])

resources_col = db.resources
bookings_col = db.bookings

ACTIVE_STATUSES = ('created', 'confirmed')


def _to_out(resource) -> schemas.ResourceOut:
    return schemas.ResourceOut(
        id=str(resource['_id']),
        name=resource['name'],
        resource_type=resource.get('resource_type', 'private_room'),
        capacity=resource.get('capacity', 1),
        image=resource.get('image'),
        description=resource.get('description'),
        created_at=as_utc(resource.get('created_at')),
        updated_at=as_utc(resource.get('updated_at')),
    )


@router.get('/{resource_id}/availability', response_model=schemas.AvailabilityOut)
async def get_availability(resource_id: str, date: Optional[str] = None):
    """Занятые интервалы объекта на день (публично, без персональных данных)."""
    resource = await resources_col.find_one({'_id': resource_id})
    if resource is None:
        raise HTTPException(status_code=404, detail='Resource not found')

    if date:
        try:
            day_start = datetime.strptime(date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(status_code=400, detail='Invalid date format, expected YYYY-MM-DD')
    else:
        now = datetime.now(timezone.utc)
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    day_end = day_start + timedelta(days=1)
    now = datetime.now(timezone.utc)
    query = {
        'resource_id': resource_id,
        'status': {'$in': list(ACTIVE_STATUSES)},
        'held_until': {'$gt': now},
        'start_at': {'$lt': day_end},
        'end_at': {'$gt': day_start},
    }

    busy = []
    cursor = bookings_col.find(query).sort('start_at', ASCENDING)
    async for doc in cursor:
        busy.append(schemas.BusyInterval(
            start_at=as_utc(doc['start_at']),
            end_at=as_utc(doc['end_at']),
            status=doc.get('status') or 'created',
        ))

    return schemas.AvailabilityOut(
        resource_id=resource_id,
        date=day_start.strftime('%Y-%m-%d'),
        busy=busy,
    )


@router.get('/{resource_id}', response_model=schemas.ResourceOut)
async def get_resource(resource_id: str):
    resource = await resources_col.find_one({'_id': resource_id})
    if resource is None:
        raise HTTPException(status_code=404, detail='Resource not found')
    return _to_out(resource)


@router.get('', response_model=List[schemas.ResourceOut])
async def list_resources(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    resource_type: Optional[str] = None,
    search: Optional[str] = Query(default=None, max_length=100),
):
    query = {}
    if resource_type:
        query['resource_type'] = resource_type
    if search:
        # Экранируем пользовательский ввод: иначе символы вроде '(' или '['
        # ломают регулярное выражение и роняют запрос.
        query['name'] = {'$regex': re.escape(search), '$options': 'i'}

    cursor = resources_col.find(query).sort('name', ASCENDING).skip(skip).limit(limit)
    out = []
    async for resource in cursor:
        out.append(_to_out(resource))
    return out


@router.post('', response_model=schemas.ResourceOut)
async def create_resource(
    payload: schemas.ResourceCreate,
    user: dict = Depends(get_current_user),
):
    if user.get('role') not in ('admin', 'employee'):
        raise HTTPException(status_code=403, detail='Admin or employee only')

    now = datetime.now(timezone.utc)
    resource_id = str(uuid4())
    doc = {
        '_id': resource_id,
        'name': payload.name,
        'resource_type': payload.resource_type,
        'capacity': payload.capacity,
        'image': payload.image,
        'description': payload.description,
        'created_at': now,
        'updated_at': now,
    }
    await resources_col.insert_one(doc)
    return _to_out(doc)


@router.delete('/{resource_id}')
async def delete_resource(
    resource_id: str,
    user: dict = Depends(get_current_user),
):
    if user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail='Admin only')
    result = await resources_col.delete_one({'_id': resource_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail='Resource not found')
    return {'ok': True}

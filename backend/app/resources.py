from datetime import datetime, timezone
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
    search: Optional[str] = None,
):
    query = {}
    if resource_type:
        query['resource_type'] = resource_type
    if search:
        query['name'] = {'$regex': search, '$options': 'i'}

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

from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from app import schemas
from app.auth import get_current_user
from app.database import db

router = APIRouter(prefix='/api/resources', tags=['Resources'])

resources_col = db.resources


@router.get('/{resource_id}', response_model=schemas.ResourceOut)
async def get_resource(resource_id: str):
    resource = await resources_col.find_one({'_id': resource_id})
    if resource is None:
        raise HTTPException(status_code=404, detail='Resource not found')
    return schemas.ResourceOut(
        id=str(resource['_id']),
        name=resource['name'],
        resource_type=resource.get('resource_type', 'private_room'),
        capacity=resource.get('capacity', 1),
        image=resource.get('image'),
        description=resource.get('description'),
        created_at=resource.get('created_at'),
        updated_at=resource.get('updated_at'),
    )


@router.post('', response_model=schemas.ResourceOut)
async def create_resource(
    payload: schemas.ResourceCreate,
    user: dict = Depends(get_current_user),
):
    user_role = user.get('role')
    if user_role not in ('admin', 'employee'):
        raise HTTPException(status_code=403, detail='Admin only')

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
    return schemas.ResourceOut(
        id=resource_id,
        name=doc['name'],
        resource_type=doc['resource_type'],
        capacity=doc['capacity'],
        image=doc.get('image'),
        description=doc.get('description'),
        created_at=doc.get('created_at'),
        updated_at=doc.get('updated_at'),
    )

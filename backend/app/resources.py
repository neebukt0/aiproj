from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from app import schemas
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

from datetime import datetime, timezone
from typing import List
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app import schemas
from app.auth import get_current_user, hash_password
from app.database import db
from app.utils import as_utc

router = APIRouter(prefix='/api/admin', tags=['Admin'])

users_col = db.users


def _to_out(user) -> schemas.UserOut:
    return schemas.UserOut(
        id=str(user['_id']),
        email=user['email'],
        role=user.get('role', 'client'),
        is_active=user.get('is_active', True),
        created_at=as_utc(user.get('created_at')),
        updated_at=as_utc(user.get('updated_at')),
    )


@router.get('/users', response_model=List[schemas.UserOut])
async def list_users(user: dict = Depends(get_current_user)):
    if user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail='Admin only')
    out = []
    cursor = users_col.find({}).sort('created_at', -1)
    async for item in cursor:
        out.append(_to_out(item))
    return out


@router.post('/users', response_model=schemas.UserOut)
async def create_user(
    payload: schemas.UserAdminCreate,
    user: dict = Depends(get_current_user),
):
    if user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail='Admin only')

    email = payload.email.lower()
    existing = await users_col.find_one({'email': email})
    if existing is not None:
        raise HTTPException(status_code=409, detail='Email already registered')

    now = datetime.now(timezone.utc)
    doc = {
        '_id': str(uuid4()),
        'email': email,
        'password_hash': hash_password(payload.password),
        'role': payload.role,
        'is_active': True,
        'created_at': now,
        'updated_at': now,
    }
    await users_col.insert_one(doc)
    return _to_out(doc)


@router.patch('/users/{user_id}')
async def update_user(
    user_id: str,
    payload: schemas.UserUpdate,
    user: dict = Depends(get_current_user),
):
    if user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail='Admin only')
    target = await users_col.find_one({'_id': user_id})
    if target is None:
        raise HTTPException(status_code=404, detail='User not found')

    if user_id == str(user['_id']):
        if payload.is_active is False:
            raise HTTPException(status_code=400, detail='Cannot deactivate yourself')
        if payload.role is not None and payload.role != 'admin':
            raise HTTPException(status_code=400, detail='Cannot demote yourself')

    update = {'updated_at': datetime.now(timezone.utc)}
    if payload.role is not None:
        update['role'] = payload.role
    if payload.is_active is not None:
        update['is_active'] = payload.is_active
    if payload.password:
        update['password_hash'] = hash_password(payload.password)

    await users_col.update_one({'_id': user_id}, {'$set': update})
    updated = await users_col.find_one({'_id': user_id})
    return _to_out(updated)


@router.delete('/users/{user_id}')
async def delete_user(
    user_id: str,
    user: dict = Depends(get_current_user),
):
    if user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail='Admin only')
    if str(user['_id']) == user_id:
        raise HTTPException(status_code=400, detail='Cannot delete yourself')
    result = await users_col.delete_one({'_id': user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail='User not found')
    await db.refresh_tokens.delete_many({'user_id': user_id})
    return {'ok': True}

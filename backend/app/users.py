from datetime import datetime, timezone
from typing import List
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from passlib.context import CryptContext

from app import schemas
from app.auth import get_current_user, hash_password
from app.database import db

router = APIRouter(prefix='/api/admin', tags=['Admin'])

users_col = db.users
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


@router.get('/users', response_model=List[schemas.UserOut])
async def list_users(user: dict = Depends(get_current_user)):
    if user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail='Admin only')
    out = []
    cursor = users_col.find({}).sort('created_at', -1)
    async for u in cursor:
        out.append(schemas.UserOut(
            id=str(u['_id']),
            email=u['email'],
            role=u.get('role', 'client'),
            is_active=u.get('is_active', True),
            created_at=u.get('created_at'),
            updated_at=u.get('updated_at'),
        ))
    return out


@router.patch('/users/{user_id}')
async def update_user(
    user_id: str,
    payload: dict,
    user: dict = Depends(get_current_user),
):
    if user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail='Admin only')
    target = await users_col.find_one({'_id': user_id})
    if target is None:
        raise HTTPException(status_code=404, detail='User not found')

    update = {'updated_at': datetime.now(timezone.utc)}
    if 'role' in payload:
        update['role'] = payload['role']
    if 'is_active' in payload:
        update['is_active'] = bool(payload['is_active'])
    if 'password' in payload and payload['password']:
        update['password_hash'] = hash_password(payload['password'])

    await users_col.update_one({'_id': user_id}, {'$set': update})
    return {'ok': True}


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
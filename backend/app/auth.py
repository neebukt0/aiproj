from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext

from app import schemas
from app.config import settings
from app.database import db

router = APIRouter(prefix='/api/auth', tags=['Auth'])

users_col = db.users
refresh_col = db.refresh_tokens

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        'sub': user_id,
        'role': role,
        'iat': int(now.timestamp()),
        'exp': int((now + timedelta(minutes=settings.JWT_ACCESS_LIFETIME_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
) -> dict:
    if credentials is None or credentials.scheme.lower() != 'bearer':
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Not authenticated')
    payload = decode_token(credentials.credentials)
    user = await users_col.find_one({'_id': payload.get('sub')})
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='User not found')
    return user


@router.post('/register', response_model=schemas.TokenPair)
async def register(payload: schemas.UserCreate):
    existing = await users_col.find_one({'email': payload.email})
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Email already registered')

    user_id = schemas.new_id()
    now = datetime.now(timezone.utc)
    await users_col.insert_one({
        '_id': user_id,
        'email': payload.email,
        'password_hash': hash_password(payload.password),
        'role': payload.role or 'client',
        'is_active': True,
        'created_at': now,
        'updated_at': now,
    })

    access = create_access_token(user_id, payload.role or 'client')
    refresh = str(uuid4())
    await refresh_col.insert_one({
        '_id': refresh,
        'jti': refresh,
        'user_id': user_id,
        'revoked': False,
        'created_at': now,
        'expires_at': now + timedelta(days=settings.JWT_REFRESH_LIFETIME_DAYS),
    })
    return schemas.TokenPair(access=access, refresh=refresh)


@router.post('/login', response_model=schemas.TokenPair)
async def login(payload: schemas.LoginRequest):
    user = await users_col.find_one({'email': payload.email})
    if user is None or not verify_password(payload.password, user['password_hash']):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid credentials')
    access = create_access_token(str(user['_id']), user['role'])
    refresh = str(uuid4())
    await refresh_col.insert_one({
        '_id': refresh,
        'jti': refresh,
        'user_id': str(user['_id']),
        'revoked': False,
        'created_at': datetime.now(timezone.utc),
        'expires_at': datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_LIFETIME_DAYS),
    })
    return schemas.TokenPair(access=access, refresh=refresh)


@router.post('/refresh')
async def refresh(payload: schemas.TokenRefreshRequest):
    token_doc = await refresh_col.find_one({'jti': payload.refresh})
    if token_doc is None or token_doc.get('revoked'):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid refresh token')
    user = await users_col.find_one({'_id': token_doc['user_id']})
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='User not found')
    access = create_access_token(str(user['_id']), user['role'])
    return {'access': access}


@router.post('/logout')
async def logout(payload: schemas.TokenRefreshRequest, user: dict = Depends(get_current_user)):
    await refresh_col.update_one(
        {'jti': payload.refresh},
        {'$set': {'revoked': True}},
    )
    return {'detail': 'Successfully logged out'}


@router.get('/me')
async def me(user: dict = Depends(get_current_user)):
    return {
        'id': str(user['_id']),
        'email': user['email'],
        'role': user['role'],
        'is_active': user.get('is_active', True),
    }

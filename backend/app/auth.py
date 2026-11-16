from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app import schemas
from app.config import settings
from app.database import db
from app.utils import as_utc

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
        'jti': str(uuid4()),
        'iat': int(now.timestamp()),
        'exp': int((now + timedelta(minutes=settings.JWT_ACCESS_LIFETIME_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])


async def _create_token_pair(user_id: str, role: str) -> schemas.TokenPair:
    now = datetime.now(timezone.utc)
    access = create_access_token(user_id, role)
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


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
) -> dict:
    if credentials is None or credentials.scheme.lower() != 'bearer':
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Not authenticated')

    try:
        payload = decode_token(credentials.credentials)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid or expired token',
        )

    user_id = payload.get('sub')
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid token payload')

    user = await users_col.find_one({'_id': user_id})
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='User not found')
    if not user.get('is_active', True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='User is inactive')
    return user


@router.post('/register', response_model=schemas.TokenPair)
async def register(payload: schemas.UserCreate):
    email = payload.email.lower()
    existing = await users_col.find_one({'email': email})
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Email already registered')

    user_id = schemas.new_id()
    now = datetime.now(timezone.utc)
    # Публичная регистрация всегда создаёт client: роль назначает только admin.
    await users_col.insert_one({
        '_id': user_id,
        'email': email,
        'password_hash': hash_password(payload.password),
        'role': 'client',
        'is_active': True,
        'created_at': now,
        'updated_at': now,
    })
    return await _create_token_pair(user_id, 'client')


@router.post('/login', response_model=schemas.TokenPair)
async def login(payload: schemas.LoginRequest):
    user = await users_col.find_one({'email': payload.email.lower()})
    if user is None or not verify_password(payload.password, user['password_hash']):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid credentials')
    if not user.get('is_active', True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='User is inactive')
    return await _create_token_pair(str(user['_id']), user['role'])


@router.post('/refresh')
async def refresh(payload: schemas.TokenRefreshRequest):
    now = datetime.now(timezone.utc)
    token_doc = await refresh_col.find_one({'jti': payload.refresh})
    if token_doc is None or token_doc.get('revoked'):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid refresh token')

    expires_at = as_utc(token_doc.get('expires_at'))
    if expires_at is None or expires_at <= now:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Refresh token expired')

    user = await users_col.find_one({'_id': token_doc['user_id']})
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='User not found')
    if not user.get('is_active', True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='User is inactive')

    access = create_access_token(str(user['_id']), user['role'])
    return {'access': access}


@router.post('/logout')
async def logout(payload: schemas.TokenRefreshRequest, user: dict = Depends(get_current_user)):
    token_doc = await refresh_col.find_one({'jti': payload.refresh})
    if token_doc is not None:
        if str(token_doc.get('user_id')) != str(user['_id']):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Not your token')
        await refresh_col.update_one(
            {'_id': token_doc['_id']},
            {'$set': {'revoked': True, 'revoked_at': datetime.now(timezone.utc)}},
        )
    return {'detail': 'Successfully logged out'}


@router.get('/me')
async def me(user: dict = Depends(get_current_user)):
    return {
        'id': str(user['_id']),
        'email': user['email'],
        'role': user['role'],
        'is_active': user.get('is_active', True),
        'created_at': as_utc(user.get('created_at')),
        'updated_at': as_utc(user.get('updated_at')),
    }

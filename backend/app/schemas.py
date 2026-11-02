from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, EmailStr, Field


def new_id() -> str:
    return str(uuid4())


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: str = 'client'


class UserOut(BaseModel):
    id: str
    email: str
    role: str
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class TokenPair(BaseModel):
    access: str
    refresh: str


class TokenRefreshRequest(BaseModel):
    refresh: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ResourceOut(BaseModel):
    id: str
    name: str
    resource_type: str = 'private_room'
    capacity: int = 1
    image: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class BookingIn(BaseModel):
    resource_id: str
    start_at: datetime
    end_at: datetime


class BookingOut(BaseModel):
    id: str
    user_id: str
    resource_id: str
    status: str = 'created'
    start_at: datetime
    end_at: datetime
    held_until: datetime
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

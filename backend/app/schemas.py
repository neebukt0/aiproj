from datetime import datetime, timezone
from typing import List, Optional
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


class ResourceCreate(BaseModel):
    name: str
    resource_type: str = 'private_room'
    capacity: int = 1
    image: Optional[str] = None
    description: Optional[str] = None


class BookingIn(BaseModel):
    resource_id: str
    start_at: datetime
    end_at: datetime


class BookingStatusRequest(BaseModel):
    status: str


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


class BookingFullOut(BookingOut):
    confirmed_at: Optional[datetime] = None
    confirmed_by: Optional[str] = None
    cancelled_at: Optional[datetime] = None
    cancel_reason: Optional[str] = None


class StatusLogOut(BaseModel):
    id: str
    booking_id: str
    from_status: Optional[str] = None
    to_status: str
    changed_by: Optional[str] = None
    changed_at: datetime
    note: Optional[str] = None


class ReportRequest(BaseModel):
    start_at: datetime
    end_at: datetime
    resource_id: Optional[str] = None


class ReportRow(BaseModel):
    resource_id: str
    resource_name: str
    total_bookings: int
    confirmed_bookings: int
    completed_bookings: int
    cancelled_bookings: int
    total_minutes: int


class ReportOut(BaseModel):
    rows: List[ReportRow]
    period_start: datetime
    period_end: datetime

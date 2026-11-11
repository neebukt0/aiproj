from datetime import datetime, timezone
from typing import List, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, EmailStr, Field

Role = Literal['client', 'employee', 'admin']
BookingStatus = Literal['created', 'confirmed', 'completed', 'cancelled']


def new_id() -> str:
    return str(uuid4())


class UserCreate(BaseModel):
    """Публичная регистрация: роль всегда client (поле role игнорируется)."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class UserAdminCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    role: Role = 'client'


class UserUpdate(BaseModel):
    role: Optional[Role] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(default=None, min_length=8, max_length=72)


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
    name: str = Field(min_length=1, max_length=200)
    resource_type: str = 'private_room'
    capacity: int = Field(default=1, ge=1)
    image: Optional[str] = None
    description: Optional[str] = None


class BookingIn(BaseModel):
    resource_id: str
    start_at: datetime
    end_at: datetime
    participant_ids: List[str] = Field(default_factory=list)


class BookingStatusRequest(BaseModel):
    status: str
    note: Optional[str] = None


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


class ParticipantOut(BaseModel):
    id: str
    booking_id: str
    user_id: str
    created_at: datetime


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

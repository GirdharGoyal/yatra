from typing import Any, List, Optional
from pydantic import BaseModel, EmailStr, Field


# Auth
class UserCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    name: str
    email: str

    model_config = {"from_attributes": True}


# Inventory
class FlightOut(BaseModel):
    id: int
    airline: str
    flight_number: str
    origin: str
    destination: str
    departure_time: str
    duration: str
    price: float
    seats_available: int

    model_config = {"from_attributes": True}


class HotelOut(BaseModel):
    id: int
    name: str
    city: str
    room_type: str
    rating: float
    price: float
    rooms_available: int

    model_config = {"from_attributes": True}


class ActivityOut(BaseModel):
    id: int
    title: str
    city: str
    category: str
    duration_hours: float
    price: float
    slots_available: int

    model_config = {"from_attributes": True}


# Bookings
class BookingCreate(BaseModel):
    item_type: str = Field(..., pattern="^(flight|hotel|activity)$")
    item_id: int = Field(..., gt=0)
    travel_date: str = Field(..., pattern="^\d{4}-\d{2}-\d{2}$")
    travellers: int = Field(default=1, ge=1, le=10)


class BookingUpdate(BaseModel):
    travel_date: Optional[str] = Field(default=None, pattern="^\d{4}-\d{2}-\d{2}$")
    travellers: Optional[int] = Field(default=None, ge=1, le=10)


class BookingOut(BaseModel):
    id: int
    user_id: int
    item_type: str
    item_id: int
    item_title: str
    travel_date: str
    travellers: int
    amount: float
    refund_amount: float
    status: str

    model_config = {"from_attributes": True}


# Payments
class PaymentCreate(BaseModel):
    booking_id: int
    card_number: str = Field(..., min_length=12, max_length=19)


class PaymentOut(BaseModel):
    id: int
    booking_id: int
    amount: float
    card_last4: str
    status: str

    model_config = {"from_attributes": True}


# Chat
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    resume: Optional[bool] = None


class ChatResponse(BaseModel):
    reply: str
    requires_confirmation: bool = False
    pending_action: Optional[dict[str, Any]] = None
    tool_calls: List[str] = []

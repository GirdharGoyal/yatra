from typing import List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.db import get_db
from backend.models import Booking, User
from backend.schemas import BookingCreate, BookingOut, BookingUpdate
from backend.services.booking_rules import (
    adjust_inventory,
    cancel_user_booking,
    create_user_booking,
    get_inventory_item,
)
from backend.services.pricing import calculate_total_amount

router = APIRouter(prefix="/bookings", tags=["Bookings"])


def _get_owned_booking(db: Session, booking_id: int, user_id: int) -> Booking:
    booking = db.query(Booking).filter(Booking.id == booking_id, Booking.user_id == user_id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    return booking


@router.post("", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
def create_booking(
    payload: BookingCreate,
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return create_user_booking(
        db=db,
        user_id=current_user.id,
        item_type=payload.item_type,
        item_id=payload.item_id,
        travel_date=payload.travel_date,
        travellers=payload.travellers,
        idempotency_key=idempotency_key,
    )


@router.get("", response_model=List[BookingOut])
def list_my_bookings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(Booking)
        .filter(Booking.user_id == current_user.id)
        .order_by(Booking.id.desc())
        .all()
    )


@router.get("/{booking_id}", response_model=BookingOut)
def get_booking(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _get_owned_booking(db, booking_id, current_user.id)


@router.patch("/{booking_id}", response_model=BookingOut)
def update_booking(
    booking_id: int,
    payload: BookingUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    booking = _get_owned_booking(db, booking_id, current_user.id)
    if booking.status == "cancelled":
        raise HTTPException(status_code=400, detail="Cannot modify a cancelled booking")

    if payload.travel_date:
        booking.travel_date = payload.travel_date

    if payload.travellers and payload.travellers != booking.travellers:
        diff = payload.travellers - booking.travellers
        item, _, _ = get_inventory_item(db, booking.item_type, booking.item_id)
        adjust_inventory(item, booking.item_type, -diff)
        booking.travellers = payload.travellers
        booking.amount = calculate_total_amount(item.price, booking.travellers)

    db.commit()
    db.refresh(booking)
    return booking


@router.post("/{booking_id}/cancel", response_model=BookingOut)
def cancel_booking(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    booking = _get_owned_booking(db, booking_id, current_user.id)
    return cancel_user_booking(db, booking)


@router.get("/{booking_id}/receipt", response_class=HTMLResponse)
def booking_receipt(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    booking = _get_owned_booking(db, booking_id, current_user.id)
    html = f"""<!DOCTYPE html>
<html>
<head><title>Yatra Receipt #{booking.id}</title>
<style>
  body {{ font-family: Arial, sans-serif; padding: 40px; background: #f8fafc; }}
  .box {{ max-width: 520px; margin: auto; background: #fff; padding: 24px; border-radius: 12px; border: 1px solid #cbd5e1; }}
  h1 {{ color: #0066cc; }}
  .row {{ display: flex; justify-content: space-between; margin: 10px 0; }}
</style>
</head>
<body>
  <div class="box">
    <h1>Yatra E-Ticket & Receipt</h1>
    <hr/>
    <div class="row"><strong>Booking ID:</strong><span>#{booking.id}</span></div>
    <div class="row"><strong>Passenger:</strong><span>{current_user.name} ({current_user.email})</span></div>
    <div class="row"><strong>Item:</strong><span>{booking.item_title or booking.item_type}</span></div>
    <div class="row"><strong>Travel Date:</strong><span>{booking.travel_date}</span></div>
    <div class="row"><strong>Travellers:</strong><span>{booking.travellers}</span></div>
    <div class="row"><strong>Status:</strong><span>{booking.status.upper()}</span></div>
    <hr/>
    <div class="row"><strong>Total Paid:</strong><span>₹{booking.amount}</span></div>
  </div>
</body>
</html>"""
    return HTMLResponse(content=html)

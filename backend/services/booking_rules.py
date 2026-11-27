from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.models import Activity, Booking, Flight, Hotel
from backend.services.pricing import calculate_refund, calculate_total_amount


def get_inventory_item(db: Session, item_type: str, item_id: int):
    if item_type == "flight":
        item = db.query(Flight).filter(Flight.id == item_id).first()
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flight not found")
        return item, item.seats_available, f"{item.airline} ({item.origin} -> {item.destination})"

    if item_type == "hotel":
        item = db.query(Hotel).filter(Hotel.id == item_id).first()
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hotel not found")
        return item, item.rooms_available, f"{item.name} ({item.city})"

    if item_type == "activity":
        item = db.query(Activity).filter(Activity.id == item_id).first()
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activity not found")
        return item, item.slots_available, f"{item.title} ({item.city})"

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid item_type")


def adjust_inventory(item, item_type: str, delta: int):
    if item_type == "flight":
        if item.seats_available + delta < 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not enough seats available")
        item.seats_available += delta
    elif item_type == "hotel":
        if item.rooms_available + delta < 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not enough rooms available")
        item.rooms_available += delta
    elif item_type == "activity":
        if item.slots_available + delta < 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not enough activity slots available")
        item.slots_available += delta


def create_user_booking(
    db: Session,
    user_id: int,
    item_type: str,
    item_id: int,
    travel_date: str,
    travellers: int,
    idempotency_key: str | None = None,
) -> Booking:
    if idempotency_key:
        existing = (
            db.query(Booking)
            .filter(Booking.user_id == user_id, Booking.idempotency_key == idempotency_key)
            .first()
        )
        if existing:
            return existing

    item, available, title = get_inventory_item(db, item_type, item_id)
    if available < travellers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only {available} spots left for this {item_type}",
        )

    adjust_inventory(item, item_type, -travellers)
    total_amount = calculate_total_amount(item.price, travellers)

    booking = Booking(
        user_id=user_id,
        item_type=item_type,
        item_id=item_id,
        item_title=title,
        travel_date=travel_date,
        travellers=travellers,
        amount=total_amount,
        status="pending_payment",
        idempotency_key=idempotency_key,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


def cancel_user_booking(db: Session, booking: Booking) -> Booking:
    if booking.status == "cancelled":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Booking is already cancelled")

    item, _, _ = get_inventory_item(db, booking.item_type, booking.item_id)
    adjust_inventory(item, booking.item_type, booking.travellers)

    try:
        travel_dt = datetime.strptime(booking.travel_date, "%Y-%m-%d")
        hours_diff = (travel_dt - datetime.utcnow()).total_seconds() / 3600.0
    except ValueError:
        hours_diff = 48.0

    if booking.status == "confirmed":
        booking.refund_amount = calculate_refund(booking.amount, hours_diff)
    else:
        booking.refund_amount = 0.0

    booking.status = "cancelled"
    db.commit()
    db.refresh(booking)
    return booking

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.db import get_db
from backend.models import Booking, Payment, User
from backend.schemas import PaymentCreate, PaymentOut

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
def process_payment(
    payload: PaymentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    booking = (
        db.query(Booking)
        .filter(Booking.id == payload.booking_id, Booking.user_id == current_user.id)
        .first()
    )
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

    if booking.status == "confirmed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Booking is already paid")
    if booking.status == "cancelled":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot pay for cancelled booking")

    clean_card = payload.card_number.replace(" ", "").replace("-", "")
    last4 = clean_card[-4:]

    # Test card 4000000000000002 simulates a declined payment
    if clean_card == "4000000000000002":
        booking.status = "payment_failed"
        payment = Payment(
            booking_id=booking.id,
            user_id=current_user.id,
            amount=booking.amount,
            card_last4=last4,
            status="failed",
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Card declined by test gateway")

    booking.status = "confirmed"
    payment = Payment(
        booking_id=booking.id,
        user_id=current_user.id,
        amount=booking.amount,
        card_last4=last4,
        status="succeeded",
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment

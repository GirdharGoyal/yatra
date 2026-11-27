from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.models import Flight
from backend.schemas import FlightOut

router = APIRouter(prefix="/flights", tags=["Flights"])


@router.get("", response_model=List[FlightOut])
def list_flights(
    origin: Optional[str] = Query(default=None),
    destination: Optional[str] = Query(default=None),
    max_price: Optional[float] = Query(default=None, gt=0),
    sort_by: str = Query(default="price"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(Flight)
    if origin:
        query = query.filter(Flight.origin.ilike(f"%{origin.strip()}%"))
    if destination:
        query = query.filter(Flight.destination.ilike(f"%{destination.strip()}%"))
    if max_price is not None:
        query = query.filter(Flight.price <= max_price)

    if sort_by == "price_desc":
        query = query.order_by(Flight.price.desc())
    else:
        query = query.order_by(Flight.price.asc())

    return query.offset(offset).limit(limit).all()


@router.get("/{flight_id}", response_model=FlightOut)
def get_flight(flight_id: int, db: Session = Depends(get_db)):
    flight = db.query(Flight).filter(Flight.id == flight_id).first()
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")
    return flight

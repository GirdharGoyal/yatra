from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.models import Hotel
from backend.schemas import HotelOut

router = APIRouter(prefix="/hotels", tags=["Hotels"])


@router.get("", response_model=List[HotelOut])
def list_hotels(
    city: Optional[str] = Query(default=None),
    max_price: Optional[float] = Query(default=None, gt=0),
    min_rating: Optional[float] = Query(default=None, ge=0, le=5),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(Hotel)
    if city:
        query = query.filter(Hotel.city.ilike(f"%{city.strip()}%"))
    if max_price is not None:
        query = query.filter(Hotel.price <= max_price)
    if min_rating is not None:
        query = query.filter(Hotel.rating >= min_rating)

    return query.order_by(Hotel.price.asc()).offset(offset).limit(limit).all()


@router.get("/{hotel_id}", response_model=HotelOut)
def get_hotel(hotel_id: int, db: Session = Depends(get_db)):
    hotel = db.query(Hotel).filter(Hotel.id == hotel_id).first()
    if not hotel:
        raise HTTPException(status_code=404, detail="Hotel not found")
    return hotel

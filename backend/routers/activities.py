from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.models import Activity
from backend.schemas import ActivityOut

router = APIRouter(prefix="/activities", tags=["Activities"])


@router.get("", response_model=List[ActivityOut])
def list_activities(
    city: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    max_price: Optional[float] = Query(default=None, gt=0),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(Activity)
    if city:
        query = query.filter(Activity.city.ilike(f"%{city.strip()}%"))
    if category:
        query = query.filter(Activity.category.ilike(f"%{category.strip()}%"))
    if max_price is not None:
        query = query.filter(Activity.price <= max_price)

    return query.order_by(Activity.price.asc()).offset(offset).limit(limit).all()


@router.get("/{activity_id}", response_model=ActivityOut)
def get_activity(activity_id: int, db: Session = Depends(get_db)):
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    return activity

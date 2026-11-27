import json
from pathlib import Path
from sqlalchemy.orm import Session

from backend.models import Activity, Flight, Hotel

SEED_DIR = Path(__file__).resolve().parent / "seed_data"


def seed_database(db: Session):
    if db.query(Flight).count() == 0:
        flights = json.loads((SEED_DIR / "flights.json").read_text(encoding="utf-8"))
        db.add_all([Flight(**f) for f in flights])

    if db.query(Hotel).count() == 0:
        hotels = json.loads((SEED_DIR / "hotels.json").read_text(encoding="utf-8"))
        db.add_all([Hotel(**h) for h in hotels])

    if db.query(Activity).count() == 0:
        activities = json.loads((SEED_DIR / "activities.json").read_text(encoding="utf-8"))
        db.add_all([Activity(**a) for a in activities])

    db.commit()

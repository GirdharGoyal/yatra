import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.db import Base, SessionLocal, engine
from backend.routers import activities, auth, bookings, chat, flights, hotels, payments
from backend.seed import seed_database

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("yatra")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database(db)
        logger.info("Database initialized and seeded.")
    finally:
        db.close()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(flights.router)
app.include_router(hotels.router)
app.include_router(activities.router)
app.include_router(bookings.router)
app.include_router(payments.router)
app.include_router(chat.router)


@app.get("/health")
def health_check():
    return {"status": "ok", "app": settings.app_name}

from datetime import datetime
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    email = Column(String(200), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    bookings = relationship("Booking", back_populates="user")
    preferences = relationship("UserPreference", back_populates="user")


class Flight(Base):
    __tablename__ = "flights"

    id = Column(Integer, primary_key=True, index=True)
    airline = Column(String(100), nullable=False)
    flight_number = Column(String(30), nullable=False)
    origin = Column(String(50), index=True, nullable=False)
    destination = Column(String(50), index=True, nullable=False)
    departure_time = Column(String(50), nullable=False)
    duration = Column(String(30), nullable=False)
    price = Column(Float, nullable=False)
    seats_available = Column(Integer, default=20)


class Hotel(Base):
    __tablename__ = "hotels"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    city = Column(String(80), index=True, nullable=False)
    room_type = Column(String(80), default="Deluxe Room")
    rating = Column(Float, default=4.2)
    price = Column(Float, nullable=False)
    rooms_available = Column(Integer, default=10)


class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(150), nullable=False)
    city = Column(String(80), index=True, nullable=False)
    category = Column(String(60), default="Sightseeing")
    duration_hours = Column(Float, default=3.0)
    price = Column(Float, nullable=False)
    slots_available = Column(Integer, default=15)


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    item_type = Column(String(30), nullable=False)  # flight, hotel, activity
    item_id = Column(Integer, nullable=False)
    item_title = Column(String(200), default="")
    travel_date = Column(String(20), nullable=False)
    travellers = Column(Integer, default=1)
    amount = Column(Float, nullable=False)
    refund_amount = Column(Float, default=0.0)
    status = Column(String(30), default="pending_payment")  # pending_payment, confirmed, payment_failed, cancelled
    idempotency_key = Column(String(100), unique=True, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="bookings")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Float, nullable=False)
    card_last4 = Column(String(4), nullable=False)
    status = Column(String(30), nullable=False)  # succeeded, failed, refunded
    created_at = Column(DateTime, default=datetime.utcnow)


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    key = Column(String(80), nullable=False)
    value = Column(Text, nullable=False)

    user = relationship("User", back_populates="preferences")

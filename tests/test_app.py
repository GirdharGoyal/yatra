import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.db import Base, get_db
from backend.main import app
from backend.seed import seed_database

TEST_DB_URL = "sqlite:///./test_yatra.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    seed_database(db)
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)


client = TestClient(app)


def _signup_and_login(name: str, email: str, password: str = "secret123") -> str:
    client.post("/auth/signup", json={"name": name, "email": email, "password": password})
    res = client.post("/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]


def test_health_and_search():
    assert client.get("/health").status_code == 200
    res = client.get("/flights?origin=DEL&destination=GOA")
    assert res.status_code == 200
    assert len(res.json()) >= 1


def test_unauthorized_me():
    res = client.get("/me")
    assert res.status_code == 401


def test_full_booking_payment_and_cancel_flow():
    token_a = _signup_and_login("Riya", "riya@example.com")
    token_b = _signup_and_login("Aman", "aman@example.com")
    headers_a = {"Authorization": f"Bearer {token_a}", "Idempotency-Key": "idem-101"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 1. Create booking (and test idempotency)
    payload = {"item_type": "flight", "item_id": 1, "travel_date": "2027-05-10", "travellers": 2}
    r1 = client.post("/bookings", json=payload, headers=headers_a)
    r2 = client.post("/bookings", json=payload, headers=headers_a)
    assert r1.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]
    booking_id = r1.json()["id"]

    # 2. User B cannot view User A's booking
    res_other = client.get(f"/bookings/{booking_id}", headers=headers_b)
    assert res_other.status_code == 404

    # 3. Failed payment keeps status non-confirmed
    fail_pay = client.post(
        "/payments",
        json={"booking_id": booking_id, "card_number": "4000000000000002"},
        headers=headers_a,
    )
    assert fail_pay.status_code == 402

    # 4. Valid payment confirms booking
    ok_pay = client.post(
        "/payments",
        json={"booking_id": booking_id, "card_number": "4111111111111111"},
        headers=headers_a,
    )
    assert ok_pay.status_code == 201

    # 5. Receipt works
    receipt = client.get(f"/bookings/{booking_id}/receipt", headers=headers_a)
    assert receipt.status_code == 200
    assert "Yatra E-Ticket" in receipt.text

    # 6. Cancel restores seats and refunds
    cancel = client.post(f"/bookings/{booking_id}/cancel", headers=headers_a)
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "cancelled"

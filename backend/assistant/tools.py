from typing import Any, Dict, Optional
import httpx
from langchain_core.tools import tool
from sqlalchemy.orm import Session

from backend.assistant.rag import policy_retriever
from backend.config import settings
from backend.models import UserPreference

# In-memory pending confirmations per user_id for Human-in-the-Loop
PENDING_ACTIONS: Dict[int, Dict[str, Any]] = {}


def build_user_tools(user_id: int, token: str, db: Session):
    headers = {"Authorization": f"Bearer {token}"}
    base_url = settings.api_base_url.rstrip("/")

    @tool
    def list_my_bookings() -> str:
        """Fetch all bookings belonging to the currently logged-in user."""
        with httpx.Client(base_url=base_url, headers=headers, timeout=10.0) as client:
            res = client.get("/bookings")
            if res.status_code != 200:
                return f"Error fetching bookings: {res.text}"
            data = res.json()
            if not data:
                return "You have no bookings yet."
            lines = [
                f"Booking #{b['id']}: {b['item_title']} ({b['item_type']}) on {b['travel_date']} | {b['travellers']} pax | ₹{b['amount']} | Status: {b['status']}"
                for b in data
            ]
            return "\n".join(lines)

    @tool
    def search_flights(origin: Optional[str] = None, destination: Optional[str] = None, max_price: Optional[float] = None) -> str:
        """Search available flights by origin city/code (e.g. DEL), destination (e.g. GOA), and optional max_price."""
        params = {}
        if origin:
            params["origin"] = origin
        if destination:
            params["destination"] = destination
        if max_price:
            params["max_price"] = max_price
        with httpx.Client(base_url=base_url, headers=headers, timeout=10.0) as client:
            res = client.get("/flights", params=params)
            items = res.json()
            if not items:
                return "No matching flights found."
            return "\n".join(
                f"Flight ID {f['id']}: {f['airline']} {f['flight_number']} ({f['origin']} -> {f['destination']}) at {f['departure_time']} | ₹{f['price']} | Seats: {f['seats_available']}"
                for f in items[:6]
            )

    @tool
    def search_hotels(city: Optional[str] = None, max_price: Optional[float] = None) -> str:
        """Search available hotels in a city with an optional max_price per night."""
        params = {}
        if city:
            params["city"] = city
        if max_price:
            params["max_price"] = max_price
        with httpx.Client(base_url=base_url, headers=headers, timeout=10.0) as client:
            res = client.get("/hotels", params=params)
            items = res.json()
            if not items:
                return "No matching hotels found."
            return "\n".join(
                f"Hotel ID {h['id']}: {h['name']} ({h['city']}) - {h['room_type']} | Rating {h['rating']}★ | ₹{h['price']}/night | Rooms: {h['rooms_available']}"
                for h in items[:6]
            )

    @tool
    def search_activities(city: Optional[str] = None, max_price: Optional[float] = None) -> str:
        """Search sightseeing tours and activities in a city."""
        params = {}
        if city:
            params["city"] = city
        if max_price:
            params["max_price"] = max_price
        with httpx.Client(base_url=base_url, headers=headers, timeout=10.0) as client:
            res = client.get("/activities", params=params)
            items = res.json()
            if not items:
                return "No matching activities found."
            return "\n".join(
                f"Activity ID {a['id']}: {a['title']} ({a['city']}, {a['category']}) | {a['duration_hours']}h | ₹{a['price']} | Slots: {a['slots_available']}"
                for a in items[:6]
            )

    @tool
    def propose_booking(item_type: str, item_id: int, travel_date: str, travellers: int = 1) -> str:
        """Stage a booking (flight, hotel, or activity) and ask the user for UI confirmation before finalizing."""
        endpoint_map = {"flight": "flights", "hotel": "hotels", "activity": "activities"}
        if item_type not in endpoint_map:
            return "Invalid item_type. Must be flight, hotel, or activity."
        with httpx.Client(base_url=base_url, headers=headers, timeout=10.0) as client:
            res = client.get(f"/{endpoint_map[item_type]}/{item_id}")
            if res.status_code != 200:
                return f"Could not find {item_type} with ID {item_id}."
            item = res.json()
            total = round(float(item["price"]) * travellers, 2)
            label = item.get("title") or item.get("name") or f"{item.get('airline')} {item.get('origin')}->{item.get('destination')}"

        PENDING_ACTIONS[user_id] = {
            "action": "create_booking",
            "payload": {
                "item_type": item_type,
                "item_id": item_id,
                "travel_date": travel_date,
                "travellers": travellers,
            },
            "summary": f"Book {item_type}: {label} on {travel_date} for {travellers} traveller(s). Total: ₹{total}",
        }
        return f"CONFIRMATION_REQUIRED: {PENDING_ACTIONS[user_id]['summary']}"

    @tool
    def propose_change_booking(booking_id: int, travel_date: Optional[str] = None, travellers: Optional[int] = None) -> str:
        """Stage a modification to an existing booking's date or number of travellers and ask for UI confirmation."""
        if not travel_date and not travellers:
            return "Please provide a new travel_date (YYYY-MM-DD) or new travellers count."
        with httpx.Client(base_url=base_url, headers=headers, timeout=10.0) as client:
            res = client.get(f"/bookings/{booking_id}")
            if res.status_code != 200:
                return f"Booking #{booking_id} not found in your account."
            b = res.json()

        payload = {}
        changes = []
        if travel_date:
            payload["travel_date"] = travel_date
            changes.append(f"Date -> {travel_date}")
        if travellers:
            payload["travellers"] = travellers
            changes.append(f"Travellers -> {travellers}")

        PENDING_ACTIONS[user_id] = {
            "action": "change_booking",
            "booking_id": booking_id,
            "payload": payload,
            "summary": f"Modify Booking #{booking_id} ({b['item_title']}): {', '.join(changes)}.",
        }
        return f"CONFIRMATION_REQUIRED: {PENDING_ACTIONS[user_id]['summary']}"

    @tool
    def propose_cancel_booking(booking_id: int) -> str:
        """Stage a booking cancellation and ask the user for confirmation first."""
        with httpx.Client(base_url=base_url, headers=headers, timeout=10.0) as client:
            res = client.get(f"/bookings/{booking_id}")
            if res.status_code != 200:
                return f"Booking #{booking_id} not found in your account."
            b = res.json()

        PENDING_ACTIONS[user_id] = {
            "action": "cancel_booking",
            "booking_id": booking_id,
            "summary": f"Cancel Booking #{booking_id} ({b['item_title']} on {b['travel_date']}, Amount ₹{b['amount']}).",
        }
        return f"CONFIRMATION_REQUIRED: {PENDING_ACTIONS[user_id]['summary']}"

    @tool
    def start_payment(booking_id: int, card_number: str = "4111111111111111") -> str:
        """Process fake payment for a pending booking ID using a 16-digit card number."""
        with httpx.Client(base_url=base_url, headers=headers, timeout=10.0) as client:
            res = client.post("/payments", json={"booking_id": booking_id, "card_number": card_number})
            if res.status_code in (200, 201):
                p = res.json()
                return f"✅ Payment of ₹{p['amount']} succeeded for Booking #{booking_id} (Card ending {p['card_last4']}). Status is now CONFIRMED!"
            return f"❌ Payment failed: {res.text}"

    @tool
    def save_preference(key: str, value: str) -> str:
        """Save a user's long-term travel preference (e.g., diet='vegetarian', seat='window')."""
        pref = (
            db.query(UserPreference)
            .filter(UserPreference.user_id == user_id, UserPreference.key == key.lower())
            .first()
        )
        if pref:
            pref.value = value
        else:
            pref = UserPreference(user_id=user_id, key=key.lower(), value=value)
            db.add(pref)
        db.commit()
        return f"Saved preference: {key} = {value}"

    @tool
    def search_policies(question: str) -> str:
        """Search Yatra policy documents for refund, cancellation, baggage, or payment rules."""
        results = policy_retriever.search(question, top_k=3)
        if not results:
            return "No relevant policy found in Yatra documents. Say 'I don't know based on Yatra policy docs.'"
        return "\n\n".join(
            f"[{r['title']} - {r['section']}]\n{r['text']}" for r in results
        )

    return [
        list_my_bookings,
        search_flights,
        search_hotels,
        search_activities,
        propose_booking,
        propose_change_booking,
        propose_cancel_booking,
        start_payment,
        save_preference,
        search_policies,
    ]


def execute_pending_action(user_id: int, token: str) -> str:
    action_data = PENDING_ACTIONS.pop(user_id, None)
    if not action_data:
        return "No pending action found to confirm."

    headers = {"Authorization": f"Bearer {token}"}
    base_url = settings.api_base_url.rstrip("/")

    with httpx.Client(base_url=base_url, headers=headers, timeout=10.0) as client:
        if action_data["action"] == "create_booking":
            res = client.post("/bookings", json=action_data["payload"])
            if res.status_code in (200, 201):
                b = res.json()
                return f"✅ Booking #{b['id']} created for {b['item_title']}! Total: ₹{b['amount']} (Status: {b['status']})."
            return f"❌ Booking failed: {res.text}"

        if action_data["action"] == "change_booking":
            bid = action_data["booking_id"]
            res = client.patch(f"/bookings/{bid}", json=action_data["payload"])
            if res.status_code == 200:
                b = res.json()
                return f"✅ Booking #{bid} updated! Date: {b['travel_date']}, Travellers: {b['travellers']}, New Total: ₹{b['amount']}."
            return f"❌ Update failed: {res.text}"

        if action_data["action"] == "cancel_booking":
            bid = action_data["booking_id"]
            res = client.post(f"/bookings/{bid}/cancel")
            if res.status_code == 200:
                b = res.json()
                return f"✅ Booking #{bid} cancelled. Refund amount: ₹{b['refund_amount']}."
            return f"❌ Cancellation failed: {res.text}"

    return "Unknown action."
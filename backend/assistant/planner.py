from typing import Any, Dict, List
import httpx
from pydantic import BaseModel, Field

from backend.config import settings


class CriticVerdict(BaseModel):
    passed: bool = Field(description="True if total cost is within budget and itinerary is logical.")
    score: int = Field(ge=1, le=10, description="Quality score from 1 to 10.")
    feedback: str = Field(description="Specific fixes needed if passed is False.")


def evaluate_plan_budget(selected_items: List[Dict[str, Any]], max_budget: float) -> Dict[str, Any]:
    total = sum(float(item.get("price", 0)) for item in selected_items)
    passed = total <= max_budget
    return {
        "passed": passed,
        "total_cost": round(total, 2),
        "budget": max_budget,
        "feedback": "Within budget" if passed else f"Over budget by ₹{round(total - max_budget, 2)}. Choose a cheaper hotel or fewer activities.",
    }


def fetch_city_inventory(city: str, origin: str = "DEL", token: str = "") -> Dict[str, List[Dict[str, Any]]]:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    base_url = settings.api_base_url.rstrip("/")
    with httpx.Client(base_url=base_url, headers=headers, timeout=10.0) as client:
        flights = client.get("/flights", params={"origin": origin, "destination": city}).json()
        hotels = client.get("/hotels", params={"city": city}).json()
        activities = client.get("/activities", params={"city": city}).json()
    return {
        "flights": flights if isinstance(flights, list) else [],
        "hotels": hotels if isinstance(hotels, list) else [],
        "activities": activities if isinstance(activities, list) else [],
    }


def build_self_refined_plan(
    llm,
    city: str,
    days: int,
    travellers: int,
    budget: float,
    interests: str = "sightseeing and food",
    origin: str = "DEL",
    token: str = "",
) -> str:
    inventory = fetch_city_inventory(city=city, origin=origin, token=token)
    if not inventory["hotels"] and not inventory["activities"]:
        return f"Sorry, {city} ke liye abhi inventory available nahi hai."

    critic_llm = llm.with_structured_output(CriticVerdict)
    feedback_history = ""
    best_plan = ""

    for round_num in range(1, 4):  # Max 3 refine rounds
        draft_prompt = f"""Create a {days}-day trip itinerary for {city} for {travellers} traveller(s) within a total budget of ₹{budget}.
Interests: {interests}.
Available Flights: {inventory['flights'][:3]}
Available Hotels (per night): {inventory['hotels'][:4]}
Available Activities (per person): {inventory['activities'][:5]}

{f"Previous Critic Feedback to fix: {feedback_history}" if feedback_history else ""}

Rules:
- Pick exact items from the lists above with their IDs and prices.
- Calculate exact total cost (Flight * {travellers} + Hotel * {max(1, days - 1)} nights + Activities * {travellers}) and ensure total <= ₹{budget}.
- Present a clear Day 1 to Day {days} schedule with a final cost breakdown."""

        draft_res = llm.invoke(draft_prompt)
        best_plan = draft_res.content if isinstance(draft_res.content, str) else str(draft_res.content)

        # Critic Review
        verdict: CriticVerdict = critic_llm.invoke(
            f"Review this {days}-day {city} trip plan for {travellers} people against a strict max budget of ₹{budget} and interests ({interests}):\n\n{best_plan}"
        )
        if verdict.passed and verdict.score >= 7:
            return f"{best_plan}\n\n✅ **Plan Verified (Critic Score: {verdict.score}/10 — Round {round_num})**\nBook karne ke liye mujhe item IDs aur date bata dein!"

        feedback_history = verdict.feedback

    return f"{best_plan}\n\n⚠️ **Best Effort Plan (3 rounds completed):** {feedback_history}"
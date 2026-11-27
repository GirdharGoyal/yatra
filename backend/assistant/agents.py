from typing import TypedDict
from langgraph.graph import END, StateGraph

from backend.assistant.planner import build_self_refined_plan, fetch_city_inventory


class MultiAgentState(TypedDict):
    city: str
    origin: str
    days: int
    travellers: int
    budget: float
    interests: str
    token: str
    flight_pick: str
    hotel_pick: str
    activity_pick: str
    final_plan: str


def route_request_complexity(message: str) -> str:
    """Routes full multi-day trip planning to multi-agent team, simple queries to single assistant."""
    keywords = ["plan", "itinerary", "din", "trip", "days", "budget", "package"]
    lower = message.lower()
    if sum(1 for k in keywords if k in lower) >= 2:
        return "multi_agent_planner"
    return "single_assistant"


def run_multi_agent_trip_team(
    llm,
    city: str,
    days: int = 3,
    travellers: int = 2,
    budget: float = 25000.0,
    interests: str = "beaches and food",
    origin: str = "DEL",
    token: str = "",
) -> str:
    inventory = fetch_city_inventory(city=city, origin=origin, token=token)

    def flight_specialist(state: MultiAgentState):
        prompt = f"You are the Flight Specialist Agent. Pick the best budget flight from {state['origin']} to {state['city']} for {state['travellers']} people from: {inventory['flights'][:4]}. Reply in 2 lines with Flight ID and total flight cost."
        res = llm.invoke(prompt)
        return {"flight_pick": res.content}

    def hotel_specialist(state: MultiAgentState):
        nights = max(1, state["days"] - 1)
        prompt = f"You are the Hotel Specialist Agent. Pick the best hotel in {state['city']} for {nights} nights within budget ₹{state['budget']} from: {inventory['hotels'][:4]}. Reply in 2 lines with Hotel ID and total stay cost."
        res = llm.invoke(prompt)
        return {"hotel_pick": res.content}

    def activity_specialist(state: MultiAgentState):
        prompt = f"You are the Activities Specialist Agent. Pick 2-3 activities in {state['city']} matching '{state['interests']}' for {state['travellers']} people from: {inventory['activities'][:5]}. Reply in 3 lines with Activity IDs and total cost."
        res = llm.invoke(prompt)
        return {"activity_pick": res.content}

    def manager_merge_and_critic(state: MultiAgentState):
        refined = build_self_refined_plan(
            llm=llm,
            city=state["city"],
            days=state["days"],
            travellers=state["travellers"],
            budget=state["budget"],
            interests=state["interests"],
            origin=state["origin"],
            token=state["token"],
        )
        trace = (
            "🤖 **Multi-Agent Team Trace:**\n"
            f"- ✈️ **Flight Agent:** {state['flight_pick']}\n"
            f"- 🏨 **Hotel Agent:** {state['hotel_pick']}\n"
            f"- 🎯 **Activity Agent:** {state['activity_pick']}\n\n---\n\n"
        )
        return {"final_plan": trace + refined}

    team = StateGraph(MultiAgentState)
    team.add_node("flight_agent", flight_specialist)
    team.add_node("hotel_agent", hotel_specialist)
    team.add_node("activity_agent", activity_specialist)
    team.add_node("manager_critic", manager_merge_and_critic)

    team.set_entry_point("flight_agent")
    team.add_edge("flight_agent", "hotel_agent")
    team.add_edge("hotel_agent", "activity_agent")
    team.add_edge("activity_agent", "manager_critic")
    team.add_edge("manager_critic", END)

    compiled = team.compile()
    result = compiled.invoke({
        "city": city,
        "origin": origin,
        "days": days,
        "travellers": travellers,
        "budget": budget,
        "interests": interests,
        "token": token,
        "flight_pick": "",
        "hotel_pick": "",
        "activity_pick": "",
        "final_plan": "",
    })
    return result["final_plan"]
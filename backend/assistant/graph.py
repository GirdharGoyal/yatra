from datetime import date
from typing import Annotated, Any, Dict, List, Optional, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.assistant.agents import route_request_complexity, run_multi_agent_trip_team
from backend.assistant.prompts import SYSTEM_PROMPT
from backend.assistant.tools import PENDING_ACTIONS, build_user_tools, execute_pending_action
from backend.config import settings
from backend.models import User, UserPreference

# Short-term memory per user (last N messages)
CHAT_HISTORY: Dict[int, List[BaseMessage]] = {}
MAX_HISTORY = 12


class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]


class TripParams(BaseModel):
    city: str = Field(default="Goa", description="Destination city name")
    origin: str = Field(default="DEL", description="Origin airport/city code")
    days: int = Field(default=3, ge=1, le=14, description="Number of trip days")
    travellers: int = Field(default=2, ge=1, le=10, description="Number of travellers")
    budget: float = Field(default=25000.0, gt=0, description="Total trip budget in INR")
    interests: str = Field(default="beaches and food", description="User travel interests")


def _get_raw_llm():
    if settings.llm_provider.lower() == "groq" and settings.groq_api_key:
        from langchain_groq import ChatGroq

        return ChatGroq(
            api_key=settings.groq_api_key,
            model=settings.model_name or "openai/gpt-oss-120b",
            temperature=0.2,
        )

    if settings.gemini_api_key:
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            google_api_key=settings.gemini_api_key,
            model=settings.model_name or "gemini-2.5-flash",
            temperature=0.2,
        )

    return None


async def run_yatra_assistant(
    db: Session,
    user: User,
    token: str,
    message: str,
    resume: Optional[bool] = None,
) -> Dict[str, Any]:
    # 1. Handle Human-in-the-Loop Confirm / Cancel response
    if resume is not None:
        if resume:
            reply = execute_pending_action(user.id, token)
        else:
            PENDING_ACTIONS.pop(user.id, None)
            reply = "Action cancelled. Bataiye aur kya madad kar sakta hoon?"
        return {"reply": reply, "requires_confirmation": False, "tool_calls": []}

    raw_llm = _get_raw_llm()
    if raw_llm is None:
        return {
            "reply": "⚠️ LLM API key configured nahi hai. Kripya `.env` file mein `GEMINI_API_KEY` ya `GROQ_API_KEY` add karein.",
            "requires_confirmation": False,
            "tool_calls": [],
        }

    # 2. Check if request needs the Multi-Agent Trip Planning Team (B7 + B9)
    if route_request_complexity(message) == "multi_agent_planner":
        extractor = raw_llm.with_structured_output(TripParams)
        params: TripParams = extractor.invoke(
            f"Extract trip details from this request (use sensible defaults if omitted): {message}"
        )
        plan_reply = run_multi_agent_trip_team(
            llm=raw_llm,
            city=params.city,
            days=params.days,
            travellers=params.travellers,
            budget=params.budget,
            interests=params.interests,
            origin=params.origin,
            token=token,
        )
        return {
            "reply": plan_reply,
            "requires_confirmation": False,
            "tool_calls": ["flight_specialist", "hotel_specialist", "activity_specialist", "critic_loop"],
        }

    # 3. Single Assistant ReAct Agent Loop for search, bookings, modifications, and policy RAG
    tools = build_user_tools(user.id, token, db)
    llm_with_tools = raw_llm.bind_tools(tools)

    prefs = db.query(UserPreference).filter(UserPreference.user_id == user.id).all()
    pref_str = ", ".join(f"{p.key}: {p.value}" for p in prefs) if prefs else "None saved yet"

    sys_msg = SystemMessage(
        content=SYSTEM_PROMPT.format(
            today=date.today().isoformat(),
            user_name=user.name,
            preferences=pref_str,
        )
    )

    history = CHAT_HISTORY.get(user.id, [])[-MAX_HISTORY:]
    history.append(HumanMessage(content=message))

    def call_model(state: AgentState):
        response = llm_with_tools.invoke([sys_msg] + state["messages"])
        return {"messages": [response]}

    def should_continue(state: AgentState):
        last = state["messages"][-1]
        if getattr(last, "tool_calls", None):
            return "tools"
        return END

    workflow = StateGraph(AgentState)
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", ToolNode(tools))
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    workflow.add_edge("tools", "agent")
    app_graph = workflow.compile()

    final_state = await app_graph.ainvoke(
        {"messages": history},
        config={"recursion_limit": 8},
    )

    all_msgs = final_state["messages"]
    CHAT_HISTORY[user.id] = all_msgs[-MAX_HISTORY:]

    called_tools = []
    for m in all_msgs[len(history) - 1 :]:
        if isinstance(m, AIMessage) and getattr(m, "tool_calls", None):
            called_tools.extend(tc["name"] for tc in m.tool_calls)

    final_reply = all_msgs[-1].content if all_msgs else "Sorry, I could not process that."
    if isinstance(final_reply, list):
        final_reply = " ".join(part.get("text", "") for part in final_reply if isinstance(part, dict))

    pending = PENDING_ACTIONS.get(user.id)
    if pending:
        return {
            "reply": f"{pending['summary']}\n\nKya aap isse confirm karna chahte hain?",
            "requires_confirmation": True,
            "pending_action": pending,
            "tool_calls": called_tools,
        }

    return {
        "reply": str(final_reply),
        "requires_confirmation": False,
        "tool_calls": called_tools,
    }
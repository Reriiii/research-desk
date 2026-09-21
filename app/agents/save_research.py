from typing import Literal

from langchain_core.messages import RemoveMessage
from langgraph.graph.message import REMOVE_ALL_MESSAGES

from app.graph.state import AgentState


def save_research_node(state: AgentState):
    if not state["messages"]:
        raise RuntimeError("No research message to save")

    note = state["messages"][-1].text

    return {
        "research_notes": [*state["research_notes"], note],
        "current_step": state["current_step"] + 1,
        "tool_call_count": 0,
        "messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES)],
    }


def step_router(
    state: AgentState,
) -> Literal["researcher", "evaluator"]:
    if state["current_step"] < len(state["plan"]):
        return "researcher"
    return "evaluator"

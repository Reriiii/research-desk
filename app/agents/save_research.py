from typing import Literal

from langchain_core.messages import RemoveMessage
from langgraph.graph.message import REMOVE_ALL_MESSAGES

from app.graph.state import AgentState
from app.logging_config import get_logger


logger = get_logger("agents.save_research")


def save_research_node(state: AgentState):
    if not state["messages"]:
        raise RuntimeError("No research message to save")

    note = state["messages"][-1].text
    logger.info(
        "run_id=%s event=node_complete node=save_research step=%d note_chars=%d",
        state["run_id"],
        state["current_step"] + 1,
        len(note),
    )

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

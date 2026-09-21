from typing import Annotated, TypedDict
from uuid import uuid4

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    # Correlation ID used in diagnostics
    run_id: str

    # Conversation history
    messages: Annotated[list[BaseMessage], add_messages]

    # Original user request
    query: str

    # Research plan
    plan: list[str]

    # Current research step
    current_step: int

    # Research information collected
    research_notes: list[str]

    # Evaluation
    evaluation: str | None
    research_complete: bool

    # Control infinite loops
    retry_count: int
    tool_call_count: int

    # Final output
    final_report: str | None


def create_initial_state(query: str) -> AgentState:
    return {
        "run_id": uuid4().hex[:12],
        "messages": [],
        "query": query,
        "plan": [],
        "current_step": 0,
        "research_notes": [],
        "evaluation": None,
        "research_complete": False,
        "retry_count": 0,
        "tool_call_count": 0,
        "final_report": None,
    }

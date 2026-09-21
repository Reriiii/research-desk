from langchain_core.messages import RemoveMessage
from langgraph.graph.message import REMOVE_ALL_MESSAGES

from app.graph.state import AgentState


def retry_planner_node(state: AgentState):

    evaluation = state["evaluation"]

    additional_step = f"""
Investigate the missing information identified by the evaluator:

{evaluation}
"""

    return {
        "plan": [
            additional_step
        ],
        "current_step": 0,
        "retry_count": state["retry_count"] + 1,
        "tool_call_count": 0,
        "messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES)],
    }

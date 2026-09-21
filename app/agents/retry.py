from langchain_core.messages import RemoveMessage
from langgraph.graph.message import REMOVE_ALL_MESSAGES

from app.graph.state import AgentState
from app.logging_config import get_logger, preview


logger = get_logger("agents.retry")


def retry_planner_node(state: AgentState):

    evaluation = state["evaluation"]
    logger.warning(
        "run_id=%s event=retry_planned retry=%d evaluation=%s",
        state["run_id"],
        state["retry_count"] + 1,
        preview(evaluation),
    )

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
        "react_iteration": 0,
        "messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES)],
    }

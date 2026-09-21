from functools import lru_cache
from typing import Literal

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.config import get_model_name
from app.graph.state import AgentState


class Evaluation(BaseModel):
    sufficient: bool = Field(
        description="Whether the collected research is sufficient."
    )
    reason: str = Field(
        description="Explanation of the evaluation."
    )
    missing_information: list[str] = Field(
        default_factory=list,
        description="Important missing information.",
    )


@lru_cache(maxsize=1)
def _get_evaluation_model():
    model = ChatOpenAI(
        model=get_model_name(),
        temperature=0,
    )
    return model.with_structured_output(Evaluation)


def evaluator_node(state: AgentState):
    notes = "\n\n".join(state["research_notes"])

    result = _get_evaluation_model().invoke(
        f"""
You are evaluating research quality.

Original research question:

{state["query"]}

Research plan:

{state["plan"]}

Collected evidence:

{notes}

Determine whether there is enough information
to produce a reliable answer.

Be strict about missing evidence.
"""
    )

    evaluation_text = f"""
Reason:
{result.reason}

Missing:
{result.missing_information}
"""

    return {
        "evaluation": evaluation_text,
        "research_complete": result.sufficient,
    }


def evaluation_router(
    state: AgentState,
) -> Literal["writer", "retry_planner"]:
    if state["research_complete"] or state["retry_count"] >= 2:
        return "writer"
    return "retry_planner"

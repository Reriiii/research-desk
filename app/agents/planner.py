from functools import lru_cache

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.config import get_model_name
from app.graph.state import AgentState


class ResearchPlan(BaseModel):
    steps: list[str] = Field(
        min_length=3,
        max_length=6,
        description="Ordered research steps required to answer the user's question.",
    )


@lru_cache(maxsize=1)
def _get_planner_model():
    model = ChatOpenAI(
        model=get_model_name(),
        temperature=0,
    )
    return model.with_structured_output(ResearchPlan)


def planner_node(state: AgentState):
    query = state["query"]

    prompt = f"""
You are a research planner.

Break the following research request into 3-6 concrete research steps.

The steps should collectively provide enough evidence to answer the question.

Research request:

{query}
"""

    result = _get_planner_model().invoke(prompt)

    return {
        "plan": result.steps,
        "current_step": 0,
    }

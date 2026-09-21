from functools import lru_cache
from time import perf_counter

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.config import get_model_name
from app.graph.state import AgentState
from app.logging_config import get_logger, log_model_response, preview


logger = get_logger("agents.planner")


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
    return model.with_structured_output(ResearchPlan, include_raw=True)


def planner_node(state: AgentState):
    query = state["query"]
    run_id = state["run_id"]
    logger.info(
        "run_id=%s event=node_start node=planner query=%s",
        run_id,
        preview(query),
    )

    prompt = f"""
You are a research planner.

Break the following research request into 3-6 concrete research steps.

The steps should collectively provide enough evidence to answer the question.

Research request:

{query}
"""

    started = perf_counter()
    try:
        result = _get_planner_model().invoke(prompt)
        parsed = result.get("parsed") if isinstance(result, dict) else result
        raw = result.get("raw") if isinstance(result, dict) else None
        if parsed is None:
            parsing_error = result.get("parsing_error") if isinstance(result, dict) else None
            raise ValueError(f"Planner returned no parsed result: {parsing_error}")
    except Exception:
        logger.exception("run_id=%s event=node_failed node=planner", run_id)
        raise

    duration_ms = (perf_counter() - started) * 1000
    if raw is not None:
        log_model_response(
            logger,
            operation="planner",
            response=raw,
            duration_ms=duration_ms,
            run_id=run_id,
        )
    logger.info(
        "run_id=%s event=node_complete node=planner duration_ms=%.1f plan_steps=%d",
        run_id,
        duration_ms,
        len(parsed.steps),
    )

    return {
        "plan": parsed.steps,
        "current_step": 0,
    }

from functools import lru_cache
from time import perf_counter
from typing import Literal

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.config import get_model_name
from app.graph.state import AgentState
from app.logging_config import get_logger, log_model_response


logger = get_logger("agents.evaluator")


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
    return model.with_structured_output(Evaluation, include_raw=True)


def evaluator_node(state: AgentState):
    notes = "\n\n".join(state["research_notes"])
    run_id = state["run_id"]
    logger.info(
        "run_id=%s event=node_start node=evaluator notes=%d retries=%d",
        run_id,
        len(state["research_notes"]),
        state["retry_count"],
    )

    started = perf_counter()
    try:
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
        parsed = result.get("parsed") if isinstance(result, dict) else result
        raw = result.get("raw") if isinstance(result, dict) else None
        if parsed is None:
            parsing_error = result.get("parsing_error") if isinstance(result, dict) else None
            raise ValueError(f"Evaluator returned no parsed result: {parsing_error}")
    except Exception:
        logger.exception("run_id=%s event=node_failed node=evaluator", run_id)
        raise

    duration_ms = (perf_counter() - started) * 1000
    if raw is not None:
        log_model_response(
            logger,
            operation="evaluator",
            response=raw,
            duration_ms=duration_ms,
            run_id=run_id,
        )
    logger.info(
        "run_id=%s event=node_complete node=evaluator duration_ms=%.1f "
        "sufficient=%s missing_items=%d",
        run_id,
        duration_ms,
        parsed.sufficient,
        len(parsed.missing_information),
    )

    evaluation_text = f"""
Reason:
{parsed.reason}

Missing:
{parsed.missing_information}
"""

    return {
        "evaluation": evaluation_text,
        "research_complete": parsed.sufficient,
    }


def evaluation_router(
    state: AgentState,
) -> Literal["writer", "retry_planner"]:
    if state["research_complete"] or state["retry_count"] >= 2:
        return "writer"
    return "retry_planner"

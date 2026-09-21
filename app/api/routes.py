from time import perf_counter

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.graph.state import create_initial_state
from app.graph.workflow import graph
from app.logging_config import get_logger, preview
from app.observability import agentops_trace


router = APIRouter()
logger = get_logger("api")


class ResearchRequest(BaseModel):
    query: str = Field(min_length=1)


class ResearchResponse(BaseModel):
    run_id: str
    final_report: str
    research_complete: bool
    evaluation: str | None


@router.post("/research", response_model=ResearchResponse)
def research(request: ResearchRequest) -> ResearchResponse:
    state = create_initial_state(request.query)
    run_id = state["run_id"]
    logger.info(
        "run_id=%s event=api_request endpoint=/research query=%s",
        run_id,
        preview(request.query),
    )
    started = perf_counter()
    try:
        with agentops_trace(run_id, "api"):
            result = graph.invoke(state)
    except Exception:
        logger.exception(
            "run_id=%s event=api_request_failed endpoint=/research duration_ms=%.1f",
            run_id,
            (perf_counter() - started) * 1000,
        )
        raise

    logger.info(
        "run_id=%s event=api_request_complete endpoint=/research duration_ms=%.1f "
        "research_complete=%s",
        run_id,
        (perf_counter() - started) * 1000,
        result["research_complete"],
    )
    return ResearchResponse(
        run_id=run_id,
        final_report=result["final_report"] or "",
        research_complete=result["research_complete"],
        evaluation=result["evaluation"],
    )

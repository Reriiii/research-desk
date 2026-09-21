from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.graph.state import create_initial_state
from app.graph.workflow import graph


router = APIRouter()


class ResearchRequest(BaseModel):
    query: str = Field(min_length=1)


class ResearchResponse(BaseModel):
    final_report: str
    research_complete: bool
    evaluation: str | None


@router.post("/research", response_model=ResearchResponse)
def research(request: ResearchRequest) -> ResearchResponse:
    result = graph.invoke(create_initial_state(request.query))
    return ResearchResponse(
        final_report=result["final_report"] or "",
        research_complete=result["research_complete"],
        evaluation=result["evaluation"],
    )

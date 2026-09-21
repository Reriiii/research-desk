from functools import lru_cache
from time import perf_counter

from langchain_openai import ChatOpenAI

from app.config import get_model_name
from app.graph.state import AgentState
from app.logging_config import get_logger, log_model_response


logger = get_logger("agents.writer")


@lru_cache(maxsize=1)
def _get_writer_model():
    return ChatOpenAI(
        model=get_model_name(),
        temperature=0.2,
    )


def writer_node(state: AgentState):
    notes = "\n\n".join(state["research_notes"])
    evaluation = state["evaluation"] or "No quality concerns were reported."
    run_id = state["run_id"]
    logger.info(
        "run_id=%s event=node_start node=writer notes=%d evidence_chars=%d",
        run_id,
        len(state["research_notes"]),
        len(notes),
    )

    started = perf_counter()
    try:
        response = _get_writer_model().invoke(
            f"""
You are a professional research writer.

Answer the user's question using ONLY the evidence collected below.

Original question:

{state["query"]}

Research evidence:

{notes}

Research quality evaluation:

{evaluation}

Requirements:

- Provide a clear direct answer.
- Organize the answer into meaningful sections.
- Distinguish factual evidence from interpretation.
- Include relevant source URLs when available.
- Mention uncertainty when evidence is incomplete.
- Do not invent missing information.
"""
        )
    except Exception:
        logger.exception("run_id=%s event=node_failed node=writer", run_id)
        raise

    duration_ms = (perf_counter() - started) * 1000
    log_model_response(
        logger,
        operation="writer",
        response=response,
        duration_ms=duration_ms,
        run_id=run_id,
    )
    logger.info(
        "run_id=%s event=node_complete node=writer duration_ms=%.1f report_chars=%d",
        run_id,
        duration_ms,
        len(response.text),
    )

    return {"final_report": response.text}

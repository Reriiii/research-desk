import os
from contextlib import contextmanager
from typing import Iterator

import agentops
from agentops.enums import TraceState
from dotenv import load_dotenv

from app.logging_config import get_logger


logger = get_logger("agentops")
_initialized = False


def init_agentops() -> bool:
    global _initialized

    if _initialized:
        return True

    load_dotenv()
    if not os.getenv("AGENTOPS_API_KEY"):
        logger.info("event=agentops_disabled reason=missing_api_key")
        return False

    try:
        # AgentOps patches these modules during init. Importing them first avoids
        # its import hook observing a partially initialized LangGraph module.
        import langchain_openai  # noqa: F401
        import langgraph.graph.state  # noqa: F401

        agentops.init(
            auto_start_session=False,
            default_tags=["langgraph-research-agent"],
            instrument_llm_calls=True,
            fail_safe=True,
            log_level="CRITICAL",
            log_session_replay_url=False,
        )
    except Exception:
        logger.exception("event=agentops_init_failed")
        return False

    _initialized = True
    logger.info("event=agentops_initialized")
    return True


@contextmanager
def agentops_trace(run_id: str, source: str) -> Iterator[None]:
    if not _initialized:
        yield
        return

    trace = agentops.start_trace(
        "research-agent",
        tags={"run_id": run_id, "source": source},
    )
    trace_id = "unknown"
    if trace is not None:
        trace_id = f"{trace.span.get_span_context().trace_id:032x}"
    logger.info(
        "run_id=%s event=agentops_trace_started source=%s trace_id=%s "
        "dashboard=https://app.agentops.ai/sessions?trace_id=%s",
        run_id,
        source,
        trace_id,
        trace_id,
    )
    try:
        yield
    except Exception:
        if trace is not None:
            agentops.end_trace(trace, end_state=TraceState.ERROR)
        logger.exception(
            "run_id=%s event=agentops_trace_failed source=%s",
            run_id,
            source,
        )
        raise
    else:
        if trace is not None:
            agentops.end_trace(trace, end_state=TraceState.SUCCESS)
        logger.info(
            "run_id=%s event=agentops_trace_completed source=%s",
            run_id,
            source,
        )

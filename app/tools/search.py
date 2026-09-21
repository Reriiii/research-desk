from functools import lru_cache
from time import perf_counter

from langchain_core.tools import tool
from tavily import TavilyClient

from app.logging_config import get_logger, preview


logger = get_logger("tools.search")


@lru_cache(maxsize=1)
def _get_client() -> TavilyClient:
    return TavilyClient()


@tool
def web_search(query: str) -> str:
    """
    Search the web for reliable information.

    Use this when external or up-to-date information
    is required to answer the research question.
    """

    logger.info("event=tavily_start query=%s", preview(query))
    started = perf_counter()
    try:
        response = _get_client().search(
            query=query,
            search_depth="advanced",
            max_results=5,
        )
    except Exception:
        logger.exception(
            "event=tavily_failed duration_ms=%.1f query=%s",
            (perf_counter() - started) * 1000,
            preview(query),
        )
        raise

    logger.info(
        "event=tavily_complete duration_ms=%.1f results=%d",
        (perf_counter() - started) * 1000,
        len(response.get("results", [])),
    )

    results = []

    for item in response.get("results", []):
        results.append(
            f"""
Title: {item.get("title")}
URL: {item.get("url")}
Content: {item.get("content")}
"""
        )

    return "\n\n".join(results)

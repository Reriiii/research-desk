from functools import lru_cache

from langchain_core.tools import tool
from tavily import TavilyClient


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

    response = _get_client().search(
        query=query,
        search_depth="advanced",
        max_results=5,
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

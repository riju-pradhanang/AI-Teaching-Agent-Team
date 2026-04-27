import os
import logging

logger = logging.getLogger(__name__)


def get_search_tools():
    """
    Returns configured SerpAPI tools, or None if unavailable.
    Agents should filter None from their tools list.
    """
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        logger.warning("SERPAPI_API_KEY not set — web search disabled.")
        return None

    try:
        from agno.tools.serpapi import SerpApiTools
        return SerpApiTools(api_key=api_key)
    except Exception as exc:
        logger.warning("SerpApiTools unavailable (%s) — continuing without search.", exc)
        return None

"""Tools the agent can call.

Only stage 3 uses a tool. The other stages are single-shot calls, so giving
them tools would just add latency and a chance to wander off task.
"""

import re

from langchain.tools import tool
from tavily import TavilyClient

# One client for the process. TavilyClient reads TAVILY_API_KEY from the
# environment, which .env has already loaded by the time this imports.
_client = TavilyClient()

# Search operators the model reaches for when told to find "real, published"
# recipes: it tries to restrict itself to sites it trusts. Tavily rejects a
# query made only of these, which killed whole runs. Listing the operators
# explicitly rather than matching any "word:" keeps URLs in a query intact.
_OPERATORS = re.compile(
    r"\b(?:site|filetype|ext|inurl|intitle|allintitle|allinurl|related|cache|inanchor)"
    r":\S+",
    re.IGNORECASE,
)


@tool
def web_search(query: str) -> dict:
    """Search the web for information."""
    # The docstring above is not a comment for humans. It is the tool
    # description the model reads when deciding whether to call this, so it
    # has to describe the tool from the model's point of view.
    cleaned = _OPERATORS.sub("", query).strip()

    if not cleaned:
        # Returning the problem instead of raising it hands control back to
        # the model, which can then retry with a usable query. Raising here
        # would abort the agent, and with it the whole pipeline run.
        return {
            "error": "That query was only search operators, which this search "
            "engine rejects. Retry with plain words describing the dish, "
            "for example 'palak paneer recipe ingredients'."
        }

    return _client.search(cleaned)

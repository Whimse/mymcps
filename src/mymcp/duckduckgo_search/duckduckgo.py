
from duckduckgo_search import DDGS

def duckduckgo_search(query: str) -> str:
    """Performs an online search using DuckDuckGo and returns formatted results.

    Args:
        query (str): The search query string.

    Returns:
        str: A formatted string containing the search results, including titles, URLs, and descriptions.
    """
    with DDGS() as ddgs:
        entries = ddgs.text(query, max_results=5)

        result = "# Search Results\n"
        for entry in entries:
            result += f"[{entry['title']}]({entry['href']}) - {entry['body']}\n"

        return result
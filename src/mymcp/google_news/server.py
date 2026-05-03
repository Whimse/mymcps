
from ..server import MCPServer
from .google_news import search_google_news as search_google_news_aux

def search_google_news(search_str:str, lang:str = 'en', period:str='7d'):
    """
    Searches Google News for articles matching a query within a specific timeframe.

    Args:
        search_str (str): The search term or phrase to look for.
        lang (str, optional): A two-letter ISO language code (e.g., 'en', 'es'). 
            Must be exactly two alphabetical characters. Defaults to 'en'.
        period (str, optional): The lookback window for news results. 
            Must end with 'h' (hours), 'd' (days), 'm' (months), or 'y' (years). 
            Defaults to '7d'.

    Returns:
        list[dict]: A list of dictionaries containing news metadata (e.g., title, link, date).
        
    Raises:
        AssertionError: If `lang` is not a 2-letter alpha string or if `period` 
            does not end with a valid time unit suffix.

    Example:
        >>> results = search_google_news("OpenAI", lang="en", period="24h")
        >>> print(results[0]['title'])
    """
    return search_google_news_aux(search_str, lang = lang, period=period)

def run():

    tools = [ search_google_news ]
    
    server = MCPServer()
    server.start(tools)

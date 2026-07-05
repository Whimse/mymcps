
import os
import json
from functools import wraps

from semanticscholar import SemanticScholar
from semanticscholar.PaginatedResults import PaginatedResults

from ..server import MCPServer

def to_json(max_items=100, indent=2, as_string=True):
    """
    Decorator that converts semanticscholar method output into JSON.

    Handles:
      - Single objects (Paper, Author, Citation, Reference, etc.)
      - Lists of objects
      - PaginatedResults (capped at max_items to avoid runaway pagination)

    Args:
        max_items: max number of items to pull from a PaginatedResults object
        indent: json.dumps indent level
        as_string: if True, returns a JSON string; if False, returns a Python
                   dict/list (useful if you want to keep working with the data)
    """
    def decorator(func):
        @wraps(func)
        
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            effective_max = kwargs.get("limit", max_items)
            cap = min(max_items, effective_max) if effective_max else max_items
            converted = _convert(result, cap)
            if as_string:
                return json.dumps(converted, indent=indent, default=str)
            return converted
        return wrapper
    return decorator


def _extract_dict(obj):
    """Pull the underlying dict out of a semanticscholar object."""
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "raw_data"):
        return obj.raw_data
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    return obj  # fallback: primitive type (str, int, etc.)


def _convert(obj, max_items):
    # PaginatedResults: iterate (capped) and recursively convert each item
    if isinstance(obj, PaginatedResults):
        items = []
        for i, item in enumerate(obj):
            if i >= max_items:
                break
            items.append(_convert(item, max_items))
        return items

    # Lists/tuples of objects
    if isinstance(obj, (list, tuple)):
        return [_convert(item, max_items) for item in obj]

    # Single semanticscholar object -> dict
    if hasattr(obj, "raw_data") or hasattr(obj, "__dict__"):
        return _extract_dict(obj)

    # Already a primitive/dict
    return obj


def run():

    api_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", None)
    
    semantic_scholar = SemanticScholar(api_key=api_key)

    tools = [
            
        # Search / discovery
        semantic_scholar.search_paper,
        semantic_scholar.search_author,

        # Lookup by ID (batch versions cover the singular case with a 1-item list)
        semantic_scholar.get_papers,
        semantic_scholar.get_authors,

        # Relationships / graph traversal
        semantic_scholar.get_paper_citations,
        semantic_scholar.get_paper_references,
        semantic_scholar.get_author_papers,

        # Recommendations
        semantic_scholar.get_recommended_papers,
    ]

    tools = [ to_json()(tool) for tool in tools ]

    server = MCPServer()
    server.start(tools)
    
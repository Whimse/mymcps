
import os
from ..server import MCPServer
from semanticscholar import SemanticScholar

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

    server = MCPServer()
    server.start(tools)
    
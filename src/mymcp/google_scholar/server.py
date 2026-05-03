
from ..server import MCPServer
from . import GoogleScholarHelper

def run():

    tools = []

    helper = GoogleScholarHelper()

    tools += [
        helper.search_google_scholar, 
        helper.get_article_citations, 
    ]
    
    server = MCPServer()
    server.start(tools)

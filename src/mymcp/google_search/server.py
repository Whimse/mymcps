
from ..server import MCPServer
from .google_search import GoogleSearchHelper

def run():

    tools = []

    google_search_helper = GoogleSearchHelper()

    tools += [
        google_search_helper.search, 
    ]
    
    server = MCPServer()
    server.start(tools)

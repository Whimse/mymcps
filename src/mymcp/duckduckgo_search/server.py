
from ..server import MCPServer
from .duckduckgo import duckduckgo_search

def run():

    tools = [ duckduckgo_search ]
    
    server = MCPServer()
    server.start(tools)

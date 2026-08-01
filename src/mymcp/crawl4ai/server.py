
from ..server import MCPServer
from . import Crawler

crawler = Crawler()

def run():

    crawler = Crawler()
    
    server = MCPServer()
    server.start(crawler.tools)


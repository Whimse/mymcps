
from ..server import MCPServer
from . import Crawler

crawler = Crawler()

def run():

    crawler = Crawler()

    tools = [ crawler.crawl_tool ]
    
    server = MCPServer()
    server.start(tools)


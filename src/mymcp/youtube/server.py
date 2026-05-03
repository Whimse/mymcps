
from ..server import MCPServer
from .youtube import YouTubeHelper, get_youtube_transcript

def run():

    yt_helper = YouTubeHelper()
    tools = [ get_youtube_transcript ] + yt_helper.tools()
    
    server = MCPServer()
    server.start(tools)

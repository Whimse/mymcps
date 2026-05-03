
import os
import argparse
import logging
from fastmcp import FastMCP
from fastmcp.server.middleware import Middleware, MiddlewareContext
from langchain_litellm import ChatLiteLLM

from .tools.docker import DockerContainer
from .tools.finance import FRED
from .tools.gmail import send_email
from .tools.cmd import safe_command
from .youtube import YouTubeHelper, get_youtube_transcript

def get_args():
    
    parser = argparse.ArgumentParser()
       
    parser.add_argument(
        "-s",
        "--stdio",
        action="store_true",
        help="Run the server using stdio (for MultiServerMCPClient).",
    )
    
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable INFO logging output.",
    )    

    # Enable sets of tools
    parser.add_argument("-W", "--webcrawler", action="store_true", help="Enable Webcralwer tools")
    parser.add_argument("-G", "--gmail", action="store_true", help="Enable GMail tools")
    parser.add_argument("-Y", "--youtube", action="store_true", help="Enable YouTube tools")
    parser.add_argument("-F", "--fred", action="store_true", help="Enable Fred (finantial data) tools")    
    parser.add_argument("-C", "--cmd", type=lambda s: s.split(","), help="Enabled comma-separated command line tools")
    #parser.add_argument("-D", "--docker", action="store_true", help="Enable Docker containerized tools")

    # Tools parameters
    '''
    parser.add_argument(
        '--docker-container',
        type=str,
        default=None,
        help='Name of docker container'
    )    

    # Tools parameters
    parser.add_argument(
        '--docker-path',
        type=str,
        default=None,
        help='Folder to mount in Docker container'
    )    

    # Tools parameters
    parser.add_argument(
        '--docker-write',
        action="store_true",
        help='Enable write tools in Docker container'
    )    
    '''
    
    args = parser.parse_args()
    
    #if not (args.web_crawler or args.docker or args):
    #    parser.error("No tools were enabled. Quitting.")

    return args

async def parse_command_line_parameters():
    
    args = get_args()       
                                    
    tools = []
    
    if args.webcrawler:
        pass
                
    if args.gmail:
        tools += [
            send_email
        ]

    '''
    if args.docker:
        docker_container = DockerContainer(model, args.docker_container)
        
        if args.docker_path:
            docker_container.bind_mount(args.docker_path, "/workspace")
            docker_container.set_workdir("/workspace")
        else:
            pass   
        docker_container.run()
        

        tools += docker_container.tools(args.docker_write)
    '''
            
    if args.youtube:
        yt_helper = YouTubeHelper()
        tools += [ get_youtube_transcript ] + yt_helper.tools()

    if args.fred:
        fred = FRED()

        tools += [
            fred.get_indicators_list,
            fred.get_indicator_values,
        ]
        
    if args.cmd:    
        tools += [ safe_command(cmd_name) for cmd_name in args.cmd ]    

    logging.getLogger("mcp_server").info(f"Initializing tools ***** {len(tools)}")

    return tools

class LoggingMiddleware(Middleware):
    
    def __init__(self, mcp):
        logging.getLogger("mcp_server").info("Initializing middleware...")
        self.tools_ready = False
        self.mcp = mcp

    async def on_initialize(self, context: MiddlewareContext, call_next):
        # TODO: does not work
        logging.getLogger("mcp_server").info("Initializing...")
        return await call_next(context)

    async def on_list_tools(self, context: MiddlewareContext, call_next):
        if not self.tools_ready:
                        
            logging.getLogger("mcp_server").info("Initializing tools:")
                        
            # Get tools and stdio option
            tools = await parse_command_line_parameters()

            for tool in tools:
                logging.getLogger("mcp_server").info(f"Adding tool: {tool.__name__}")
                self.mcp.tool()(tool)

            self.tools_ready = True
            
        return await call_next(context)
    
    async def on_call_tool(self, context: MiddlewareContext, call_next):        
        logging.getLogger("mcp_server").info(f"Invoking tool: {context.message.name}({context.message.arguments})")
        return await call_next(context)    

def run():
    
    # Configure logger
    logging_level = logging.INFO if get_args().verbose else logging.WARNING
    
    logging.getLogger("fastmcp").setLevel(logging_level)
    logging.getLogger("mcp_server").setLevel(logging_level)
    logging.getLogger("uvicorn").setLevel(logging_level)
    
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(levelname)s:     %(message)s")
    handler.setFormatter(formatter)
    logging.getLogger("mcp_server").addHandler(handler)
    
    # Create MCP server
    mcp = FastMCP("MyServer")
    mcp.add_middleware(LoggingMiddleware(mcp))

    # Get tools and stdio option
    #tools = parse_command_line_parameters()
    #if not tools:
    #    print("No tools enabled!")
    #    quit()
    #for tool in tools:
    #    mcp.tool()(tool)
    
    if get_args().stdio:
        mcp.run(transport="stdio", show_banner=get_args().verbose)
    else:
        mcp.run(transport="http", host="127.0.0.1", port=8000, show_banner=get_args().verbose)

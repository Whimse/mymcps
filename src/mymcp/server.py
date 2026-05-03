import argparse
import logging
from fastmcp import FastMCP
from fastmcp.server.middleware import Middleware, MiddlewareContext

class LoggingMiddleware(Middleware):
    
    def __init__(self, mcp, tools):
        logging.getLogger("mcp_server").info("Initializing middleware...")
        
        self.tools_ready = False
        self.mcp = mcp
        self.tools = tools

        logging.getLogger("mcp_server").info(f"Loaded {len(self.tools)} tools")

    async def on_initialize(self, context: MiddlewareContext, call_next):
        # TODO: does not work
        logging.getLogger("mcp_server").info("Initializing...")
        return await call_next(context)

    async def on_list_tools(self, context: MiddlewareContext, call_next):
        if not self.tools_ready:
                        
            logging.getLogger("mcp_server").info("Initializing tools:")
                        
            for tool in self.tools:
                logging.getLogger("mcp_server").info(f"Adding tool: {tool.__name__}")
                self.mcp.tool()(tool)

            self.tools_ready = True
            
        return await call_next(context)
    
    async def on_call_tool(self, context: MiddlewareContext, call_next):        
        logging.getLogger("mcp_server").info(f"Invoking tool: {context.message.name}({context.message.arguments})")
        return await call_next(context)

class MCPServer:
    
    def __init__(self):

        self.parser = argparse.ArgumentParser()
        
        self.parser.add_argument(
            "-s",
            "--server",
            action="store_true",
            help="Run the MCP as a server with HTTP transport (instead of as a process with STDIO transport).",
        )
        
        self.parser.add_argument(
            "-v",
            "--verbose",
            action="store_true",
            help="Enable INFO logging output.",
        )    

        self.__args = None

    def add_argument(self, *args, **kwargs):
        self.parser.add_argument(*args, **kwargs)

    @property
    def args(self):
        if self.__args is None:
            self.__args = self.parser.parse_args()
            
        # Configure logger
        logging_level = logging.INFO if self.__args.verbose else logging.WARNING
        
        logging.getLogger("fastmcp").setLevel(logging_level)
        logging.getLogger("mcp_server").setLevel(logging_level)
        logging.getLogger("uvicorn").setLevel(logging_level)
                
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(levelname)s:     %(message)s")
        handler.setFormatter(formatter)
        logging.getLogger("mcp_server").addHandler(handler)
            

        return self.__args
    
    def start(self, tools):
                
        mcp = FastMCP("MyServer")
        mcp.add_middleware(LoggingMiddleware(mcp, tools))
        
        if self.args.server:
            mcp.run(transport="http", host="127.0.0.1", port=8000, show_banner=self.args.verbose)
        else:
            mcp.run(transport="stdio", show_banner=self.args.verbose)

            
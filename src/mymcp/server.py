import argparse
import logging
import time
import threading
import functools

from fastmcp import FastMCP
from fastmcp.server.middleware import Middleware, MiddlewareContext


def rate_limited(min_interval: float):
    """Decorator that ensures calls to the wrapped function are at least
    `min_interval` seconds apart, across all callers (thread-safe).

    If min_interval <= 0, the decorator is a no-op and returns the
    original function unmodified.
    """
    if min_interval <= 0:
        return lambda func: func

    lock = threading.Lock()
    last_call = {"t": 0.0}

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with lock:
                now = time.monotonic()
                wait = last_call["t"] + min_interval - now
                if wait > 0:
                    time.sleep(wait)
                last_call["t"] = time.monotonic()
            return func(*args, **kwargs)
        return wrapper
    return decorator


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

        self.parser.add_argument(
            "-i",
            "--request_interval",
            type=float,
            default=0.0,
            help="Minimal time between requests (seconds).",
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

        rate_limited_tools =  [ rate_limited(tools, self.args.request_interval) ]
        
        mcp = FastMCP("MyServer")
        mcp.add_middleware(LoggingMiddleware(mcp, rate_limited_tools))
        
        if self.args.server:
            mcp.run(transport="http", host="127.0.0.1", port=8000, show_banner=self.args.verbose)
        else:
            mcp.run(transport="stdio", show_banner=self.args.verbose)


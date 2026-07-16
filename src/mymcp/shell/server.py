
from ..server import MCPServer
from .shell import Shell

def run():

    shell = Shell()

    server = MCPServer()
    server.start(shell.get_tools())


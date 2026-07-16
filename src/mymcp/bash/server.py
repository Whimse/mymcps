
from ..server import MCPServer
from .bash import BashShell

def run():

    bash_shell = BashShell()

    server = MCPServer()
    server.start(bash_shell.get_tools())


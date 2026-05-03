import logging
from ..server import MCPServer
from . import DockerContainer


def run():

    server = MCPServer()

    server.add_argument(
        '-n',
        '--docker-container',
        type=str,
        default=None,
        help='Name of docker container'
    )    

    server.add_argument(
        '-p',
        '--docker-path',
        type=str,
        default=None,
        help='Folder to mount in Docker container'
    )    

    server.add_argument(
        '-w',
        '--docker-write',
        action="store_true",
        help='Enable write tools in Docker container'
    )

    tools =  []
    
    server.args
    
    logging.getLogger("mcp_server").info("Initializing docker container...")
    docker_container = DockerContainer(server.args.docker_container)
    
    if server.args.docker_path:
        docker_container.bind_mount(server.args.docker_path, "/workspace")
        docker_container.set_workdir("/workspace")
    else:
        pass  

    logging.getLogger("mcp_server").info("Starting docker container...")        
    docker_container.run()
    
    tools = docker_container.tools(server.args.docker_write)
    logging.getLogger("mcp_server").info("Container started")
    
    server.start(tools)

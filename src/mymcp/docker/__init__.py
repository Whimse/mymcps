import os
import pwd
import grp

import docker
from docker.errors import NotFound
import warnings
import logging
import io
import tarfile
from mymcp.utils import query_document, update_document, random_string
    
class DockerContainer:
    """
    A class to manage Docker containers, allowing for easy creation, configuration, and execution of containers.

    The DockerContainer class provides a high-level interface to interact with Docker containers. It simplifies the process of building images from Dockerfiles, running containers, managing volumes, and executing commands within the container.

    Usage:
        1. Create a DockerContainer instance by specifying a container name, either a base image or a Dockerfile, and optionally a build path.
        2. Configure the container by adding bind mounts using the bind_mount method.
        3. Start the container using the run() method.
        4. Execute commands within the container using exec_command() or other utility methods like get_tree_view(), read_file(), etc.

    Example:
        # Create a container using a base image
        container = DockerContainer("my_container", base_image="ubuntu:latest")
        container.bind_mount("/host/path", "/container/path")
        container.run()
        print(container.exec_command("ls -la"))

        # Create a container using a Dockerfile
        container = DockerContainer("my_container", dockerfile="Dockerfile", build_path="./my_project")
        container.run()
        print(container.get_tree_view("/app"))
    """
    def __init__(
            self,
            container_name: str = None,
            base_image: str = "michaelirey/ubuntu-with-tools",
            dockerfile: str = None,
            build_path: str = ".",
        ):
        self.client = docker.from_env()
        self.container_name = container_name if container_name else random_string(8)
        self.base_image = base_image
        self.dockerfile = dockerfile
        self.build_path = build_path
        self.volumes = {}
        self.user_id = os.getuid()
        self.group_id = os.getgid()
        self.container = None  # Container is not started automatically
        self.workdir = "/"
        
        try:
            self.container = self.client.containers.get(self.container_name)
            logging.getLogger("mcp_server").info(f"Container '{self.container_name}' already exists")
        except docker.errors.NotFound:
            logging.getLogger("mcp_server").info(f"Container '{self.container_name}' does not exist")
            self.container = None
    
    def run(self):
        """
        Runs the container with the specified configuration.
        """

        if self.container is not None:
            return
        
        logging.getLogger("mcp_server").info(f"Initializing container '{self.container_name}'")
            
        if self.dockerfile:
            dockerfile_path = os.path.join(self.build_path, self.dockerfile)
            if not os.path.exists(dockerfile_path):
                raise FileNotFoundError(f"Dockerfile not found at {dockerfile_path}")
            image, _ = self.client.images.build(path=self.build_path, dockerfile=self.dockerfile, tag=self.container_name)
        elif self.base_image:
            self.client.images.pull(self.base_image)
            image = self.base_image
        else:
            raise ValueError("Either a base image or a Dockerfile must be provided.")
        
        self.container = self.client.containers.run(
            image,
            name=self.container_name,
            detach=True,
            tty=True,
            volumes=self.volumes,
        )

        # Look up the user name and group name
        user_name = pwd.getpwuid(self.user_id).pw_name
        group_name = grp.getgrgid(self.group_id).gr_name

        # Install missing tools and setup user config
        self.exec_root_command(f"groupadd -g {self.group_id} {group_name}")
        self.exec_root_command(f"useradd -u {self.user_id} -g {group_name} -m {user_name}")

        self.exec_root_command("apt-get update")
        self.exec_root_command("apt-get update && apt-get install -y sudo tree")
        self.exec_root_command("apt install -y python3.10 python3-pip python3.10-venv")
        self.exec_root_command("update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1")
        self.exec_root_command("python3 -m pip install pytest==8.3.4 pytest-timeout==2.3.1")
        
    def tools(self, write_permission = False):

        read_tools = [
            self.get_workdir,
            self.set_workdir,
            self.get_tree_view,
            self.file_exists,
            self.read_file,
        ]
        
        write_tools = [
            self.write_file,
            self.exec_command,
            self.make_dir,
            self.delete,
            self.update_file,
            self.move,    
        ]
        
        if write_permission:
            return read_tools + write_tools
        else:
            return read_tools
        
    def reset(self):
        """
        Stops and removes the container, allowing the user to restart it manually.
        """
        if self.container:
            self.container.stop()
            self.container.remove()
            self.container = None
                
    def bind_mount(self, host_path: str, container_path: str):
        """
        Bind mounts a folder from the host machine to a folder inside the container.
        """
        assert os.path.exists(host_path), f"Path '{host_path}' not found"
        
        abs_host_path = os.path.abspath(host_path)
        
        self.volumes[abs_host_path] = {'bind': container_path, 'mode': 'rw'}
    
    def set_workdir(self, workdir: str) -> None:
        """
        Sets CWD

        Args:
            command (str): The path to the target CWD

        Returns:
            str: The result of the executed command.
        """
        
        self.workdir = workdir
        
        return f"CWD set to {workdir}"

    def get_workdir(self) -> None:
        """
        Sets CWD

        Returns:
            str: The result of the executed command.
        """
        
        return self.workdir

    def exec_root_command(self, command: str) -> str:
        """
        Executes a bash command as superuser.

        Args:
            command (str): The bash command to be executed.

        Returns:
            str: The output of the executed command.
        """
        
        if not self.container:
            raise RuntimeError("Container is not running. Please start it first.")
                        
        exec_result = self.container.exec_run(
            f"/bin/bash -c '{command.strip()}'",
            stdout=True,
            stderr=True,
            workdir=self.workdir,
        )
        return exec_result.output.decode()
    
    def exec_command(self, command: str) -> str:
        """
        Executes a bash command.

        Args:
            command (str): The bash command to be executed.

        Returns:
            str: The output of the executed command.
        """
        
        return self.exec_root_command(f"sudo -u#{self.user_id} -g#{self.group_id} {command}")
    
    def get_tree_view(self, path: str = "./") -> str:
        """
        Provides the recursive contents of a folder, and their file sizes. The input argument is the path to that folder.

        Args:
            path (str): The directory path to generate the structure for.

        Returns:
            str: A string representation of the tree view, including files and directories.
        """
        
        return self.exec_command(f"tree -h {path}")

    def file_exists(self, path: str) -> str:
        """
        Checks if the specified file exists in the container, given its path.

        Args:
            path (str): The file path to check.

        Returns:
            str: A message indicating whether the file exists in the container.
        """
        file_exists_cond = self.exec_command(f"file {path}")
        exists_str = "exists" if "No such file or directory" not in file_exists_cond else "does not exist"
        
        return f"File '{path}' {exists_str} in container"

    
    def read_file(self, path: str) -> str:
        """
        Provides the content of a file, given it's path.

        Args:
            path (str): The path of the file to be read

        Returns:
            str: The content of the file as a string
        """
        return self.exec_command(f"cat {path.strip()}")
    
    def write_file(self, path: str, content: str) -> str:
        """
        Writes the provided text content into a file, given it's path and the target file content.

        Args:
            path (str): The path to the file
            content (str): The content to write to the file
        """

        clean_path = path.strip()
        
        # Prepend workdir if needed
        if not os.path.isabs(clean_path):
            clean_path = os.path.join(self.workdir, clean_path)
                
        dir_name, base_name = os.path.split(clean_path)

        # Prepend './' to path if it's a relative route       
        if not dir_name:
            dir_name = './'
            
        try:
            tarstream = io.BytesIO()
            with tarfile.open(fileobj=tarstream, mode='w') as tar:
                file_data = io.BytesIO(content.encode())
                tarinfo = tarfile.TarInfo(name=base_name)
                tarinfo.size = len(content)
                tarinfo.uid = self.user_id
                tarinfo.gid = self.group_id
                tar.addfile(tarinfo, file_data)
            tarstream.seek(0)
            self.container.put_archive(dir_name, tarstream)
            return f"File '{path}' updated"
        except NotFound as e:
            return f"Error when trying to write file '{path}': {str(e)}"
    
    def make_dir(self, path: str) -> str:
        """
        Creates a directory at the specified path

        Args:
            path (str): The directory path to create

        Returns:
            str: A success message indicating the directory was created
        """
        return self.exec_command(f"mkdir -p {path.strip()}")
    
    def delete(self, path: str) -> str:
        """
        Deletes a file or a folder (recursively) at the specified path

        Args:
            path (str): The path to the file or folder to be deleted

        Returns:
            str: A success message indicating deletion
        """
        return self.exec_command(f"rm -rf {path.strip()}")            
    
    def update_file(self, path: str, instructions:str) -> str:
        """
        Modifies a file given some instructions on how to update it.

        Args:
            path (str): The path to the file or folder to be updated
            instructions (str): The instructions that must be followed to update the file

        Returns:
            str: A success message indicating the changes produced on the file
        """

        assert self.model_parameters
        
        original_content = self.read_file(path)
        
        updated_content = update_document(self.processor, original_content, instructions)
        
        return self.write_file(path, updated_content)
        
    
    def move(self, source_path: str, destination_path: str) -> str:
        """
        Moves a file to a new location

        Args:
            source_path (str): The source file path
            destination_path (str): The destination file path
        
        Returns:
            str: A success message indicating the file was moved
        """            
        return self.exec_command(f"mv {source_path.strip()} {destination_path.strip()}")

    def run_pytests(self, filepath: str) -> str:
        """
        Runs tests in the provided Python test file, and returns the tests results
        
        Args:
            filepath (str):
                A Python file (.py extension) that contains the tests (typically, includes the word 'test' in the filename)e
        """   
        
        return self.exec_command(f"pytest {filepath} --timeout=2.0")
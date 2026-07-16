"""
bash_shell.py

A Python class that wraps a persistent bash process, letting you run
commands as if you were typing into an interactive shell session.

Key idea: instead of spawning a new subprocess per command (which loses
`cd`, exported variables, shell functions, aliases, etc.), we keep ONE
long-lived `bash` process alive and feed it commands via stdin, reading
back stdout/stderr until a unique sentinel marks the command as done.

Usage:
    with BashShell() as sh:
        sh.run("cd /tmp")
        result = sh.run("pwd")
        print(result.stdout)   # /tmp

        sh.run("export FOO=bar")
        result = sh.run("echo $FOO")
        print(result.stdout)   # bar

        result = sh.run("nonexistent_command")
        print(result.exit_code)  # 127
        print(result.stderr)

    # Streaming a long-running command line by line:
    with BashShell() as sh:
        for line in sh.stream("for i in 1 2 3; do echo $i; sleep 1; done"):
            print("got:", line)
"""

from __future__ import annotations

import os
import select
import signal
import subprocess
import time
import uuid
from dataclasses import dataclass
from typing import Iterator, Optional


class BashShellError(Exception):
    """Raised for shell-level failures (not command failures)."""


class BashShellTimeout(BashShellError):
    """Raised when a command exceeds its timeout."""


@dataclass
class CommandResult:
    command: str
    stdout: str
    stderr: str
    exit_code: int
    duration: float

    @property
    def ok(self) -> bool:
        return self.exit_code == 0

    def __repr__(self) -> str:
        return (
            f"CommandResult(exit_code={self.exit_code}, "
            f"stdout={self.stdout!r}, stderr={self.stderr!r})"
        )


class BashShell:
    """
    A persistent, stateful bash session.

    Anything you could type at a bash prompt works here: pipes, redirects,
    control flow (`for`/`while`/`if`), variable assignment/export, `cd`,
    functions, `source`, background jobs (`&`), subshells, heredocs, etc.,
    because commands are literally executed by a real `bash` process.
    """

    def __init__(
        self,
        cwd: Optional[str] = None,
        env: Optional[dict] = None,
        bash_path: str = "/bin/bash",
        default_timeout: Optional[float] = 30.0,
        inherit_env: bool = True,
    ):
        self.bash_path = bash_path
        self.default_timeout = default_timeout
        self._closed = False
        self._inherit_env = inherit_env
        self._init_cwd = cwd
        self._init_env_overrides = env
        self.last_exit_code: Optional[int] = None

        # --posix keeps behavior predictable; -i is avoided (no job-control
        # noise / prompt strings to fight with). We manage our own "prompt"
        # via sentinels instead.
        self._spawn(cwd=cwd, env=env)

    # ------------------------------------------------------------------ #
    # Core execution
    # ------------------------------------------------------------------ #

    def run(self, command: str, timeout: Optional[float] = None) -> CommandResult:
        """
        Run `command` in the persistent shell and block until it completes.

        Returns a CommandResult with stdout, stderr, and exit_code.
        Raises BashShellTimeout if the command doesn't finish in time
        (the shell itself is preserved for further use if possible;
        if the runaway process can't be reaped cleanly the session is
        marked closed).
        """
        self._check_alive()
        timeout = self.default_timeout if timeout is None else timeout

        marker = uuid.uuid4().hex
        end_tag = f"__END_{marker}__"

        # Redirect the command's own stderr into fd 3 temporarily so we can
        # tell stdout and stderr apart while still sharing one sentinel.
        # Simpler & very robust approach: run command, then separately
        # print two tagged sentinels (one after stdout finishes via wait,
        # one carrying the exit code) — bash guarantees ordering on each
        # stream, and we tag stdout/stderr independently.
        wrapped = (
            f"{command}\n"
            f"__ec=$?\n"
            f'echo "{end_tag}:$__ec"\n'
            f'echo "{end_tag}:$__ec" 1>&2\n'
        )

        start = time.monotonic()
        try:
            self._proc.stdin.write(wrapped)
            self._proc.stdin.flush()
        except (BrokenPipeError, ValueError) as e:
            raise BashShellError("Shell process is not accepting input") from e

        stdout_chunks = []
        stderr_chunks = []
        stdout_done = False
        stderr_done = False
        stdout_buf = ""
        stderr_buf = ""
        exit_code = 0

        while not (stdout_done and stderr_done):
            if timeout is not None and (time.monotonic() - start) > timeout:
                self._recover_from_timeout(end_tag)
                raise BashShellTimeout(
                    f"Command timed out after {timeout}s: {command!r}"
                )

            rlist, _, _ = select.select(
                [self._out_fd, self._err_fd], [], [], 0.1
            )

            if self._out_fd in rlist and not stdout_done:
                chunk = os.read(self._out_fd, 65536).decode(errors="replace")
                stdout_buf += chunk
                stdout_buf, done, clean, code = self._extract(stdout_buf, end_tag)
                if done:
                    stdout_chunks.append(clean)
                    stdout_done = True
                    exit_code = code
                elif clean:
                    stdout_chunks.append(clean)

            if self._err_fd in rlist and not stderr_done:
                chunk = os.read(self._err_fd, 65536).decode(errors="replace")
                stderr_buf += chunk
                stderr_buf, done, clean, code = self._extract(stderr_buf, end_tag)
                if done:
                    stderr_chunks.append(clean)
                    stderr_done = True
                elif clean:
                    stderr_chunks.append(clean)

        stdout_text = "".join(stdout_chunks)
        stderr_text = "".join(stderr_chunks)

        return CommandResult(
            command=command,
            stdout=stdout_text,
            stderr=stderr_text,
            exit_code=exit_code,
            duration=time.monotonic() - start,
        )

    '''
    def stream(self, command: str, timeout: Optional[float] = None) -> Iterator[str]:
        """
        Run `command` and yield stdout lines as they arrive (generator),
        for long-running / progressively-outputting commands. The exit
        code is available afterwards via `self.last_exit_code`.
        """
        self._check_alive()
        timeout = self.default_timeout if timeout is None else timeout
        marker = uuid.uuid4().hex
        end_tag = f"__END_{marker}__"

        wrapped = f"{command}\n__ec=$?\necho \"{end_tag}:$__ec\"\n"

        start = time.monotonic()
        self._proc.stdin.write(wrapped)
        self._proc.stdin.flush()

        buf = ""
        while True:
            if timeout is not None and (time.monotonic() - start) > timeout:
                raise BashShellTimeout(f"Command timed out after {timeout}s")

            rlist, _, _ = select.select([self._out_fd], [], [], 0.1)
            if self._out_fd not in rlist:
                continue

            chunk = os.read(self._out_fd, 65536).decode(errors="replace")
            buf += chunk

            while "\n" in buf:
                line, buf = buf.split("\n", 1)
                if line.startswith(end_tag):
                    self.last_exit_code = int(line.split(":", 1)[1])
                    return
                yield line
    '''
    
    # ------------------------------------------------------------------ #
    # Convenience helpers
    # ------------------------------------------------------------------ #

    def is_alive(self) -> bool:
        return self._proc.poll() is None and not self._closed

    def interrupt(self) -> None:
        """Send Ctrl-C (SIGINT) to the running shell (e.g. to stop a hang)."""
        if self.is_alive():
            os.killpg(os.getpgid(self._proc.pid), signal.SIGINT)

    # ------------------------------------------------------------------ #
    # LLM agent tool integration
    # ------------------------------------------------------------------ #

    def get_tools(self) -> list:
        """
        Return a list of bound methods on this shell instance that are
        safe and sensible to expose as tools to an LLM agent: `run`,
        `cd`, `pwd`, `env_var`, and `interrupt`.

        These are the actual callables (not schemas/descriptions) --
        hand them to whatever mechanism your agent framework uses to
        turn Python functions into tools (e.g. auto-generating a JSON
        schema from each function's signature, type hints, and
        docstring). Each method already has type-hinted parameters and
        a docstring, so it introspects cleanly for that purpose.

        Lower-level plumbing (`stream`, `close`, `is_alive`, `export`)
        is intentionally left out since it either doesn't map onto a
        single call/response turn or is redundant with `run`.
        """
        return [
            self.run,
        ]

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            if self._proc.poll() is None:
                self._proc.stdin.write("exit\n")
                self._proc.stdin.flush()
                self._proc.wait(timeout=5)
        except Exception:
            pass
        finally:
            if self._proc.poll() is None:
                try:
                    os.killpg(os.getpgid(self._proc.pid), signal.SIGKILL)
                except Exception:
                    pass

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #

    def _recover_from_timeout(self, end_tag: str) -> None:
        """
        After a run() times out, the old command (and possibly bash's
        wait on it) is still live. Trying to signal just the runaway
        child and not bash itself is unreliable without a real PTY
        (bash and its child share a process group), so instead we
        kill the whole process group and transparently respawn a
        fresh bash process. This keeps the BashShell instance usable,
        at the cost of losing any `cd`/exports/state set since the
        last successfully-completed command.
        """
        old_proc = self._proc
        try:
            os.killpg(os.getpgid(old_proc.pid), signal.SIGKILL)
        except Exception:
            pass
        try:
            old_proc.wait(timeout=2)
        except Exception:
            pass

        self._spawn(cwd=self._init_cwd, env=self._init_env_overrides)

    def _spawn(self, cwd: Optional[str], env: Optional[dict]) -> None:
        run_env = os.environ.copy() if self._inherit_env else {}
        if env:
            run_env.update(env)
        self._proc = subprocess.Popen(
            [self.bash_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd=cwd,
            env=run_env,
            start_new_session=True,
        )
        self._out_fd = self._proc.stdout.fileno()
        self._err_fd = self._proc.stderr.fileno()

    def _check_alive(self):
        if self._closed or self._proc.poll() is not None:
            raise BashShellError("Shell process is not running (closed or crashed)")

    @staticmethod
    def _quote(s: str) -> str:
        return "'" + s.replace("'", "'\\''") + "'"

    @staticmethod
    def _extract(buf: str, end_tag: str):
        """
        Look for a full line `end_tag:<code>\\n` in buf.
        Returns (remaining_buf, done, clean_text, exit_code):
          - clean_text: everything before the tag line (safe to emit)
          - done: True once the tagged line has fully arrived
          - exit_code: parsed int if done, else 0 (ignored by caller)
        """
        idx = buf.find(end_tag)
        if idx == -1:
            # Keep a small tail back in case the tag is split across reads
            safe_len = max(0, len(buf) - len(end_tag) - 16)
            return buf[safe_len:], False, buf[:safe_len], 0

        # Need the rest of the line (":<code>\n") to fully arrive too.
        newline_idx = buf.find("\n", idx)
        if newline_idx == -1:
            # Tag found but exit code / newline not fully received yet
            return buf, False, "", 0

        clean = buf[:idx]
        tag_line = buf[idx:newline_idx]  # e.g. "__END_xxx__:0"
        try:
            code = int(tag_line.split(":", 1)[1])
        except (IndexError, ValueError):
            code = 0
        return "", True, clean, code

    # ------------------------------------------------------------------ #
    # Context manager support
    # ------------------------------------------------------------------ #

    def __enter__(self) -> "BashShell":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass


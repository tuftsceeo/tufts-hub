"""
Server lifecycle management for Tufts Hub.
"""

import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

import uvicorn
from rich.console import Console

from thub.config import load_config

console = Console()


def find_ssl_certificates(
    directory: Optional[Path] = None,
) -> tuple[Optional[str], Optional[str]]:
    """
    Find SSL certificate files in a directory.

    Looks for .pem files, attempting to identify key and cert files by name.

    Returns tuple of (ssl_keyfile, ssl_certfile), or (None, None) if not found.
    """
    if directory is None:
        directory = Path.cwd()

    pem_files = list(directory.glob("*.pem"))

    if not pem_files:
        return None, None

    ssl_keyfile = None
    ssl_certfile = None

    for pem in pem_files:
        if "key" in pem.name.lower():
            ssl_keyfile = str(pem)
        else:
            ssl_certfile = str(pem)

    if ssl_keyfile and ssl_certfile:
        return ssl_keyfile, ssl_certfile

    return None, None


def start_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    reload: bool = False,
    ssl_keyfile: Optional[str] = None,
    ssl_certfile: Optional[str] = None,
    block: bool = True,
) -> Optional[subprocess.Popen]:
    """
    Start the Tufts Hub server.

    Validates that config.json exists before starting.

    Parameters:
        host: Host to bind to (default: 127.0.0.1)
        port: Port to bind to (default: 8000)
        reload: Enable auto-reload on file changes (default: False)
        ssl_keyfile: Path to SSL key file (optional)
        ssl_certfile: Path to SSL certificate file (optional)
        block: If True, blocks until server stops (for CLI use).
               If False, starts in subprocess and returns Popen object.

    Returns:
        If block=True: None (blocks until server stops)
        If block=False: subprocess.Popen object for programmatic control

    Raises:
        FileNotFoundError: If config.json doesn't exist
    """
    # Validate config.json exists.
    config_path = Path.cwd() / "config.json"
    if not config_path.exists():
        raise FileNotFoundError(
            "config.json not found in current directory. "
            "Please create a configuration file before starting the server."
        )

    # Validate config is loadable.
    try:
        load_config()
    except Exception as e:
        raise ValueError(f"Invalid config.json: {e}")

    if block:
        # Blocking mode - for CLI use.
        if ssl_keyfile and ssl_certfile:  # pragma: no cover
            console.print(
                f"[green]Starting with SSL using {ssl_certfile} "
                f"and {ssl_keyfile}[/green]"
            )

        console.print(f"[blue]Starting Tufts Hub on {host}:{port}[/blue]")

        # Configure uvicorn logging.
        log_config = uvicorn.config.LOGGING_CONFIG
        log_config["formatters"]["default"]["fmt"] = "%(message)s"
        log_config["formatters"]["access"]["fmt"] = "%(message)s"

        uvicorn.run(
            "thub.app:app",
            host=host,
            port=port,
            reload=reload,
            ssl_keyfile=ssl_keyfile,
            ssl_certfile=ssl_certfile,
            log_config=log_config,
            access_log=False,
        )

        return None

    else:
        # Non-blocking mode - for programmatic use.
        # Start uvicorn in a subprocess.
        cmd = [
            sys.executable,
            "-m",
            "uvicorn",
            "thub.app:app",
            "--host",
            host,
            "--port",
            str(port),
        ]

        if reload:
            cmd.append("--reload")

        if ssl_keyfile and ssl_certfile:
            cmd.extend(["--ssl-keyfile", ssl_keyfile])
            cmd.extend(["--ssl-certfile", ssl_certfile])

        # Start the process.
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(Path.cwd()),
        )

        # Give it a moment to start.
        time.sleep(1)

        # Check if it started successfully.
        if process.poll() is not None:
            # Process ended immediately - something went wrong.
            stdout, stderr = process.communicate()
            raise RuntimeError(
                f"Server failed to start: {stderr.decode('utf-8')}"
            )

        return process


def stop_server(process: subprocess.Popen, timeout: int = 5) -> None:
    """
    Gracefully stop a server process.

    Attempts graceful shutdown first (SIGTERM), then force-kills if needed.

    Parameters:
        process: The Popen object returned from start_server(block=False)
        timeout: Seconds to wait for graceful shutdown before force-killing
    """
    if process.poll() is not None:
        # Already stopped.
        return

    # Try graceful shutdown.
    process.terminate()

    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        # Force kill if graceful shutdown failed.
        process.kill()
        process.wait()


@contextmanager
def run_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    reload: bool = False,
    ssl_keyfile: Optional[str] = None,
    ssl_certfile: Optional[str] = None,
):
    """
    Context manager for running the Tufts Hub server.

    Automatically starts the server on entry and stops it on exit.

    Parameters:
        host: Host to bind to (default: 127.0.0.1)
        port: Port to bind to (default: 8000)
        reload: Enable auto-reload on file changes (default: False)
        ssl_keyfile: Path to SSL key file (optional)
        ssl_certfile: Path to SSL certificate file (optional)

    Example:
        with run_server(host="127.0.0.1", port=8000) as server:
            # Server is running here
            do_work()
        # Server automatically stopped

    Yields:
        subprocess.Popen object for the server process
    """
    process = start_server(
        host=host,
        port=port,
        reload=reload,
        ssl_keyfile=ssl_keyfile,
        ssl_certfile=ssl_certfile,
        block=False,
    )

    try:
        yield process
    finally:
        stop_server(process)

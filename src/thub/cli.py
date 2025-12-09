"""
Command line interface for Tufts Hub.
"""

import argparse
import hashlib
import secrets
from pathlib import Path

import httpx
import uvicorn
from rich.console import Console

from thub.config import load_config, save_config


console = Console()


def hash_password(password: str) -> tuple[str, str]:
    """
    Hash a password using SHA256 with a random salt.

    Returns a tuple of (hash_hex, salt_hex).
    """
    salt = secrets.token_bytes(32)
    password_bytes = password.encode("utf-8")
    hash_bytes = hashlib.sha256(salt + password_bytes).digest()
    return hash_bytes.hex(), salt.hex()


def serve(args: argparse.Namespace):
    """
    Start the FastAPI server from the current directory.
    """
    # Check for SSL certificates if host is specified.
    ssl_keyfile = None
    ssl_certfile = None

    if args.host:
        # Look for any .pem files in current directory.
        pem_files = list(Path.cwd().glob("*.pem"))
        if pem_files:
            # Try to identify key and cert files.
            for pem in pem_files:
                if "key" in pem.name.lower():
                    ssl_keyfile = str(pem)
                else:
                    ssl_certfile = str(pem)

        if ssl_keyfile and ssl_certfile:
            console.print(
                f"[green]Starting with SSL using {ssl_certfile} "
                f"and {ssl_keyfile}[/green]"
            )

    console.print(
        f"[blue]Starting Tufts Hub on {args.host}:{args.port}[/blue]"
    )

    # Configure uvicorn logging to use structlog.
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["default"]["fmt"] = "%(message)s"
    log_config["formatters"]["access"]["fmt"] = "%(message)s"

    uvicorn.run(
        "thub.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        ssl_keyfile=ssl_keyfile,
        ssl_certfile=ssl_certfile,
        log_config=log_config,
        access_log=False,
    )


def adduser(args: argparse.Namespace):
    """
    Add a new user to the configuration.
    """
    config = load_config()

    if args.username in config["users"]:
        console.print(
            f"[yellow]User '{args.username}' already exists.[/yellow]"
        )
        return

    password_hash, salt = hash_password(args.password)
    config["users"][args.username] = [password_hash, salt]

    save_config(config)
    console.print(f"[green]User '{args.username}' added successfully.[/green]")


def deluser(args: argparse.Namespace):
    """
    Remove a user from the configuration.
    """
    config = load_config()

    if args.username in config["users"]:
        del config["users"][args.username]
        save_config(config)
        console.print(
            f"[green]User '{args.username}' removed successfully.[/green]"
        )
    else:
        console.print(
            f"[yellow]User '{args.username}' does not exist.[/yellow]"
        )


def new(args: argparse.Namespace):
    """
    Create a new skeleton PyScript project.
    """
    # Path to static assets directory.
    static_dir = Path(__file__).parent / "static_assets"

    # Determine PyScript version.
    if args.version:
        version = args.version
        console.print(f"[blue]Using PyScript version {version}[/blue]")
    else:
        console.print("[blue]Fetching latest PyScript version...[/blue]")
        try:
            response = httpx.get("https://pyscript.net/version.json")
            response.raise_for_status()
            version = response.json()
            console.print(f"[green]Latest version: {version}[/green]")
        except Exception as e:
            console.print(f"[red]Failed to fetch version: {e}[/red]")
            console.print("[yellow]Using default version 2025.11.2[/yellow]")
            version = "2025.11.2"

    # Create project directory.
    project_path = Path(args.project_name)

    if project_path.exists():
        console.print(
            f"[red]Directory '{args.project_name}' already exists.[/red]"
        )
        return

    project_path.mkdir()
    console.print(f"[green]Created directory '{args.project_name}'[/green]")

    # Create main.py.
    main_py = project_path / "main.py"
    main_py.write_text('print("Hello, World!")\n', encoding="utf-8")

    # Create settings.json.
    settings_json = project_path / "settings.json"
    settings_json.write_text("{}\n", encoding="utf-8")

    # Create index.html from template.
    index_html = project_path / "index.html"
    template = (static_dir / "skeleton_index.html").read_text(encoding="utf-8")
    html_content = template.format(
        project_name=args.project_name, version=version
    )
    index_html.write_text(html_content, encoding="utf-8")

    # Create style.css from template.
    style_css = project_path / "style.css"
    css_content = (static_dir / "skeleton_style.css").read_text(
        encoding="utf-8"
    )
    style_css.write_text(css_content, encoding="utf-8")

    console.print(
        f"[green]Created PyScript project '{args.project_name}' "
        f"with version {version}[/green]"
    )


def main():
    """
    Main entry point for the CLI.
    """
    parser = argparse.ArgumentParser(
        description="Tufts Hub - Self-hosted PyScript infrastructure"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Serve command.
    serve_parser = subparsers.add_parser(
        "serve", help="Start the FastAPI server"
    )
    serve_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    serve_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to (default: 8000)",
    )
    serve_parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload on file changes",
    )

    # Adduser command.
    adduser_parser = subparsers.add_parser("adduser", help="Add a new user")
    adduser_parser.add_argument("username", help="Username for the new user")
    adduser_parser.add_argument("password", help="Password for the new user")

    # Deluser command.
    deluser_parser = subparsers.add_parser("deluser", help="Remove a user")
    deluser_parser.add_argument("username", help="Username to remove")

    # New command.
    new_parser = subparsers.add_parser(
        "new", help="Create a new PyScript project"
    )
    new_parser.add_argument("project_name", help="Name of the new project")
    new_parser.add_argument(
        "--version", help="PyScript version to use (default: latest)"
    )

    # Parse arguments and dispatch.
    args = parser.parse_args()

    if args.command == "serve":
        serve(args)
    elif args.command == "adduser":
        adduser(args)
    elif args.command == "deluser":
        deluser(args)
    elif args.command == "new":
        new(args)


if __name__ == "__main__":
    main()

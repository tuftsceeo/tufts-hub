"""
FastAPI application for Tufts Hub.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import (
    Depends,
    FastAPI,
    Form,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import HTMLResponse, Response

from thub.auth import (
    create_jwt_token,
    get_current_user,
    verify_password,
    verify_jwt_token,
)
from thub.config import load_config
from thub.logging import (
    LoggingMiddleware,
    configure_logging,
    log_auth_success,
    log_shutdown,
    log_startup,
)
from thub.websocket import broadcast, connect, disconnect


# Path to static assets directory.
STATIC_DIR = Path(__file__).parent / "static_assets"


def load_template(filename: str) -> str:
    """
    Load an HTML template from the static assets directory.
    """
    template_path = STATIC_DIR / filename
    return template_path.read_text(encoding="utf-8")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan for startup and shutdown logging.
    """
    configure_logging()
    log_startup()
    yield
    log_shutdown()


app = FastAPI(title="Tufts Hub", lifespan=lifespan)
app.add_middleware(LoggingMiddleware)


@app.get("/static/{filename}")
async def serve_static(filename: str):
    """
    Serve static CSS files for login pages.
    """
    css_path = STATIC_DIR / filename
    if not css_path.exists() or not filename.endswith(".css"):
        return Response(status_code=404)

    content = css_path.read_text(encoding="utf-8")
    return Response(content=content, media_type="text/css")


@app.get("/login", response_class=HTMLResponse)
async def login_form():
    """
    Display login form.
    """
    template = load_template("login.html")
    return template.format(error="")


@app.post("/login", response_class=HTMLResponse)
async def login(username: str = Form(...), password: str = Form(...)):
    """
    Process login and return JWT token.
    """
    config = load_config()

    if not verify_password(username, password, config):
        template = load_template("login.html")
        return template.format(
            error='<p class="error">Invalid username or password</p>'
        )

    log_auth_success(username)

    token = create_jwt_token(username, config)

    template = load_template("success.html")
    response = HTMLResponse(template.format(username=username, token=token))

    # Set session cookie.
    response.set_cookie(
        key="session",
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
    )

    return response


@app.get("/{path:path}")
async def serve_static_files(
    path: str, username: str = Depends(get_current_user)
):
    """
    Serve static files from the current directory.

    Excludes config.json and .pem files for security.
    Serves index.html for directory requests if it exists.
    """
    from pathlib import Path
    from fastapi.responses import FileResponse

    # Security: block sensitive files.
    if path == "config.json" or path.endswith(".pem"):
        return Response(status_code=404)

    # Handle root path.
    if not path:
        path = "."

    # Get the file path relative to current directory.
    file_path = Path.cwd() / path

    # Security: prevent directory traversal.
    try:
        file_path = file_path.resolve()
        if not str(file_path).startswith(str(Path.cwd().resolve())):
            return Response(status_code=404)
    except (ValueError, RuntimeError):
        return Response(status_code=404)

    # If path is a directory, try to serve index.html.
    if file_path.is_dir():
        index_file = file_path / "index.html"
        if index_file.exists() and index_file.is_file():
            file_path = index_file
        else:
            return Response(status_code=404)

    # Check if file exists.
    if not file_path.exists() or not file_path.is_file():
        return Response(status_code=404)

    # Serve the file.
    return FileResponse(file_path)


@app.websocket("/channel/{channel_name}")
async def websocket_channel(websocket: WebSocket, channel_name: str):
    """
    WebSocket endpoint for pub/sub channels.

    Requires authentication via session cookie or query parameter 'token'.
    """
    # Try to get token from cookie first (most secure for browsers).
    token = websocket.cookies.get("session")

    # Fall back to query parameter for non-browser clients.
    if not token:
        token = websocket.query_params.get("token")

    if not token:
        await websocket.close(code=1008)
        return

    # Verify token and get username.
    config = load_config()
    username = verify_jwt_token(token, config)

    if not username:
        await websocket.close(code=1008)
        return

    # Connect to channel.
    await connect(websocket, channel_name, username)

    try:
        while True:
            # Receive message from client.
            message = await websocket.receive_text()

            # Broadcast to all other clients in the channel.
            await broadcast(message, channel_name, websocket)
    except WebSocketDisconnect:
        # Clean up on disconnect.
        disconnect(websocket, channel_name, username)

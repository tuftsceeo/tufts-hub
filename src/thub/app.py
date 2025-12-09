"""
FastAPI application for Tufts Hub.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, Response

from thub.auth import create_jwt_token, get_current_user, verify_password
from thub.config import load_config
from thub.logging import (
    LoggingMiddleware,
    configure_logging,
    log_auth_success,
    log_shutdown,
    log_startup,
)


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


@app.get("/")
async def root(username: str = Depends(get_current_user)):
    """
    Root endpoint requiring authentication.
    """
    return {"message": "Tufts Hub is running", "user": username}

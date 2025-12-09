"""
Authentication for Tufts Hub using JWT tokens and session cookies.
"""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import jwt
from fastapi import Cookie, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from thub.config import load_config, save_config


security = HTTPBearer(auto_error=False)


def ensure_jwt_secret(config: dict[str, Any]) -> str:
    """
    Ensure JWT secret exists in config, generating if needed.

    Returns the JWT secret key.
    """
    if config["jwt"]["secret"] is None:
        config["jwt"]["secret"] = secrets.token_urlsafe(32)
        save_config(config)

    return config["jwt"]["secret"]


def verify_password(
    username: str, password: str, config: dict[str, Any]
) -> bool:
    """
    Verify username and password against stored credentials.

    Uses constant-time comparison to prevent timing attacks.
    """
    if username not in config["users"]:
        return False

    stored_hash, stored_salt = config["users"][username]

    # Recreate the hash with provided password and stored salt.
    salt_bytes = bytes.fromhex(stored_salt)
    password_bytes = password.encode("utf-8")
    computed_hash = hashlib.sha256(salt_bytes + password_bytes).hexdigest()

    # Use constant-time comparison.
    return hmac.compare_digest(computed_hash, stored_hash)


def create_jwt_token(username: str, config: dict[str, Any]) -> str:
    """
    Create a JWT token for the given username.

    Token expires according to config's expiry_hours setting.
    """
    secret = ensure_jwt_secret(config)
    expiry_hours = config["jwt"]["expiry_hours"]

    expiry = datetime.now(timezone.utc) + timedelta(hours=expiry_hours)

    payload = {
        "sub": username,
        "exp": expiry,
        "iat": datetime.now(timezone.utc),
    }

    token = jwt.encode(payload, secret, algorithm="HS256")
    return token


def verify_jwt_token(token: str, config: dict[str, Any]) -> Optional[str]:
    """
    Verify a JWT token and return the username.

    Returns None if token is invalid or expired.
    """
    secret = ensure_jwt_secret(config)

    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        return payload["sub"]
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


async def get_current_user(
    request: Request,
    session_token: Optional[str] = Cookie(None, alias="session"),
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> str:
    """
    Extract and verify authentication from cookie or Authorization header.

    Returns the authenticated username or redirects to login page.
    """
    config = load_config()
    token = None

    # Try session cookie first.
    if session_token:
        token = session_token
    # Fall back to Authorization header.
    elif authorization:
        token = authorization.credentials

    if not token:
        # Redirect to login page.
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/login"},
        )

    username = verify_jwt_token(token, config)

    if not username:
        # Redirect to login page.
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/login"},
        )

    return username

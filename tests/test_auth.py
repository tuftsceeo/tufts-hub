"""
Tests for authentication.
"""

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import jwt
import pytest
from fastapi import HTTPException

from thub.auth import (
    create_jwt_token,
    ensure_jwt_secret,
    get_current_user,
    verify_jwt_token,
    verify_password,
)


def test_ensure_jwt_secret_generates_secret_when_missing(
    tmp_path, monkeypatch
):
    """
    JWT secret is generated when not present in config.
    """
    config_path = tmp_path / "config.json"
    monkeypatch.chdir(tmp_path)

    config = {
        "users": {},
        "proxies": {},
        "jwt": {"secret": None, "expiry_hours": 24},
    }

    secret = ensure_jwt_secret(config)

    assert secret is not None
    assert len(secret) > 0
    assert config["jwt"]["secret"] == secret

    # Should be saved to file.
    with open(config_path, "r", encoding="utf-8") as f:
        saved_config = json.load(f)

    assert saved_config["jwt"]["secret"] == secret


def test_ensure_jwt_secret_returns_existing_secret(tmp_path, monkeypatch):
    """
    JWT secret is returned when already present in config.
    """
    monkeypatch.chdir(tmp_path)

    existing_secret = "existing_secret_key"
    config = {
        "users": {},
        "proxies": {},
        "jwt": {"secret": existing_secret, "expiry_hours": 24},
    }

    secret = ensure_jwt_secret(config)

    assert secret == existing_secret


def test_verify_password_succeeds_with_correct_credentials(
    tmp_path, monkeypatch
):
    """
    Password verification succeeds with correct username and password.
    """
    monkeypatch.chdir(tmp_path)

    password = "test_password"
    salt = b"a" * 32
    password_hash = hashlib.sha256(salt + password.encode("utf-8")).hexdigest()

    config = {
        "users": {"alice": [password_hash, salt.hex()]},
        "proxies": {},
        "jwt": {"secret": "secret", "expiry_hours": 24},
    }

    assert verify_password("alice", password, config) is True


def test_verify_password_fails_with_wrong_password(tmp_path, monkeypatch):
    """
    Password verification fails with incorrect password.
    """
    monkeypatch.chdir(tmp_path)

    password = "correct_password"
    salt = b"a" * 32
    password_hash = hashlib.sha256(salt + password.encode("utf-8")).hexdigest()

    config = {
        "users": {"alice": [password_hash, salt.hex()]},
        "proxies": {},
        "jwt": {"secret": "secret", "expiry_hours": 24},
    }

    assert verify_password("alice", "wrong_password", config) is False


def test_verify_password_fails_with_nonexistent_user(tmp_path, monkeypatch):
    """
    Password verification fails for non-existent users.
    """
    monkeypatch.chdir(tmp_path)

    config = {
        "users": {},
        "proxies": {},
        "jwt": {"secret": "secret", "expiry_hours": 24},
    }

    assert verify_password("nonexistent", "password", config) is False


def test_create_jwt_token_generates_valid_token(tmp_path, monkeypatch):
    """
    JWT token creation generates a valid token with correct claims.
    """
    monkeypatch.chdir(tmp_path)

    config = {
        "users": {},
        "proxies": {},
        "jwt": {"secret": "test_secret", "expiry_hours": 24},
    }

    token = create_jwt_token("alice", config)

    assert isinstance(token, str)
    assert len(token) > 0

    # Decode and verify payload.
    payload = jwt.decode(token, "test_secret", algorithms=["HS256"])
    assert payload["sub"] == "alice"
    assert "exp" in payload
    assert "iat" in payload


def test_create_jwt_token_respects_expiry_hours(tmp_path, monkeypatch):
    """
    JWT token expiry is set according to config.
    """
    monkeypatch.chdir(tmp_path)

    config = {
        "users": {},
        "proxies": {},
        "jwt": {"secret": "test_secret", "expiry_hours": 48},
    }

    token = create_jwt_token("alice", config)
    payload = jwt.decode(token, "test_secret", algorithms=["HS256"])

    # Check expiry is approximately 48 hours from now.
    exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    now = datetime.now(timezone.utc)
    diff = exp_time - now

    # Allow some variance (47-49 hours).
    assert 47 * 3600 < diff.total_seconds() < 49 * 3600


def test_verify_jwt_token_succeeds_with_valid_token(tmp_path, monkeypatch):
    """
    JWT token verification succeeds with valid token.
    """
    monkeypatch.chdir(tmp_path)

    config = {
        "users": {},
        "proxies": {},
        "jwt": {"secret": "test_secret", "expiry_hours": 24},
    }

    token = create_jwt_token("alice", config)
    username = verify_jwt_token(token, config)

    assert username == "alice"


def test_verify_jwt_token_fails_with_expired_token(tmp_path, monkeypatch):
    """
    JWT token verification fails with expired token.
    """
    monkeypatch.chdir(tmp_path)

    config = {
        "users": {},
        "proxies": {},
        "jwt": {"secret": "test_secret", "expiry_hours": 24},
    }

    # Create token that expired 1 hour ago.
    expiry = datetime.now(timezone.utc) - timedelta(hours=1)
    payload = {"sub": "alice", "exp": expiry}
    token = jwt.encode(payload, "test_secret", algorithm="HS256")

    username = verify_jwt_token(token, config)

    assert username is None


def test_verify_jwt_token_fails_with_invalid_signature(tmp_path, monkeypatch):
    """
    JWT token verification fails with wrong signature.
    """
    monkeypatch.chdir(tmp_path)

    config = {
        "users": {},
        "proxies": {},
        "jwt": {"secret": "test_secret", "expiry_hours": 24},
    }

    # Create token with wrong secret.
    expiry = datetime.now(timezone.utc) + timedelta(hours=24)
    payload = {"sub": "alice", "exp": expiry}
    token = jwt.encode(payload, "wrong_secret", algorithm="HS256")

    username = verify_jwt_token(token, config)

    assert username is None


def test_verify_jwt_token_fails_with_malformed_token(tmp_path, monkeypatch):
    """
    JWT token verification fails with malformed token.
    """
    monkeypatch.chdir(tmp_path)

    config = {
        "users": {},
        "proxies": {},
        "jwt": {"secret": "test_secret", "expiry_hours": 24},
    }

    username = verify_jwt_token("not_a_valid_token", config)

    assert username is None


@pytest.mark.asyncio
async def test_get_current_user_succeeds_with_cookie(tmp_path, monkeypatch):
    """
    User authentication succeeds with valid session cookie.
    """
    config_path = tmp_path / "config.json"
    monkeypatch.chdir(tmp_path)

    config = {
        "users": {},
        "proxies": {},
        "jwt": {"secret": "test_secret", "expiry_hours": 24},
    }

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f)

    token = create_jwt_token("alice", config)

    mock_request = MagicMock()

    username = await get_current_user(
        request=mock_request, session_token=token
    )

    assert username == "alice"


@pytest.mark.asyncio
async def test_get_current_user_succeeds_with_bearer_token(
    tmp_path, monkeypatch
):
    """
    User authentication succeeds with valid Authorization header.
    """
    config_path = tmp_path / "config.json"
    monkeypatch.chdir(tmp_path)

    config = {
        "users": {},
        "proxies": {},
        "jwt": {"secret": "test_secret", "expiry_hours": 24},
    }

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f)

    token = create_jwt_token("bob", config)

    mock_request = MagicMock()
    mock_auth = MagicMock()
    mock_auth.credentials = token

    username = await get_current_user(
        request=mock_request, session_token=None, authorization=mock_auth
    )

    assert username == "bob"


@pytest.mark.asyncio
async def test_get_current_user_prefers_cookie_over_header(
    tmp_path, monkeypatch
):
    """
    Session cookie takes precedence over Authorization header.
    """
    config_path = tmp_path / "config.json"
    monkeypatch.chdir(tmp_path)

    config = {
        "users": {},
        "proxies": {},
        "jwt": {"secret": "test_secret", "expiry_hours": 24},
    }

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f)

    cookie_token = create_jwt_token("alice", config)
    header_token = create_jwt_token("bob", config)

    mock_request = MagicMock()
    mock_auth = MagicMock()
    mock_auth.credentials = header_token

    username = await get_current_user(
        request=mock_request,
        session_token=cookie_token,
        authorization=mock_auth,
    )

    assert username == "alice"


@pytest.mark.asyncio
async def test_get_current_user_redirects_without_token(tmp_path, monkeypatch):
    """
    User authentication redirects to login when no token provided.
    """
    config_path = tmp_path / "config.json"
    monkeypatch.chdir(tmp_path)

    config = {
        "users": {},
        "proxies": {},
        "jwt": {"secret": "test_secret", "expiry_hours": 24},
    }

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f)

    mock_request = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(
            request=mock_request,
            session_token=None,
            authorization=None,
        )

    assert exc_info.value.status_code == 303
    assert exc_info.value.headers["Location"] == "/login"


@pytest.mark.asyncio
async def test_get_current_user_redirects_with_invalid_token(
    tmp_path, monkeypatch
):
    """
    User authentication redirects to login with invalid token.
    """
    config_path = tmp_path / "config.json"
    monkeypatch.chdir(tmp_path)

    config = {
        "users": {},
        "proxies": {},
        "jwt": {"secret": "test_secret", "expiry_hours": 24},
    }

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f)

    mock_request = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(
            request=mock_request, session_token="invalid_token"
        )

    assert exc_info.value.status_code == 303
    assert exc_info.value.headers["Location"] == "/login"

"""
Tests for API proxy.
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from thub.app import app
from thub.auth import create_jwt_token
from thub.proxy import proxy_request


@pytest.fixture
def proxy_config(tmp_path, monkeypatch):
    """
    Create a config with proxy settings.
    """
    config_path = tmp_path / "config.json"
    monkeypatch.chdir(tmp_path)

    config = {
        "users": {},
        "proxies": {
            "testapi": {
                "base_url": "https://api.example.com/v1",
                "headers": {
                    "Authorization": "Bearer test_key",
                    "X-Custom-Header": "custom_value",
                },
            }
        },
        "jwt": {"secret": "test_secret", "expiry_hours": 24},
    }

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f)

    return config


@pytest.mark.asyncio
async def test_proxy_request_forwards_get_request(proxy_config):
    """
    Proxy forwards GET requests to configured API.
    """
    mock_request = MagicMock()
    mock_request.query_params = {}
    mock_request.body = AsyncMock(return_value=b"")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b'{"result": "success"}'
    mock_response.headers = {"content-type": "application/json"}

    with patch("httpx.AsyncClient") as mock_client:
        mock_client_instance = MagicMock()
        mock_client_instance.__aenter__ = AsyncMock(
            return_value=mock_client_instance
        )
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_instance.request = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_client_instance

        response = await proxy_request(
            "testapi", "endpoint", "GET", mock_request, "alice"
        )

        assert response.status_code == 200
        assert response.body == b'{"result": "success"}'

        # Verify request was made correctly.
        mock_client_instance.request.assert_called_once()
        call_args = mock_client_instance.request.call_args
        assert call_args.kwargs["method"] == "GET"
        assert call_args.kwargs["url"] == "https://api.example.com/v1/endpoint"
        assert (
            call_args.kwargs["headers"]["Authorization"] == "Bearer test_key"
        )


@pytest.mark.asyncio
async def test_proxy_request_forwards_post_with_body(proxy_config):
    """
    Proxy forwards POST requests with body content.
    """
    mock_request = MagicMock()
    mock_request.query_params = {}
    mock_request.body = AsyncMock(return_value=b'{"data": "test"}')

    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.content = b'{"id": 123}'
    mock_response.headers = {"content-type": "application/json"}

    with patch("httpx.AsyncClient") as mock_client:
        mock_client_instance = MagicMock()
        mock_client_instance.__aenter__ = AsyncMock(
            return_value=mock_client_instance
        )
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_instance.request = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_client_instance

        response = await proxy_request(
            "testapi", "create", "POST", mock_request, "bob"
        )

        assert response.status_code == 201

        # Verify body was forwarded.
        call_args = mock_client_instance.request.call_args
        assert call_args.kwargs["content"] == b'{"data": "test"}'


@pytest.mark.asyncio
async def test_proxy_request_forwards_query_parameters(proxy_config):
    """
    Proxy forwards query parameters from original request.
    """
    mock_request = MagicMock()
    mock_request.query_params = {"page": "2", "limit": "10"}
    mock_request.body = AsyncMock(return_value=b"")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"[]"
    mock_response.headers = {}

    with patch("httpx.AsyncClient") as mock_client:
        mock_client_instance = MagicMock()
        mock_client_instance.__aenter__ = AsyncMock(
            return_value=mock_client_instance
        )
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_instance.request = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_client_instance

        await proxy_request("testapi", "items", "GET", mock_request, "charlie")

        # Verify query params were forwarded.
        call_args = mock_client_instance.request.call_args
        assert call_args.kwargs["params"] == {"page": "2", "limit": "10"}


@pytest.mark.asyncio
async def test_proxy_request_strips_sensitive_response_headers(proxy_config):
    """
    Proxy strips sensitive headers from responses.
    """
    mock_request = MagicMock()
    mock_request.query_params = {}
    mock_request.body = AsyncMock(return_value=b"")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"data"
    mock_response.headers = {
        "content-type": "text/plain",
        "set-cookie": "session=abc123",
        "authorization": "Bearer secret",
        "x-custom": "value",
    }

    with patch("httpx.AsyncClient") as mock_client:
        mock_client_instance = MagicMock()
        mock_client_instance.__aenter__ = AsyncMock(
            return_value=mock_client_instance
        )
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_instance.request = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_client_instance

        response = await proxy_request(
            "testapi", "data", "GET", mock_request, "dave"
        )

        # Check sensitive headers are stripped.
        assert "set-cookie" not in response.headers
        assert "authorization" not in response.headers
        # Check non-sensitive headers are preserved.
        assert "x-custom" in response.headers


@pytest.mark.asyncio
async def test_proxy_request_strips_content_length_header(proxy_config):
    """
    Proxy strips encoding headers to let FastAPI handle them correctly.

    This prevents ERR_CONTENT_LENGTH_MISMATCH and ERR_CONTENT_DECODING_FAILED
    errors when the proxied response headers don't match the actual content.
    """
    mock_request = MagicMock()
    mock_request.query_params = {}
    mock_request.body = AsyncMock(return_value=b"")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b'{"result": "success"}'  # Actual length: 21
    mock_response.headers = {
        "content-type": "application/json",
        "content-length": "9999",  # Wrong length from upstream API.
        "transfer-encoding": "chunked",
        "content-encoding": "gzip",  # Compression header.
    }

    with patch("httpx.AsyncClient") as mock_client:
        mock_client_instance = MagicMock()
        mock_client_instance.__aenter__ = AsyncMock(
            return_value=mock_client_instance
        )
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_instance.request = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_client_instance

        response = await proxy_request(
            "testapi", "data", "GET", mock_request, "dave"
        )

        # FastAPI will add Content-Length back with the CORRECT value.
        # The key is that we stripped the incorrect value from upstream.
        assert response.body == b'{"result": "success"}'
        assert len(response.body) == 21

        # If Content-Length is present, it should be correct (21), not 9999.
        if "content-length" in response.headers:
            assert response.headers["content-length"] == "21"

        # Transfer-Encoding should be stripped.
        assert "transfer-encoding" not in response.headers

        # Content-Encoding should be stripped to prevent decode errors.
        assert "content-encoding" not in response.headers


@pytest.mark.asyncio
async def test_proxy_request_returns_404_for_unknown_api(proxy_config):
    """
    Proxy returns 404 for unconfigured API names.
    """
    mock_request = MagicMock()
    mock_request.query_params = {}
    mock_request.body = AsyncMock(return_value=b"")

    response = await proxy_request(
        "unknownapi", "endpoint", "GET", mock_request, "eve"
    )

    assert response.status_code == 404
    assert b"not configured" in response.body


@pytest.mark.asyncio
async def test_proxy_request_handles_connection_errors(proxy_config):
    """
    Proxy handles connection errors gracefully.
    """
    mock_request = MagicMock()
    mock_request.query_params = {}
    mock_request.body = AsyncMock(return_value=b"")

    with patch("httpx.AsyncClient") as mock_client:
        mock_client_instance = MagicMock()
        mock_client_instance.__aenter__ = AsyncMock(
            return_value=mock_client_instance
        )
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_instance.request = AsyncMock(
            side_effect=httpx.ConnectError("Connection failed")
        )
        mock_client.return_value = mock_client_instance

        response = await proxy_request(
            "testapi", "endpoint", "GET", mock_request, "frank"
        )

        assert response.status_code == 502
        assert b"Proxy request failed" in response.body


def test_proxy_endpoint_requires_authentication(proxy_config):
    """
    Proxy endpoint requires authentication.
    """
    client = TestClient(app)

    response = client.get("/proxy/testapi/endpoint", follow_redirects=False)

    # Should redirect to login.
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_proxy_endpoint_get_request(proxy_config):
    """
    Proxy endpoint handles GET requests.
    """
    token = create_jwt_token("alice", proxy_config)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b'{"data": "test"}'
    mock_response.headers = {"content-type": "application/json"}

    with patch("httpx.AsyncClient") as mock_client:
        mock_client_instance = MagicMock()
        mock_client_instance.__aenter__ = AsyncMock(
            return_value=mock_client_instance
        )
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_instance.request = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_client_instance

        client = TestClient(app)
        client.cookies.set("session", token)

        response = client.get("/proxy/testapi/users")

        assert response.status_code == 200
        assert response.json() == {"data": "test"}


def test_proxy_endpoint_post_request(proxy_config):
    """
    Proxy endpoint handles POST requests with body.
    """
    token = create_jwt_token("bob", proxy_config)

    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.content = b'{"id": 123}'
    mock_response.headers = {"content-type": "application/json"}

    with patch("httpx.AsyncClient") as mock_client:
        mock_client_instance = MagicMock()
        mock_client_instance.__aenter__ = AsyncMock(
            return_value=mock_client_instance
        )
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_instance.request = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_client_instance

        client = TestClient(app)
        client.cookies.set("session", token)

        response = client.post(
            "/proxy/testapi/users", json={"name": "Test User"}
        )

        assert response.status_code == 201
        assert response.json() == {"id": 123}
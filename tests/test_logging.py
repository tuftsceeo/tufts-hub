"""
Tests for structured logging.
"""

import json
from io import StringIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.testclient import TestClient

from thub.logging import (
    LoggingMiddleware,
    configure_logging,
    log_auth_success,
    log_config_loaded,
    log_proxy_request,
    log_proxy_response,
    log_shutdown,
    log_startup,
    log_websocket_connect,
    log_websocket_disconnect,
    obfuscate_sensitive,
)


def test_obfuscate_sensitive_redacts_password():
    """
    Obfuscation processor redacts password fields.
    """
    event_dict = {"username": "alice", "password": "secret123"}
    result = obfuscate_sensitive(None, None, event_dict)

    assert result["username"] == "alice"
    assert result["password"] == "***"


def test_obfuscate_sensitive_redacts_api_key():
    """
    Obfuscation processor redacts API key fields.
    """
    event_dict = {"service": "openai", "api_key": "sk-12345"}
    result = obfuscate_sensitive(None, None, event_dict)

    assert result["service"] == "openai"
    assert result["api_key"] == "***"


def test_obfuscate_sensitive_redacts_authorization():
    """
    Obfuscation processor redacts authorization headers.
    """
    event_dict = {"authorization": "Bearer token123"}
    result = obfuscate_sensitive(None, None, event_dict)

    assert result["authorization"] == "***"


def test_obfuscate_sensitive_redacts_token():
    """
    Obfuscation processor redacts token fields.
    """
    event_dict = {"user": "bob", "token": "xyz789"}
    result = obfuscate_sensitive(None, None, event_dict)

    assert result["user"] == "bob"
    assert result["token"] == "***"


def test_obfuscate_sensitive_redacts_case_insensitive():
    """
    Obfuscation processor is case insensitive.
    """
    event_dict = {"API_KEY": "key123", "Password": "pass456"}
    result = obfuscate_sensitive(None, None, event_dict)

    assert result["API_KEY"] == "***"
    assert result["Password"] == "***"


def test_obfuscate_sensitive_preserves_non_sensitive_data():
    """
    Obfuscation processor preserves non-sensitive fields.
    """
    event_dict = {
        "username": "alice",
        "email": "alice@example.com",
        "age": 30,
    }
    result = obfuscate_sensitive(None, None, event_dict)

    assert result == event_dict


def test_configure_logging_sets_up_structlog():
    """
    Configuration sets up structlog with correct processors.
    """
    configure_logging()

    # Get a logger and verify it works.
    log = structlog.get_logger()
    assert log is not None


@patch("sys.stdout", new_callable=StringIO)
def test_logging_produces_json_output(mock_stdout):
    """
    Configured logging produces JSON formatted output.
    """
    configure_logging()
    log = structlog.get_logger()

    log.info("test_event", data="value")

    output = mock_stdout.getvalue()
    log_entry = json.loads(output.strip())

    assert log_entry["event"] == "test_event"
    assert log_entry["data"] == "value"
    assert "timestamp" in log_entry
    assert log_entry["level"] == "info"


@patch("sys.stdout", new_callable=StringIO)
def test_logging_obfuscates_sensitive_data(mock_stdout):
    """
    Configured logging automatically obfuscates sensitive data.
    """
    configure_logging()
    log = structlog.get_logger()

    log.info("login", username="alice", password="secret")

    output = mock_stdout.getvalue()
    log_entry = json.loads(output.strip())

    assert log_entry["username"] == "alice"
    assert log_entry["password"] == "***"


@pytest.mark.asyncio
async def test_logging_middleware_logs_request():
    """
    Middleware logs incoming HTTP requests.
    """
    app = FastAPI()
    app.add_middleware(LoggingMiddleware)

    @app.get("/test")
    async def test_endpoint():
        return {"message": "ok"}

    with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
        configure_logging()
        client = TestClient(app)
        response = client.get("/test")

        assert response.status_code == 200

        output = mock_stdout.getvalue()
        lines = [line for line in output.strip().split("\n") if line]

        # Should have request and response logs.
        assert len(lines) >= 2

        request_log = json.loads(lines[0])
        assert request_log["event"] == "http_request"
        assert request_log["method"] == "GET"
        assert request_log["path"] == "/test"
        assert "request_id" in request_log


@pytest.mark.asyncio
async def test_logging_middleware_logs_response():
    """
    Middleware logs HTTP responses.
    """
    app = FastAPI()
    app.add_middleware(LoggingMiddleware)

    @app.get("/test")
    async def test_endpoint():
        return {"message": "ok"}

    with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
        configure_logging()
        client = TestClient(app)
        response = client.get("/test")

        assert response.status_code == 200

        output = mock_stdout.getvalue()
        lines = [line for line in output.strip().split("\n") if line]

        response_log = json.loads(lines[-1])
        assert response_log["event"] == "http_response"
        assert response_log["status_code"] == 200
        assert "request_id" in response_log


@pytest.mark.asyncio
async def test_logging_middleware_logs_exceptions():
    """
    Middleware logs exceptions with full context.
    """
    app = FastAPI()
    app.add_middleware(LoggingMiddleware)

    @app.get("/error")
    async def error_endpoint():
        raise ValueError("Test error")

    with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
        configure_logging()
        client = TestClient(app)

        with pytest.raises(ValueError):
            client.get("/error")

        output = mock_stdout.getvalue()
        lines = [line for line in output.strip().split("\n") if line]

        # Last line should be the exception log.
        error_log = json.loads(lines[-1])
        assert error_log["event"] == "http_exception"
        assert "request_id" in error_log
        assert "exception" in error_log


@patch("sys.stdout", new_callable=StringIO)
def test_log_auth_success(mock_stdout):
    """
    Authentication success logging includes username.
    """
    configure_logging()
    log_auth_success("alice")

    output = mock_stdout.getvalue()
    log_entry = json.loads(output.strip())

    assert log_entry["event"] == "authentication_success"
    assert log_entry["username"] == "alice"


@patch("sys.stdout", new_callable=StringIO)
def test_log_websocket_connect(mock_stdout):
    """
    WebSocket connection logging includes channel and username.
    """
    configure_logging()
    log_websocket_connect("chat", "bob")

    output = mock_stdout.getvalue()
    log_entry = json.loads(output.strip())

    assert log_entry["event"] == "websocket_connect"
    assert log_entry["channel"] == "chat"
    assert log_entry["username"] == "bob"


@patch("sys.stdout", new_callable=StringIO)
def test_log_websocket_disconnect(mock_stdout):
    """
    WebSocket disconnection logging includes channel and username.
    """
    configure_logging()
    log_websocket_disconnect("chat", "bob")

    output = mock_stdout.getvalue()
    log_entry = json.loads(output.strip())

    assert log_entry["event"] == "websocket_disconnect"
    assert log_entry["channel"] == "chat"
    assert log_entry["username"] == "bob"


@patch("sys.stdout", new_callable=StringIO)
def test_log_proxy_request(mock_stdout):
    """
    Proxy request logging includes API details and username.
    """
    configure_logging()
    log_proxy_request("openai", "/chat/completions", "POST", "alice")

    output = mock_stdout.getvalue()
    log_entry = json.loads(output.strip())

    assert log_entry["event"] == "proxy_request"
    assert log_entry["api_name"] == "openai"
    assert log_entry["path"] == "/chat/completions"
    assert log_entry["method"] == "POST"
    assert log_entry["username"] == "alice"


@patch("sys.stdout", new_callable=StringIO)
def test_log_proxy_response(mock_stdout):
    """
    Proxy response logging includes status code.
    """
    configure_logging()
    log_proxy_response("openai", 200)

    output = mock_stdout.getvalue()
    log_entry = json.loads(output.strip())

    assert log_entry["event"] == "proxy_response"
    assert log_entry["api_name"] == "openai"
    assert log_entry["status_code"] == 200


@patch("sys.stdout", new_callable=StringIO)
def test_log_startup(mock_stdout):
    """
    Startup logging creates appropriate event.
    """
    configure_logging()
    log_startup()

    output = mock_stdout.getvalue()
    log_entry = json.loads(output.strip())

    assert log_entry["event"] == "application_startup"


@patch("sys.stdout", new_callable=StringIO)
def test_log_shutdown(mock_stdout):
    """
    Shutdown logging creates appropriate event.
    """
    configure_logging()
    log_shutdown()

    output = mock_stdout.getvalue()
    log_entry = json.loads(output.strip())

    assert log_entry["event"] == "application_shutdown"


@patch("sys.stdout", new_callable=StringIO)
def test_log_config_loaded(mock_stdout):
    """
    Configuration loaded logging includes counts.
    """
    configure_logging()
    log_config_loaded(5, 3)

    output = mock_stdout.getvalue()
    log_entry = json.loads(output.strip())

    assert log_entry["event"] == "configuration_loaded"
    assert log_entry["user_count"] == 5
    assert log_entry["proxy_count"] == 3

"""
Structured logging configuration for Tufts Hub.
"""

import logging
import sys
import uuid
from typing import Any

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


# Sensitive keys that should be obfuscated in logs.
SENSITIVE_KEYS = {
    "password",
    "api_key",
    "authorization",
    "token",
    "secret",
    "key",
}


def obfuscate_sensitive(
    logger: Any, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """
    Obfuscate sensitive data in log events.

    Replaces values for keys matching sensitive patterns with '***'.
    """
    for key in list(event_dict.keys()):
        if any(sensitive in key.lower() for sensitive in SENSITIVE_KEYS):
            event_dict[key] = "***"
    return event_dict


def configure_logging():
    """
    Configure structlog for JSON output to stdout.

    Sets up processors for timestamps, obfuscation, and formatting.
    """
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            obfuscate_sensitive,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all HTTP requests and responses.
    """

    async def dispatch(self, request: Request, call_next):
        """
        Log request details, process request, and log response.
        """
        request_id = str(uuid.uuid4())
        log = structlog.get_logger()

        # Log incoming request.
        log.info(
            "http_request",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client=request.client.host if request.client else None,
        )

        # Process request and capture response.
        try:
            response = await call_next(request)

            # Log response.
            log.info(
                "http_response",
                request_id=request_id,
                status_code=response.status_code,
            )

            return response
        except Exception as exc:
            # Log exception with full context.
            log.error(
                "http_exception",
                request_id=request_id,
                exc_info=exc,
            )
            raise


def log_auth_success(username: str):
    """
    Log successful authentication.
    """
    log = structlog.get_logger()
    log.info("authentication_success", username=username)


def log_websocket_connect(channel: str, username: str):
    """
    Log WebSocket connection.
    """
    log = structlog.get_logger()
    log.info("websocket_connect", channel=channel, username=username)


def log_websocket_disconnect(channel: str, username: str):
    """
    Log WebSocket disconnection.
    """
    log = structlog.get_logger()
    log.info("websocket_disconnect", channel=channel, username=username)


def log_proxy_request(api_name: str, path: str, method: str, username: str):
    """
    Log proxy request to external API.
    """
    log = structlog.get_logger()
    log.info(
        "proxy_request",
        api_name=api_name,
        path=path,
        method=method,
        username=username,
    )


def log_proxy_response(api_name: str, status_code: int):
    """
    Log proxy response from external API.
    """
    log = structlog.get_logger()
    log.info("proxy_response", api_name=api_name, status_code=status_code)


def log_startup():
    """
    Log application startup.
    """
    log = structlog.get_logger()
    log.info("application_startup")


def log_shutdown():
    """
    Log application shutdown.
    """
    log = structlog.get_logger()
    log.info("application_shutdown")


def log_config_loaded(user_count: int, proxy_count: int):
    """
    Log configuration loading with counts.

    Passwords and API keys are automatically obfuscated by the processor.
    """
    log = structlog.get_logger()
    log.info(
        "configuration_loaded",
        user_count=user_count,
        proxy_count=proxy_count,
    )

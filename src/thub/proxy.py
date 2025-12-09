"""
API proxy functionality for Tufts Hub.
"""

from typing import Any, Dict, Optional

import httpx
from fastapi import Request, Response

from thub.config import load_config
from thub.logging import log_proxy_request, log_proxy_response


# Headers to strip from proxied responses for security.
SENSITIVE_RESPONSE_HEADERS = {
    "set-cookie",
    "authorization",
    "www-authenticate",
    "proxy-authenticate",
    "proxy-authorization",
    "content-length",  # Let FastAPI recalculate this.
    "transfer-encoding",  # Let FastAPI handle encoding.
    "content-encoding",  # Let FastAPI handle compression.
}


async def proxy_request(
    api_name: str,
    path: str,
    method: str,
    request: Request,
    username: str,
) -> Response:
    """
    Proxy a request to a configured external API.

    Returns the proxied response with sensitive headers removed.
    """
    config = load_config()

    # Check if API is configured.
    if api_name not in config.get("proxies", {}):
        return Response(
            content=f"API '{api_name}' not configured",
            status_code=404,
        )

    api_config = config["proxies"][api_name]
    base_url = api_config.get("base_url", "").rstrip("/")
    configured_headers = api_config.get("headers", {})

    # Build full URL.
    full_path = path.lstrip("/")
    url = f"{base_url}/{full_path}"

    # Get query parameters from original request.
    query_params = dict(request.query_params)

    # Get request body if present.
    body = await request.body()

    # Prepare headers (use configured headers).
    headers = dict(configured_headers)

    # Log the proxy request.
    log_proxy_request(api_name, path, method, username)

    # Make the proxied request.
    async with httpx.AsyncClient() as client:
        try:
            response = await client.request(
                method=method,
                url=url,
                params=query_params,
                content=body if body else None,
                headers=headers,
                follow_redirects=False,
            )

            # Log the proxy response.
            log_proxy_response(api_name, response.status_code)

            # Prepare response headers (strip sensitive ones).
            response_headers = {
                key: value
                for key, value in response.headers.items()
                if key.lower() not in SENSITIVE_RESPONSE_HEADERS
            }

            # Return proxied response.
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=response_headers,
                media_type=response.headers.get(
                    "content-type", "application/octet-stream"
                ),
            )

        except httpx.RequestError as e:
            return Response(
                content=f"Proxy request failed: {str(e)}",
                status_code=502,
            )

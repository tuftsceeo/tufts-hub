"""
Tests for app middleware and headers.
"""

import json

from fastapi.testclient import TestClient

from thub.app import app


def test_cors_headers_present(tmp_path, monkeypatch):
    """
    CORS headers are present in responses when Origin header is sent.
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

    client = TestClient(app)

    response = client.get("/login", headers={"Origin": "http://localhost"})

    # Check CORS headers.
    assert "access-control-allow-origin" in response.headers
    # The value can be "*" or the echoed origin depending on endpoint.
    assert response.headers["access-control-allow-origin"] in [
        "*",
        "http://localhost",
    ]


def test_coi_headers_present(tmp_path, monkeypatch):
    """
    Cross-Origin Isolation headers are present in responses.
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

    client = TestClient(app)

    response = client.get("/login")

    # Check COI headers.
    assert "cross-origin-opener-policy" in response.headers
    assert response.headers["cross-origin-opener-policy"] == "same-origin"

    assert "cross-origin-embedder-policy" in response.headers
    assert response.headers["cross-origin-embedder-policy"] == "require-corp"

    assert "cross-origin-resource-policy" in response.headers
    assert response.headers["cross-origin-resource-policy"] == "cross-origin"


def test_cors_and_coi_headers_on_static_files(tmp_path, monkeypatch):
    """
    CORS and COI headers are present on static file responses.
    """
    config_path = tmp_path / "config.json"
    monkeypatch.chdir(tmp_path)

    config = {
        "users": {
            "testuser": {
                "password_hash": "somehash",
                "salt": "somesalt",
            }
        },
        "proxies": {},
        "jwt": {"secret": "test_secret", "expiry_hours": 24},
    }

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f)

    # Create a test file.
    test_file = tmp_path / "test.html"
    test_file.write_text("<h1>Hello World</h1>", encoding="utf-8")

    # Create a valid JWT token.
    from thub.auth import create_jwt_token

    token = create_jwt_token("testuser", config)

    client = TestClient(app)

    response = client.get(
        "/test.html",
        cookies={"session": token},
        headers={"Origin": "http://localhost"},
    )

    assert response.status_code == 200

    # Check CORS headers.
    assert "access-control-allow-origin" in response.headers
    # With allow_credentials=True, origin is echoed back, not "*".
    assert (
        response.headers["access-control-allow-origin"] == "http://localhost"
    )

    # Check COI headers.
    assert "cross-origin-opener-policy" in response.headers
    assert response.headers["cross-origin-opener-policy"] == "same-origin"

    assert "cross-origin-embedder-policy" in response.headers
    assert response.headers["cross-origin-embedder-policy"] == "require-corp"

    assert "cross-origin-resource-policy" in response.headers
    assert response.headers["cross-origin-resource-policy"] == "cross-origin"

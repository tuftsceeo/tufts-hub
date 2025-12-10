"""
Tests for static file serving.
"""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from thub.app import app
from thub.auth import create_jwt_token


def test_serve_static_file(tmp_path, monkeypatch):
    """
    Static file serving returns file content.
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

    # Create a test file.
    test_file = tmp_path / "test.html"
    test_file.write_text("<h1>Hello World</h1>", encoding="utf-8")

    token = create_jwt_token("alice", config)

    client = TestClient(app)
    client.cookies.set("session", token)

    response = client.get("/test.html")

    assert response.status_code == 200
    assert response.text == "<h1>Hello World</h1>"


def test_serve_static_file_in_subdirectory(tmp_path, monkeypatch):
    """
    Static file serving works for files in subdirectories.
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

    # Create subdirectory with file.
    subdir = tmp_path / "examples" / "test"
    subdir.mkdir(parents=True)
    test_file = subdir / "index.html"
    test_file.write_text("<h1>Example</h1>", encoding="utf-8")

    token = create_jwt_token("alice", config)

    client = TestClient(app)
    client.cookies.set("session", token)

    response = client.get("/examples/test/index.html")

    assert response.status_code == 200
    assert response.text == "<h1>Example</h1>"


def test_serve_static_blocks_config_json(tmp_path, monkeypatch):
    """
    Static file serving blocks access to config.json.
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

    client = TestClient(app)
    client.cookies.set("session", token)

    response = client.get("/config.json")

    assert response.status_code == 404


def test_serve_static_blocks_pem_files(tmp_path, monkeypatch):
    """
    Static file serving blocks access to .pem files.
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

    # Create a .pem file.
    pem_file = tmp_path / "certificate.pem"
    pem_file.write_text("SECRET KEY DATA", encoding="utf-8")

    token = create_jwt_token("alice", config)

    client = TestClient(app)
    client.cookies.set("session", token)

    response = client.get("/certificate.pem")

    assert response.status_code == 404


def test_serve_static_prevents_directory_traversal(tmp_path, monkeypatch):
    """
    Static file serving prevents directory traversal attacks.
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

    # Create a file outside the current directory.
    parent_file = tmp_path.parent / "secret.txt"
    parent_file.write_text("SECRET DATA", encoding="utf-8")

    token = create_jwt_token("alice", config)

    client = TestClient(app)
    client.cookies.set("session", token)

    # Try to access file outside current directory.
    response = client.get("/../secret.txt")

    assert response.status_code == 404


def test_serve_static_returns_404_for_nonexistent_file(tmp_path, monkeypatch):
    """
    Static file serving returns 404 for non-existent files.
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

    client = TestClient(app)
    client.cookies.set("session", token)

    response = client.get("/nonexistent.html")

    assert response.status_code == 404


def test_serve_static_returns_404_for_directory(tmp_path, monkeypatch):
    """
    Static file serving returns 404 for directories without index.html.
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

    # Create a directory without index.html.
    test_dir = tmp_path / "examples"
    test_dir.mkdir()

    token = create_jwt_token("alice", config)

    client = TestClient(app)
    client.cookies.set("session", token)

    response = client.get("/examples")

    assert response.status_code == 404


def test_serve_static_serves_index_html_for_directory(tmp_path, monkeypatch):
    """
    Static file serving serves index.html for directory requests.
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

    # Create a directory with index.html.
    test_dir = tmp_path / "examples"
    test_dir.mkdir()
    index_file = test_dir / "index.html"
    index_file.write_text("<h1>Example Index</h1>", encoding="utf-8")

    token = create_jwt_token("alice", config)

    client = TestClient(app)
    client.cookies.set("session", token)

    response = client.get("/examples")

    assert response.status_code == 200
    assert response.text == "<h1>Example Index</h1>"


def test_serve_static_serves_index_html_with_trailing_slash(
    tmp_path, monkeypatch
):
    """
    Static file serving serves index.html with trailing slash.
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

    # Create a directory with index.html.
    test_dir = tmp_path / "examples"
    test_dir.mkdir()
    index_file = test_dir / "index.html"
    index_file.write_text("<h1>Example Index</h1>", encoding="utf-8")

    token = create_jwt_token("alice", config)

    client = TestClient(app)
    client.cookies.set("session", token)

    response = client.get("/examples/")

    assert response.status_code == 200
    assert response.text == "<h1>Example Index</h1>"


def test_serve_static_requires_authentication(tmp_path, monkeypatch):
    """
    Static file serving requires authentication.
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

    # Create a test file.
    test_file = tmp_path / "test.html"
    test_file.write_text("<h1>Hello World</h1>", encoding="utf-8")

    client = TestClient(app)

    response = client.get("/test.html", follow_redirects=False)

    # Should redirect to login with next parameter.
    assert response.status_code == 303
    assert response.headers["location"] == "/login?next=/test.html"


def test_static_files_have_no_cache_headers(tmp_path, monkeypatch):
    """
    Static files are served with no-cache headers to prevent stale content.
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
    client.cookies.set("session", token)

    response = client.get("/test.html")

    assert response.status_code == 200
    # Check for no-cache headers.
    assert "cache-control" in response.headers
    assert "no-cache" in response.headers["cache-control"]
    assert "no-store" in response.headers["cache-control"]
    assert "must-revalidate" in response.headers["cache-control"]


def test_404_page_is_playful(tmp_path, monkeypatch):
    """
    404 errors return a playful custom error page.
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

    # Create a valid JWT token.
    from thub.auth import create_jwt_token

    token = create_jwt_token("testuser", config)

    client = TestClient(app)
    client.cookies.set("session", token)

    # Try to access a non-existent file.
    response = client.get("/does-not-exist.html")

    assert response.status_code == 404
    # Check for playful 404 page content.
    assert "404" in response.text
    assert "Page Not Found" in response.text
    assert "hide and seek" in response.text
    assert "Take Me Home" in response.text

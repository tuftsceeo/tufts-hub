"""
Tests for command line interface.
"""

import hashlib
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from thub.cli import hash_password, adduser, deluser, new


def test_hash_password_returns_hex_strings():
    """
    Password hashing returns hex-encoded hash and salt.
    """
    password_hash, salt = hash_password("test_password")

    # Check both are hex strings.
    assert isinstance(password_hash, str)
    assert isinstance(salt, str)
    assert len(password_hash) == 64  # SHA256 produces 32 bytes = 64 hex.
    assert len(salt) == 64  # 32 bytes of salt = 64 hex.


def test_hash_password_produces_unique_salts():
    """
    Each call to hash_password produces a unique salt.
    """
    hash1, salt1 = hash_password("same_password")
    hash2, salt2 = hash_password("same_password")

    assert salt1 != salt2
    assert hash1 != hash2


def test_hash_password_is_deterministic_with_same_salt():
    """
    Same password and salt produce same hash.
    """
    password = "test_password"
    salt_bytes = b"a" * 32

    hash1 = hashlib.sha256(salt_bytes + password.encode("utf-8")).digest()
    hash2 = hashlib.sha256(salt_bytes + password.encode("utf-8")).digest()

    assert hash1 == hash2


def test_adduser_creates_new_user(tmp_path, monkeypatch):
    """
    Adding user creates entry in config with hashed password.
    """
    config_path = tmp_path / "config.json"
    monkeypatch.chdir(tmp_path)

    args = MagicMock()
    args.username = "testuser"
    args.password = "testpass"

    adduser(args)

    assert config_path.exists()

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    assert "testuser" in config["users"]
    assert isinstance(config["users"]["testuser"], list)
    assert len(config["users"]["testuser"]) == 2


def test_adduser_does_not_overwrite_existing_user(tmp_path, monkeypatch):
    """
    Adding existing user does not change their password.
    """
    config_path = tmp_path / "config.json"
    monkeypatch.chdir(tmp_path)

    # Create existing user.
    original_config = {
        "users": {"testuser": ["original_hash", "original_salt"]},
        "proxies": {},
    }

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(original_config, f)

    args = MagicMock()
    args.username = "testuser"
    args.password = "newpassword"

    adduser(args)

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    # Original credentials should remain unchanged.
    assert config["users"]["testuser"] == ["original_hash", "original_salt"]


def test_deluser_removes_existing_user(tmp_path, monkeypatch):
    """
    Deleting user removes their entry from config.
    """
    config_path = tmp_path / "config.json"
    monkeypatch.chdir(tmp_path)

    original_config = {
        "users": {"alice": ["hash1", "salt1"], "bob": ["hash2", "salt2"]},
        "proxies": {},
    }

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(original_config, f)

    args = MagicMock()
    args.username = "alice"

    deluser(args)

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    assert "alice" not in config["users"]
    assert "bob" in config["users"]


def test_deluser_handles_nonexistent_user(tmp_path, monkeypatch):
    """
    Deleting non-existent user does not raise error.
    """
    config_path = tmp_path / "config.json"
    monkeypatch.chdir(tmp_path)

    original_config = {"users": {"alice": ["hash", "salt"]}, "proxies": {}}

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(original_config, f)

    args = MagicMock()
    args.username = "nonexistent"

    # Should not raise an exception.
    deluser(args)

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    # Original user should remain.
    assert "alice" in config["users"]


@patch("thub.cli.httpx.get")
def test_new_creates_project_with_specified_version(
    mock_get, tmp_path, monkeypatch
):
    """
    Creating new project with specified version uses that version.
    """
    monkeypatch.chdir(tmp_path)

    args = MagicMock()
    args.project_name = "myproject"
    args.version = "2025.1.1"
    args.offline = False

    new(args)

    project_path = tmp_path / "myproject"
    assert project_path.exists()

    # Check all four files exist.
    assert (project_path / "main.py").exists()
    assert (project_path / "settings.json").exists()
    assert (project_path / "style.css").exists()
    assert (project_path / "index.html").exists()

    # Check index.html contains correct version.
    html_content = (project_path / "index.html").read_text(encoding="utf-8")
    assert "2025.1.1" in html_content
    assert "myproject" in html_content

    # Should not fetch version from API.
    mock_get.assert_not_called()


@patch("thub.cli.httpx.get")
def test_new_fetches_latest_version_when_not_specified(
    mock_get, tmp_path, monkeypatch
):
    """
    Creating new project without version fetches latest from API.
    """
    monkeypatch.chdir(tmp_path)

    mock_response = MagicMock()
    mock_response.json.return_value = "2025.12.1"
    mock_get.return_value = mock_response

    args = MagicMock()
    args.project_name = "myproject"
    args.version = None
    args.offline = False

    new(args)

    # Should fetch version.
    mock_get.assert_called_once_with("https://pyscript.net/version.json")

    # Check version in HTML.
    html_content = (tmp_path / "myproject" / "index.html").read_text(
        encoding="utf-8"
    )
    assert "2025.12.1" in html_content


@patch("thub.cli.httpx.get")
def test_new_uses_default_version_on_fetch_failure(
    mock_get, tmp_path, monkeypatch
):
    """
    Creating new project uses default version if API fetch fails.
    """
    monkeypatch.chdir(tmp_path)

    mock_get.side_effect = Exception("Network error")

    args = MagicMock()
    args.project_name = "myproject"
    args.version = None
    args.offline = False

    new(args)

    # Check default version in HTML.
    html_content = (tmp_path / "myproject" / "index.html").read_text(
        encoding="utf-8"
    )
    assert "2025.11.2" in html_content


def test_new_does_not_overwrite_existing_directory(tmp_path, monkeypatch):
    """
    Creating new project does not overwrite existing directory.
    """
    monkeypatch.chdir(tmp_path)

    # Create existing directory.
    project_path = tmp_path / "myproject"
    project_path.mkdir()
    (project_path / "existing_file.txt").write_text("important data")

    args = MagicMock()
    args.project_name = "myproject"
    args.version = "2025.1.1"
    args.offline = False

    new(args)

    # Existing file should still be there.
    assert (project_path / "existing_file.txt").exists()
    # New files should not be created.
    assert not (project_path / "main.py").exists()


def test_new_creates_correct_file_contents(tmp_path, monkeypatch):
    """
    New project files contain expected content.
    """
    monkeypatch.chdir(tmp_path)

    args = MagicMock()
    args.project_name = "testproject"
    args.version = "2025.1.1"
    args.offline = False

    new(args)

    project_path = tmp_path / "testproject"

    # Check main.py.
    main_content = (project_path / "main.py").read_text(encoding="utf-8")
    assert main_content == 'print("Hello, World!")\n'

    # Check settings.json.
    settings_content = (project_path / "settings.json").read_text(
        encoding="utf-8"
    )
    assert settings_content == "{}\n"

    # Check style.css has basic structure.
    style_content = (project_path / "style.css").read_text(encoding="utf-8")
    assert "prefers-color-scheme: dark" in style_content
    assert "background-color" in style_content

    # Check index.html structure.
    html_content = (project_path / "index.html").read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in html_content
    assert '<script type="mpy" src="./main.py"' in html_content
    assert 'config="./settings.json"' in html_content
    assert "terminal" in html_content


def test_new_creates_gitignore(tmp_path, monkeypatch):
    """
    New project includes .gitignore with security files.
    """
    monkeypatch.chdir(tmp_path)

    args = MagicMock()
    args.project_name = "testproject"
    args.version = "2025.1.1"
    args.offline = False

    new(args)

    project_path = tmp_path / "testproject"
    gitignore_path = project_path / ".gitignore"

    # Check .gitignore exists.
    assert gitignore_path.exists()

    # Check .gitignore content.
    gitignore_content = gitignore_path.read_text(encoding="utf-8")
    assert "config.json" in gitignore_content
    assert "*.pem" in gitignore_content
    assert "__pycache__/" in gitignore_content


@patch("thub.cache.download_offline_version")
@patch("thub.cache.get_cached_version")
def test_new_offline_with_version(
    mock_get_cached, mock_download, tmp_path, monkeypatch
):
    """
    New project with --offline flag and specific version.
    """
    monkeypatch.chdir(tmp_path)

    # Mock cache functions.
    mock_pyscript_dir = tmp_path / "cache" / "2025.12.1" / "pyscript"
    mock_pyscript_dir.mkdir(parents=True)
    (mock_pyscript_dir / "core.js").write_text("// core.js")
    (mock_pyscript_dir / "core.css").write_text("/* core.css */")

    mock_get_cached.return_value = None  # Not cached yet.
    mock_download.return_value = mock_pyscript_dir

    args = MagicMock()
    args.project_name = "testproject"
    args.version = "2025.12.1"
    args.offline = True

    new(args)

    project_path = tmp_path / "testproject"

    # Check project was created.
    assert project_path.exists()

    # Check pyscript directory was copied.
    pyscript_dir = project_path / "pyscript"
    assert pyscript_dir.exists()
    assert (pyscript_dir / "core.js").exists()
    assert (pyscript_dir / "core.css").exists()

    # Check HTML uses offline template.
    html_content = (project_path / "index.html").read_text(encoding="utf-8")
    assert 'src="./pyscript/core.js"' in html_content
    assert 'href="./pyscript/core.css"' in html_content
    assert "offline" in html_content

    # Verify download was called.
    mock_download.assert_called_once_with("2025.12.1")


@patch("thub.cache.get_cached_version")
def test_new_offline_reuses_cache(mock_get_cached, tmp_path, monkeypatch):
    """
    New project with --offline flag reuses cached version.
    """
    monkeypatch.chdir(tmp_path)

    # Mock cached version exists.
    mock_pyscript_dir = tmp_path / "cache" / "2025.12.1" / "pyscript"
    mock_pyscript_dir.mkdir(parents=True)
    (mock_pyscript_dir / "core.js").write_text("// core.js")
    (mock_pyscript_dir / "core.css").write_text("/* core.css */")

    mock_get_cached.return_value = mock_pyscript_dir

    args = MagicMock()
    args.project_name = "testproject"
    args.version = "2025.12.1"
    args.offline = True

    new(args)

    project_path = tmp_path / "testproject"

    # Check pyscript directory was copied from cache.
    pyscript_dir = project_path / "pyscript"
    assert pyscript_dir.exists()
    assert (pyscript_dir / "core.js").exists()

    # Verify cache was checked.
    mock_get_cached.assert_called_once_with("2025.12.1")


@patch("thub.cache.download_offline_version")
@patch("thub.cache.get_cached_version")
@patch("thub.cache.get_latest_cached_version")
def test_new_offline_fallback_to_cached(
    mock_get_latest, mock_get_cached, mock_download, tmp_path, monkeypatch
):
    """
    New project falls back to latest cached version when download fails.
    """
    monkeypatch.chdir(tmp_path)

    # Mock download failure.
    mock_get_cached.return_value = None
    mock_download.side_effect = Exception("Network error")

    # Mock latest cached version.
    mock_pyscript_dir = tmp_path / "cache" / "2024.11.1" / "pyscript"
    mock_pyscript_dir.mkdir(parents=True)
    (mock_pyscript_dir / "core.js").write_text("// core.js")
    (mock_pyscript_dir / "core.css").write_text("/* core.css */")

    mock_get_latest.return_value = mock_pyscript_dir

    args = MagicMock()
    args.project_name = "testproject"
    args.version = "2025.12.1"
    args.offline = True

    new(args)

    project_path = tmp_path / "testproject"

    # Check project was created with cached version.
    pyscript_dir = project_path / "pyscript"
    assert pyscript_dir.exists()

    # Verify fallback was used.
    mock_get_latest.assert_called_once()


@patch("thub.cache.download_offline_version")
@patch("thub.cache.get_cached_version")
@patch("thub.cache.get_latest_cached_version")
def test_new_offline_fails_no_cache_no_network(
    mock_get_latest, mock_get_cached, mock_download, tmp_path, monkeypatch
):
    """
    New project fails gracefully when offline and no cache available.
    """
    monkeypatch.chdir(tmp_path)

    # Mock download failure and no cache.
    mock_get_cached.return_value = None
    mock_download.side_effect = Exception("Network error")
    mock_get_latest.return_value = None

    args = MagicMock()
    args.project_name = "testproject"
    args.version = "2025.12.1"
    args.offline = True

    new(args)

    project_path = tmp_path / "testproject"

    # Check project directory was not created (cleaned up).
    assert not project_path.exists()


def test_new_online_mode_unchanged(tmp_path, monkeypatch):
    """
    New project without --offline flag behaves as before.
    """
    monkeypatch.chdir(tmp_path)

    args = MagicMock()
    args.project_name = "testproject"
    args.version = "2025.1.1"
    args.offline = False

    new(args)

    project_path = tmp_path / "testproject"

    # Check project was created.
    assert project_path.exists()

    # Check pyscript directory was NOT created.
    pyscript_dir = project_path / "pyscript"
    assert not pyscript_dir.exists()

    # Check HTML uses online CDN.
    html_content = (project_path / "index.html").read_text(encoding="utf-8")
    assert "pyscript.net" in html_content
    assert "2025.1.1" in html_content

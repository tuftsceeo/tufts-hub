"""
Tests for cache management.
"""

import shutil
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from thub.cache import (
    copy_pyscript_to_project,
    download_offline_version,
    get_cache_dir,
    get_cached_version,
    get_latest_cached_version,
    get_offline_url,
    list_cached_versions,
)


def test_get_cache_dir_creates_directory(tmp_path, monkeypatch):
    """
    Cache directory is created if it doesn't exist.
    """
    # Mock platformdirs to use tmp_path.
    mock_cache_dir = tmp_path / "cache"
    monkeypatch.setattr(
        "thub.cache.user_cache_dir",
        lambda *args, **kwargs: str(mock_cache_dir),
    )

    cache_dir = get_cache_dir()

    assert cache_dir == mock_cache_dir / "pyscript"
    assert cache_dir.exists()
    assert cache_dir.is_dir()


def test_get_offline_url():
    """
    Offline URL is correctly formatted.
    """
    url = get_offline_url("2025.12.1")

    assert (
        url == "https://pyscript.net/releases/2025.12.1/offline_2025.12.1.zip"
    )


def test_get_cached_version_exists(tmp_path, monkeypatch):
    """
    Returns path when version is cached and valid.
    """
    # Mock cache dir.
    mock_cache_dir = tmp_path / "cache" / "pyscript"
    monkeypatch.setattr(
        "thub.cache.user_cache_dir",
        lambda *args, **kwargs: str(tmp_path / "cache"),
    )

    # Create fake cached version.
    version_dir = mock_cache_dir / "2025.12.1" / "pyscript"
    version_dir.mkdir(parents=True)
    (version_dir / "core.js").write_text("// core.js")
    (version_dir / "core.css").write_text("/* core.css */")

    result = get_cached_version("2025.12.1")

    assert result == version_dir


def test_get_cached_version_missing(tmp_path, monkeypatch):
    """
    Returns None when version is not cached.
    """
    # Mock cache dir.
    mock_cache_dir = tmp_path / "cache" / "pyscript"
    monkeypatch.setattr(
        "thub.cache.user_cache_dir",
        lambda *args, **kwargs: str(tmp_path / "cache"),
    )

    result = get_cached_version("2025.12.1")

    assert result is None


def test_get_cached_version_incomplete(tmp_path, monkeypatch):
    """
    Returns None when cached version is incomplete (missing core files).
    """
    # Mock cache dir.
    mock_cache_dir = tmp_path / "cache" / "pyscript"
    monkeypatch.setattr(
        "thub.cache.user_cache_dir",
        lambda *args, **kwargs: str(tmp_path / "cache"),
    )

    # Create incomplete cached version (missing core.css).
    version_dir = mock_cache_dir / "2025.12.1" / "pyscript"
    version_dir.mkdir(parents=True)
    (version_dir / "core.js").write_text("// core.js")

    result = get_cached_version("2025.12.1")

    assert result is None


def test_list_cached_versions(tmp_path, monkeypatch):
    """
    Lists all valid cached versions sorted newest first.
    """
    # Mock cache dir.
    mock_cache_dir = tmp_path / "cache" / "pyscript"
    monkeypatch.setattr(
        "thub.cache.user_cache_dir",
        lambda *args, **kwargs: str(tmp_path / "cache"),
    )

    # Create multiple cached versions.
    for version in ["2025.12.1", "2024.11.2", "2025.10.1"]:
        version_dir = mock_cache_dir / version / "pyscript"
        version_dir.mkdir(parents=True)
        (version_dir / "core.js").write_text("// core.js")
        (version_dir / "core.css").write_text("/* core.css */")

    versions = list_cached_versions()

    # Should be sorted newest first.
    assert versions == ["2025.12.1", "2025.10.1", "2024.11.2"]


def test_list_cached_versions_empty(tmp_path, monkeypatch):
    """
    Returns empty list when no versions are cached.
    """
    # Mock cache dir.
    mock_cache_dir = tmp_path / "cache" / "pyscript"
    monkeypatch.setattr(
        "thub.cache.user_cache_dir",
        lambda *args, **kwargs: str(tmp_path / "cache"),
    )

    versions = list_cached_versions()

    assert versions == []


def test_get_latest_cached_version(tmp_path, monkeypatch):
    """
    Returns path to the latest cached version.
    """
    # Mock cache dir.
    mock_cache_dir = tmp_path / "cache" / "pyscript"
    monkeypatch.setattr(
        "thub.cache.user_cache_dir",
        lambda *args, **kwargs: str(tmp_path / "cache"),
    )

    # Create multiple cached versions.
    for version in ["2025.12.1", "2024.11.2"]:
        version_dir = mock_cache_dir / version / "pyscript"
        version_dir.mkdir(parents=True)
        (version_dir / "core.js").write_text("// core.js")
        (version_dir / "core.css").write_text("/* core.css */")

    result = get_latest_cached_version()

    # Should return the latest (2025.12.1).
    assert result == mock_cache_dir / "2025.12.1" / "pyscript"


def test_get_latest_cached_version_none(tmp_path, monkeypatch):
    """
    Returns None when no versions are cached.
    """
    # Mock cache dir.
    mock_cache_dir = tmp_path / "cache" / "pyscript"
    monkeypatch.setattr(
        "thub.cache.user_cache_dir",
        lambda *args, **kwargs: str(tmp_path / "cache"),
    )

    result = get_latest_cached_version()

    assert result is None


@patch("thub.cache.httpx.stream")
def test_download_offline_version_success(mock_stream, tmp_path, monkeypatch):
    """
    Downloads and extracts PyScript offline version successfully.
    """
    # Mock cache dir.
    mock_cache_dir = tmp_path / "cache" / "pyscript"
    monkeypatch.setattr(
        "thub.cache.user_cache_dir",
        lambda *args, **kwargs: str(tmp_path / "cache"),
    )

    # Create a fake zip file with proper directory structure.
    # The zip should contain: offline_2025.12.1/pyscript/core.js etc.
    zip_content_dir = tmp_path / "zip_content"
    offline_dir = zip_content_dir / "offline_2025.12.1"
    pyscript_dir = offline_dir / "pyscript"
    pyscript_dir.mkdir(parents=True)
    (pyscript_dir / "core.js").write_text("// core.js content")
    (pyscript_dir / "core.css").write_text("/* core.css content */")
    (pyscript_dir / "worker.js").write_text("// worker.js content")

    zip_path = tmp_path / "test.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(
            pyscript_dir / "core.js", "offline_2025.12.1/pyscript/core.js"
        )
        zf.write(
            pyscript_dir / "core.css", "offline_2025.12.1/pyscript/core.css"
        )
        zf.write(
            pyscript_dir / "worker.js",
            "offline_2025.12.1/pyscript/worker.js",
        )

    # Mock HTTP response.
    mock_response = MagicMock()
    mock_response.headers = {"content-length": str(zip_path.stat().st_size)}
    mock_response.iter_bytes = lambda chunk_size: [zip_path.read_bytes()]
    mock_response.raise_for_status = MagicMock()

    mock_context = MagicMock()
    mock_context.__enter__ = MagicMock(return_value=mock_response)
    mock_context.__exit__ = MagicMock(return_value=None)
    mock_stream.return_value = mock_context

    result = download_offline_version("2025.12.1")

    # Verify the files were extracted.
    assert result == mock_cache_dir / "2025.12.1" / "pyscript"
    assert (result / "core.js").exists()
    assert (result / "core.css").exists()
    assert (result / "worker.js").exists()
    assert (result / "core.js").read_text() == "// core.js content"


@patch("thub.cache.httpx.stream")
def test_download_offline_version_http_error(
    mock_stream, tmp_path, monkeypatch
):
    """
    Raises exception and cleans up on HTTP error.
    """
    # Mock cache dir.
    mock_cache_dir = tmp_path / "cache" / "pyscript"
    monkeypatch.setattr(
        "thub.cache.user_cache_dir",
        lambda *args, **kwargs: str(tmp_path / "cache"),
    )

    # Mock HTTP error.
    mock_stream.side_effect = httpx.HTTPStatusError(
        "404 Not Found", request=MagicMock(), response=MagicMock()
    )

    with pytest.raises(httpx.HTTPStatusError):
        download_offline_version("2025.12.1")

    # Verify cleanup happened.
    version_dir = mock_cache_dir / "2025.12.1"
    assert not version_dir.exists()


def test_copy_pyscript_to_project(tmp_path):
    """
    Copies pyscript directory to project directory.
    """
    # Create source pyscript directory.
    source_dir = tmp_path / "source" / "pyscript"
    source_dir.mkdir(parents=True)
    (source_dir / "core.js").write_text("// core.js")
    (source_dir / "core.css").write_text("/* core.css */")
    (source_dir / "other.txt").write_text("other file")

    # Create project directory.
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    copy_pyscript_to_project(source_dir, project_dir)

    # Verify files were copied.
    dest_dir = project_dir / "pyscript"
    assert dest_dir.exists()
    assert (dest_dir / "core.js").read_text() == "// core.js"
    assert (dest_dir / "core.css").read_text() == "/* core.css */"
    assert (dest_dir / "other.txt").read_text() == "other file"


def test_copy_pyscript_to_project_overwrites(tmp_path):
    """
    Overwrites existing pyscript directory in project.
    """
    # Create source pyscript directory.
    source_dir = tmp_path / "source" / "pyscript"
    source_dir.mkdir(parents=True)
    (source_dir / "core.js").write_text("// new core.js")

    # Create project directory with existing pyscript.
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    old_pyscript = project_dir / "pyscript"
    old_pyscript.mkdir()
    (old_pyscript / "core.js").write_text("// old core.js")
    (old_pyscript / "old.txt").write_text("old file")

    copy_pyscript_to_project(source_dir, project_dir)

    # Verify old content was replaced.
    dest_dir = project_dir / "pyscript"
    assert (dest_dir / "core.js").read_text() == "// new core.js"
    assert not (dest_dir / "old.txt").exists()


def test_parse_version():
    """
    Version parsing works correctly.
    """
    from thub.cache import parse_version

    assert parse_version("2025.12.1") == (2025, 12, 1)
    assert parse_version("2024.11.2") == (2024, 11, 2)
    assert parse_version("2025.1.10") == (2025, 1, 10)


def test_parse_version_invalid():
    """
    Invalid version format raises ValueError.
    """
    from thub.cache import parse_version

    with pytest.raises(ValueError):
        parse_version("invalid")

    with pytest.raises(ValueError):
        parse_version("2025.12")


def test_is_version_supported():
    """
    Version support check works correctly.
    """
    from thub.cache import is_version_supported

    # Supported versions (>= 2025.11.2).
    assert is_version_supported("2025.11.2") is True
    assert is_version_supported("2025.12.1") is True
    assert is_version_supported("2026.1.1") is True

    # Unsupported versions (< 2025.11.2).
    assert is_version_supported("2025.11.1") is False
    assert is_version_supported("2024.12.1") is False
    assert is_version_supported("2025.10.5") is False

    # Invalid versions.
    assert is_version_supported("invalid") is False


def test_get_offline_url_2025_11_2():
    """
    Special case: version 2025.11.2 uses offline.zip.
    """
    url = get_offline_url("2025.11.2")

    assert url == "https://pyscript.net/releases/2025.11.2/offline.zip"


def test_get_offline_url_other_versions():
    """
    Other versions use offline_{version}.zip.
    """
    url = get_offline_url("2025.12.1")
    assert (
        url == "https://pyscript.net/releases/2025.12.1/offline_2025.12.1.zip"
    )

    url = get_offline_url("2026.1.1")
    assert url == "https://pyscript.net/releases/2026.1.1/offline_2026.1.1.zip"


def test_download_offline_version_unsupported_version(tmp_path, monkeypatch):
    """
    Downloading unsupported version raises ValueError.
    """
    # Mock cache dir.
    mock_cache_dir = tmp_path / "cache" / "pyscript"
    monkeypatch.setattr(
        "thub.cache.user_cache_dir",
        lambda *args, **kwargs: str(tmp_path / "cache"),
    )

    with pytest.raises(ValueError) as exc_info:
        download_offline_version("2025.11.1")

    assert "does not support offline assets" in str(exc_info.value)
    assert "2025.11.2 or later" in str(exc_info.value)

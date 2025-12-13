"""
Tests for server lifecycle management.
"""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from thub.server import (
    find_ssl_certificates,
    run_server,
    start_server,
    stop_server,
)


def test_find_ssl_certificates_found(tmp_path, monkeypatch):
    """
    SSL certificates are found when .pem files exist.
    """
    monkeypatch.chdir(tmp_path)

    # Create mock certificate files.
    key_file = tmp_path / "server-key.pem"
    cert_file = tmp_path / "server-cert.pem"
    key_file.write_text("mock key")
    cert_file.write_text("mock cert")

    ssl_keyfile, ssl_certfile = find_ssl_certificates()

    assert ssl_keyfile == str(key_file)
    assert ssl_certfile == str(cert_file)


def test_find_ssl_certificates_not_found(tmp_path, monkeypatch):
    """
    Returns None, None when no .pem files exist.
    """
    monkeypatch.chdir(tmp_path)

    ssl_keyfile, ssl_certfile = find_ssl_certificates()

    assert ssl_keyfile is None
    assert ssl_certfile is None


def test_find_ssl_certificates_custom_directory(tmp_path):
    """
    Can search custom directory for certificates.
    """
    # Create certificate files in custom directory.
    cert_dir = tmp_path / "certs"
    cert_dir.mkdir()

    key_file = cert_dir / "my-key.pem"
    cert_file = cert_dir / "my-cert.pem"
    key_file.write_text("mock key")
    cert_file.write_text("mock cert")

    ssl_keyfile, ssl_certfile = find_ssl_certificates(directory=cert_dir)

    assert ssl_keyfile == str(key_file)
    assert ssl_certfile == str(cert_file)


def test_find_ssl_certificates_incomplete(tmp_path, monkeypatch):
    """
    Returns None, None when only one .pem file exists.
    """
    monkeypatch.chdir(tmp_path)

    # Create only key file.
    key_file = tmp_path / "server-key.pem"
    key_file.write_text("mock key")

    ssl_keyfile, ssl_certfile = find_ssl_certificates()

    assert ssl_keyfile is None
    assert ssl_certfile is None


def test_start_server_no_config(tmp_path, monkeypatch):
    """
    Starting server without config.json raises FileNotFoundError.
    """
    monkeypatch.chdir(tmp_path)

    with pytest.raises(FileNotFoundError) as exc_info:
        start_server(block=True)

    assert "config.json not found" in str(exc_info.value)


def test_start_server_invalid_config(tmp_path, monkeypatch):
    """
    Starting server with invalid config.json raises ValueError.
    """
    monkeypatch.chdir(tmp_path)

    # Create invalid config.
    config_path = tmp_path / "config.json"
    config_path.write_text("invalid json")

    with pytest.raises(ValueError) as exc_info:
        start_server(block=True)

    assert "Invalid config.json" in str(exc_info.value)


@patch("thub.server.uvicorn.run")
def test_start_server_blocking_mode(mock_uvicorn_run, tmp_path, monkeypatch):
    """
    Blocking mode calls uvicorn.run directly.
    """
    monkeypatch.chdir(tmp_path)

    # Create valid config.
    config_path = tmp_path / "config.json"
    config = {
        "users": {},
        "proxies": {},
        "jwt": {"secret": "test_secret", "expiry_hours": 24},
    }
    config_path.write_text(json.dumps(config))

    result = start_server(
        host="0.0.0.0",
        port=9000,
        reload=True,
        block=True,
    )

    # Should return None in blocking mode.
    assert result is None

    # Should have called uvicorn.run.
    mock_uvicorn_run.assert_called_once()
    call_kwargs = mock_uvicorn_run.call_args[1]

    assert call_kwargs["host"] == "0.0.0.0"
    assert call_kwargs["port"] == 9000
    assert call_kwargs["reload"] is True


@patch("thub.server.subprocess.Popen")
def test_start_server_nonblocking_mode(mock_popen, tmp_path, monkeypatch):
    """
    Non-blocking mode starts server in subprocess.
    """
    monkeypatch.chdir(tmp_path)

    # Create valid config.
    config_path = tmp_path / "config.json"
    config = {
        "users": {},
        "proxies": {},
        "jwt": {"secret": "test_secret", "expiry_hours": 24},
    }
    config_path.write_text(json.dumps(config))

    # Mock process.
    mock_process = MagicMock()
    mock_process.poll.return_value = None  # Still running.
    mock_popen.return_value = mock_process

    result = start_server(
        host="127.0.0.1",
        port=8000,
        reload=False,
        block=False,
    )

    # Should return process object.
    assert result == mock_process

    # Should have started subprocess.
    mock_popen.assert_called_once()
    call_args = mock_popen.call_args[0][0]

    assert "uvicorn" in " ".join(call_args)
    assert "--host" in call_args
    assert "127.0.0.1" in call_args
    assert "--port" in call_args
    assert "8000" in call_args


@patch("thub.server.subprocess.Popen")
def test_start_server_nonblocking_with_ssl(mock_popen, tmp_path, monkeypatch):
    """
    Non-blocking mode includes SSL args when provided.
    """
    monkeypatch.chdir(tmp_path)

    # Create valid config.
    config_path = tmp_path / "config.json"
    config = {
        "users": {},
        "proxies": {},
        "jwt": {"secret": "test_secret", "expiry_hours": 24},
    }
    config_path.write_text(json.dumps(config))

    # Mock process.
    mock_process = MagicMock()
    mock_process.poll.return_value = None
    mock_popen.return_value = mock_process

    start_server(
        host="127.0.0.1",
        port=8000,
        ssl_keyfile="/path/to/key.pem",
        ssl_certfile="/path/to/cert.pem",
        block=False,
    )

    call_args = mock_popen.call_args[0][0]

    assert "--ssl-keyfile" in call_args
    assert "/path/to/key.pem" in call_args
    assert "--ssl-certfile" in call_args
    assert "/path/to/cert.pem" in call_args


@patch("thub.server.subprocess.Popen")
def test_start_server_nonblocking_with_reload(
    mock_popen, tmp_path, monkeypatch
):
    """
    Non-blocking mode includes --reload flag when enabled.
    """
    monkeypatch.chdir(tmp_path)

    # Create valid config.
    config_path = tmp_path / "config.json"
    config = {
        "users": {},
        "proxies": {},
        "jwt": {"secret": "test_secret", "expiry_hours": 24},
    }
    config_path.write_text(json.dumps(config))

    # Mock process.
    mock_process = MagicMock()
    mock_process.poll.return_value = None
    mock_popen.return_value = mock_process

    start_server(
        host="127.0.0.1",
        port=8000,
        reload=True,
        block=False,
    )

    call_args = mock_popen.call_args[0][0]

    assert "--reload" in call_args


@patch("thub.server.subprocess.Popen")
def test_start_server_subprocess_failure(mock_popen, tmp_path, monkeypatch):
    """
    Raises RuntimeError if subprocess fails to start.
    """
    monkeypatch.chdir(tmp_path)

    # Create valid config.
    config_path = tmp_path / "config.json"
    config = {
        "users": {},
        "proxies": {},
        "jwt": {"secret": "test_secret", "expiry_hours": 24},
    }
    config_path.write_text(json.dumps(config))

    # Mock process that fails immediately.
    mock_process = MagicMock()
    mock_process.poll.return_value = 1  # Exited with error.
    mock_process.communicate.return_value = (b"", b"Error starting server")
    mock_popen.return_value = mock_process

    with pytest.raises(RuntimeError) as exc_info:
        start_server(block=False)

    assert "Server failed to start" in str(exc_info.value)


def test_stop_server_graceful():
    """
    Stop server attempts graceful shutdown first.
    """
    mock_process = MagicMock()
    mock_process.poll.return_value = None  # Still running.
    mock_process.wait.return_value = None  # Stops gracefully.

    stop_server(mock_process, timeout=5)

    # Should call terminate first.
    mock_process.terminate.assert_called_once()
    mock_process.wait.assert_called_once_with(timeout=5)

    # Should not force kill.
    mock_process.kill.assert_not_called()


def test_stop_server_force_kill():
    """
    Stop server force-kills if graceful shutdown times out.
    """
    mock_process = MagicMock()
    mock_process.poll.return_value = None  # Still running.
    mock_process.wait.side_effect = [
        subprocess.TimeoutExpired("cmd", 5),
        None,
    ]

    stop_server(mock_process, timeout=5)

    # Should attempt graceful shutdown.
    mock_process.terminate.assert_called_once()

    # Should force kill after timeout.
    mock_process.kill.assert_called_once()

    # Should wait again after kill.
    assert mock_process.wait.call_count == 2


def test_stop_server_already_stopped():
    """
    Stop server handles already-stopped process gracefully.
    """
    mock_process = MagicMock()
    mock_process.poll.return_value = 0  # Already stopped.

    stop_server(mock_process)

    # Should not try to terminate or kill.
    mock_process.terminate.assert_not_called()
    mock_process.kill.assert_not_called()


@patch("thub.server.start_server")
@patch("thub.server.stop_server")
def test_run_server_context_manager(
    mock_stop, mock_start, tmp_path, monkeypatch
):
    """
    Context manager starts and stops server automatically.
    """
    monkeypatch.chdir(tmp_path)

    # Mock process.
    mock_process = MagicMock()
    mock_start.return_value = mock_process

    with run_server(host="127.0.0.1", port=8000) as server:
        # Server should be running.
        assert server == mock_process

    # Should have started with block=False.
    mock_start.assert_called_once()
    assert mock_start.call_args[1]["block"] is False

    # Should have stopped after context exit.
    mock_stop.assert_called_once_with(mock_process)


@patch("thub.server.start_server")
@patch("thub.server.stop_server")
def test_run_server_context_manager_with_exception(
    mock_stop, mock_start, tmp_path, monkeypatch
):
    """
    Context manager stops server even if exception occurs.
    """
    monkeypatch.chdir(tmp_path)

    # Mock process.
    mock_process = MagicMock()
    mock_start.return_value = mock_process

    with pytest.raises(ValueError):
        with run_server() as server:
            raise ValueError("Test error")

    # Should still stop server despite exception.
    mock_stop.assert_called_once_with(mock_process)

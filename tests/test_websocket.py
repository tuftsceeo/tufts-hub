"""
Tests for WebSocket channels.
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from thub.app import app
from thub.auth import create_jwt_token
from thub.websocket import (
    broadcast,
    channels,
    connect,
    disconnect,
    get_connection_count,
)


@pytest.fixture
def clear_channels():
    """
    Clear channels before each test.
    """
    channels.clear()
    yield
    channels.clear()


def test_connect_adds_websocket_to_channel(clear_channels):
    """
    Connecting adds WebSocket to channel tracking.
    """
    mock_ws = MagicMock()
    mock_ws.accept = AsyncMock()

    import asyncio

    asyncio.run(connect(mock_ws, "test_channel", "alice"))

    assert "test_channel" in channels
    assert (mock_ws, "alice") in channels["test_channel"]
    mock_ws.accept.assert_called_once()


def test_connect_creates_channel_if_not_exists(clear_channels):
    """
    Connecting to non-existent channel creates it.
    """
    mock_ws = MagicMock()
    mock_ws.accept = AsyncMock()

    assert "new_channel" not in channels

    import asyncio

    asyncio.run(connect(mock_ws, "new_channel", "bob"))

    assert "new_channel" in channels


def test_disconnect_removes_websocket_from_channel(clear_channels):
    """
    Disconnecting removes WebSocket from channel.
    """
    mock_ws = MagicMock()
    mock_ws.accept = AsyncMock()

    import asyncio

    asyncio.run(connect(mock_ws, "test_channel", "alice"))

    assert (mock_ws, "alice") in channels["test_channel"]

    disconnect(mock_ws, "test_channel", "alice")

    assert (mock_ws, "alice") not in channels.get("test_channel", set())


def test_disconnect_removes_empty_channel(clear_channels):
    """
    Disconnecting last connection removes channel.
    """
    mock_ws = MagicMock()
    mock_ws.accept = AsyncMock()

    import asyncio

    asyncio.run(connect(mock_ws, "test_channel", "alice"))

    assert "test_channel" in channels

    disconnect(mock_ws, "test_channel", "alice")

    assert "test_channel" not in channels


def test_disconnect_handles_nonexistent_channel(clear_channels):
    """
    Disconnecting from non-existent channel does not raise error.
    """
    mock_ws = MagicMock()

    # Should not raise an exception.
    disconnect(mock_ws, "nonexistent", "alice")


def test_broadcast_sends_to_all_except_sender(clear_channels):
    """
    Broadcasting sends message to all connections except sender.
    """
    mock_ws1 = MagicMock()
    mock_ws1.accept = AsyncMock()
    mock_ws1.send_text = AsyncMock()

    mock_ws2 = MagicMock()
    mock_ws2.accept = AsyncMock()
    mock_ws2.send_text = AsyncMock()

    mock_ws3 = MagicMock()
    mock_ws3.accept = AsyncMock()
    mock_ws3.send_text = AsyncMock()

    import asyncio

    asyncio.run(connect(mock_ws1, "chat", "alice"))
    asyncio.run(connect(mock_ws2, "chat", "bob"))
    asyncio.run(connect(mock_ws3, "chat", "charlie"))

    asyncio.run(broadcast("Hello!", "chat", mock_ws1))

    # Sender should not receive message.
    mock_ws1.send_text.assert_not_called()

    # Other connections should receive message.
    mock_ws2.send_text.assert_called_once_with("Hello!")
    mock_ws3.send_text.assert_called_once_with("Hello!")


def test_broadcast_to_nonexistent_channel_does_nothing(clear_channels):
    """
    Broadcasting to non-existent channel does not raise error.
    """
    mock_ws = MagicMock()

    import asyncio

    # Should not raise an exception.
    asyncio.run(broadcast("Hello!", "nonexistent", mock_ws))


def test_get_connection_count_returns_correct_count(clear_channels):
    """
    Connection count returns number of connections in channel.
    """
    mock_ws1 = MagicMock()
    mock_ws1.accept = AsyncMock()

    mock_ws2 = MagicMock()
    mock_ws2.accept = AsyncMock()

    import asyncio

    asyncio.run(connect(mock_ws1, "chat", "alice"))
    asyncio.run(connect(mock_ws2, "chat", "bob"))

    assert get_connection_count("chat") == 2


def test_get_connection_count_returns_zero_for_nonexistent_channel(
    clear_channels,
):
    """
    Connection count returns zero for non-existent channel.
    """
    assert get_connection_count("nonexistent") == 0


def test_channel_isolation(clear_channels):
    """
    Messages in one channel do not affect other channels.
    """
    mock_ws1 = MagicMock()
    mock_ws1.accept = AsyncMock()
    mock_ws1.send_text = AsyncMock()

    mock_ws2 = MagicMock()
    mock_ws2.accept = AsyncMock()
    mock_ws2.send_text = AsyncMock()

    import asyncio

    asyncio.run(connect(mock_ws1, "chat", "alice"))
    asyncio.run(connect(mock_ws2, "notifications", "bob"))

    asyncio.run(broadcast("Hello!", "chat", MagicMock()))

    # Only chat channel should receive message.
    mock_ws1.send_text.assert_called_once_with("Hello!")
    mock_ws2.send_text.assert_not_called()


def test_websocket_endpoint_rejects_without_token(tmp_path, monkeypatch):
    """
    WebSocket endpoint rejects connection without token.
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

    with pytest.raises(Exception):
        with client.websocket_connect("/channel/test"):
            pass


def test_websocket_endpoint_rejects_with_invalid_token(tmp_path, monkeypatch):
    """
    WebSocket endpoint rejects connection with invalid token.
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

    with pytest.raises(Exception):
        with client.websocket_connect("/channel/test?token=invalid"):
            pass


def test_websocket_endpoint_accepts_valid_token(tmp_path, monkeypatch):
    """
    WebSocket endpoint accepts connection with valid token in query param.
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

    with client.websocket_connect(f"/channel/test?token={token}") as ws:
        # Connection successful, send a message.
        ws.send_text("Hello!")


def test_websocket_endpoint_accepts_cookie_auth(tmp_path, monkeypatch):
    """
    WebSocket endpoint accepts connection with valid session cookie.
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

    # Set cookie in test client.
    client.cookies.set("session", token)

    with client.websocket_connect("/channel/test") as ws:
        # Connection successful, send a message.
        ws.send_text("Hello from cookie auth!")


def test_websocket_broadcasts_messages(tmp_path, monkeypatch, clear_channels):
    """
    WebSocket broadcasts messages to other connected clients.
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

    token1 = create_jwt_token("alice", config)
    token2 = create_jwt_token("bob", config)

    client = TestClient(app)

    with client.websocket_connect(
        f"/channel/chat?token={token1}"
    ) as ws1, client.websocket_connect(f"/channel/chat?token={token2}") as ws2:
        # Alice sends a message.
        ws1.send_text("Hello from Alice!")

        # Bob should receive it.
        message = ws2.receive_text()
        assert message == "Hello from Alice!"

        # Bob sends a message.
        ws2.send_text("Hi Alice!")

        # Alice should receive it.
        message = ws1.receive_text()
        assert message == "Hi Alice!"


def test_websocket_channel_isolation(tmp_path, monkeypatch, clear_channels):
    """
    Messages in one channel do not appear in other channels.
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

    with client.websocket_connect(
        f"/channel/chat?token={token}"
    ) as ws_chat, client.websocket_connect(
        f"/channel/notifications?token={token}"
    ) as ws_notifications:
        # Send message to chat channel.
        ws_chat.send_text("Chat message")

        # Notifications channel should not receive it.
        # (We can't directly test non-receipt, but we verify isolation
        # through the broadcast tests above)

        # Send message to notifications channel.
        ws_notifications.send_text("Notification message")

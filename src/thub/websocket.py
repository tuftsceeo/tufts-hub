"""
WebSocket channel management for Tufts Hub.
"""

from typing import Dict, Set

from fastapi import WebSocket

from thub.logging import log_websocket_connect, log_websocket_disconnect


# Store active connections per channel.
# Structure: {channel_name: {(websocket, username), ...}}
channels: Dict[str, Set[tuple[WebSocket, str]]] = {}


async def connect(websocket: WebSocket, channel: str, username: str):
    """
    Add a WebSocket connection to a channel.
    """
    await websocket.accept()

    if channel not in channels:
        channels[channel] = set()

    channels[channel].add((websocket, username))
    log_websocket_connect(channel, username)


def disconnect(websocket: WebSocket, channel: str, username: str):
    """
    Remove a WebSocket connection from a channel.
    """
    if channel in channels:
        channels[channel].discard((websocket, username))

        # Clean up empty channels.
        if not channels[channel]:
            del channels[channel]

    log_websocket_disconnect(channel, username)


async def broadcast(message: str, channel: str, sender_websocket: WebSocket):
    """
    Broadcast a message to all connections in a channel except sender.
    """
    if channel not in channels:
        return

    # Send to all connections except the sender.
    for websocket, username in channels[channel]:
        if websocket != sender_websocket:
            await websocket.send_text(message)


def get_connection_count(channel: str) -> int:
    """
    Get the number of active connections in a channel.
    """
    if channel not in channels:
        return 0
    return len(channels[channel])

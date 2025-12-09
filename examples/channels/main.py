"""
WebSocket channels example for Tufts Hub.

Demonstrates real-time pub/sub messaging using WebSocket channels.
"""

from pyscript import WebSocket, when, web, window

# Global WebSocket connection.
ws = None
current_channel = None


def connect_to_channel(channel_name):
    """
    Connect to a WebSocket channel.
    """
    global ws, current_channel

    # Close existing connection if any.
    if ws:
        ws.close()

    # Build WebSocket URL (use wss:// for HTTPS, ws:// for HTTP).
    protocol = "wss" if window.location.protocol == "https:" else "ws"
    host = window.location.host
    url = f"{protocol}://{host}/channel/{channel_name}"

    # Create WebSocket connection.
    ws = WebSocket(url=url)
    ws.onopen = on_open
    ws.onmessage = on_message
    ws.onclose = on_close
    ws.onerror = on_error

    current_channel = channel_name


def on_open(event):
    """
    Handle WebSocket connection opened.
    """
    status = web.page.find("#status")[0]
    status.innerHTML = (
        f"Connected to channel: <strong>{current_channel}</strong>"
    )
    status.classes.remove("error")
    status.classes.add("connected")

    # Enable message input.
    web.page.find("#message-input")[0].disabled = False
    web.page.find("#send-button")[0].disabled = False


def on_message(event):
    """
    Handle incoming message from WebSocket.
    """
    # Create message element.
    message_div = web.div(
        web.span(event.data, className="message-text"),
        className="message received",
    )

    # Add to output.
    output = web.page.find("#output")[0]
    output.append(message_div)

    # Scroll to bottom.
    output._dom_element.scrollTop = output._dom_element.scrollHeight


def on_close(event):
    """
    Handle WebSocket connection closed.
    """
    status = web.page.find("#status")[0]
    status.innerHTML = "Disconnected"
    status.classes.remove("connected")
    status.classes.add("error")

    # Disable message input.
    web.page["message-input"].disabled = True
    web.page["send-button"].disabled = True


def on_error(event):
    """
    Handle WebSocket error.
    """
    status = web.page.find("#status")[0]
    status.innerHTML = "Connection error - please refresh and login"
    status.classes.remove("connected")
    status.classes.add("error")


@when("click", "#connect-button")
def handle_connect(event):
    """
    Handle connect button click.
    """
    channel_input = web.page.find("#channel-input")[0]
    channel_name = channel_input.value.strip()

    if not channel_name:
        status = web.page["status"]
        status.innerHTML = "Please enter a channel name"
        status.classes.add("error")
        return

    connect_to_channel(channel_name)


@when("click", "#send-button")
def handle_send(event):
    """
    Handle send button click.
    """
    message_input = web.page.find("#message-input")[0]
    message = message_input.value.strip()

    if not message:
        return

    # Send message to WebSocket.
    if ws:
        ws.send(message)

        # Display sent message in output.
        message_div = web.div(
            web.span(message, className="message-text"),
            className="message sent",
        )

        output = web.page.find("#output")[0]
        output.append(message_div)

        # Scroll to bottom.
        output._dom_element.scrollTop = output._dom_element.scrollHeight

        # Clear input.
        message_input.value = ""


@when("keydown", "#message-input")
def handle_keydown(event):
    """
    Handle Enter key in message input.
    """
    if event.key == "Enter" and not event.shiftKey:
        event.preventDefault()
        handle_send(event)


# Initialize on load.
print("WebSocket channels example loaded!")
print("Enter a channel name and click Connect to start.")

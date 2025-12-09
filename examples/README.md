# Tufts Hub Examples

This directory contains example applications demonstrating how to use Tufts Hub features with PyScript.

## WebSocket Channels (`/examples/channels`)

A real-time messaging application that demonstrates WebSocket pub/sub channels.

### Features

- Connect to any channel by name
- Send messages to all connected clients
- Receive messages in real-time
- Visual distinction between sent and received messages
- Responsive design with dark/light mode support

### How to Use

1. Start Tufts Hub from your project directory:
   ```bash
   cd /path/to/your/project
   thub serve
   ```

2. Login at `http://localhost:8000/login`

3. Navigate to `http://localhost:8000` (or wherever your examples are hosted)

4. Enter a channel name (e.g., "chat") and click Connect

5. Open the same page in another browser tab or window

6. Type messages and watch them appear instantly across all connected clients

### Technical Details

The example demonstrates:

- **WebSocket connection**: Using PyScript's `WebSocket` class with automatic cookie authentication
- **Event handling**: Using `@when` decorator for button clicks and keyboard events
- **DOM manipulation**: Creating and updating elements dynamically with `pyscript.web`
- **Real-time updates**: Automatic scrolling and message display
- **Error handling**: Connection status and error states

### Code Structure

- `main.py` - Python logic for WebSocket connection and message handling
- `index.html` - HTML structure with semantic markup
- `style.css` - Responsive CSS with dark/light mode theming
- `settings.json` - PyScript configuration (empty for this simple example)
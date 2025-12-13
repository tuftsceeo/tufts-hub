# Tufts Hub Examples

This directory contains example applications demonstrating how to use Tufts
Hub features with PyScript. **DO NOT USE THESE IN PRODUCTION.**

## WebSocket Channels (`/examples/channels`)

A real-time messaging application that demonstrates WebSocket pub/sub
channels. Log in using these credentials:

* Username: `test`
* Password: `password123`

### Features

* Connect to any channel by name
* Send messages to all connected clients
* Receive messages in real-time
* Visual distinction between sent and received messages
* Responsive design with dark/light mode support

### How to Use

1. Start Tufts Hub from inside the project's directory:
   ```bash
   cd example/channels
   thub serve
   ```

2. Use your browser to visit `http://localhost:8000/`. Sign in with the
   `test` / `password123` credentials.

3. Once signed in, click the "Continue" button to view the app.

4. Enter a channel name (e.g., "chat") and click Connect.

5. Sign in and open the same page in another browser tab or window.

6. Type messages and watch them appear instantly across all connected clients.

### Technical Details

The example demonstrates:

* **WebSocket connection**: Using PyScript's `WebSocket` class with automatic
  cookie authentication.
* **Event handling**: Using `@when` decorator for button clicks and keyboard
  events.
* **DOM manipulation**: Creating and updating elements dynamically with
  `pyscript.web`.
* **Real-time updates**: Automatic scrolling and message display.
* **Error handling**: Connection status and error states.


## Pokémon Proxy Explorer (`/examples/proxy`)

A playful Pokémon card viewer that demonstrates API proxy functionality. Log
in using these credentials:

* Username: `test`
* Password: `password123`

### Features

* Search for any Pokémon by name.
* Real-time request logging showing proxy API calls.
* Beautiful animated Pokémon cards with:
    * Official sprites (front and back views).
    * Type badges with emoji.
    * Pokémon cries (audio).
    * Physical stats (height, weight).
    * Battle stats with visual bars.
* Playful error messages for not-found Pokémon.
* Responsive design with fun, colourful theming.

### How to Use

1. Note the configuration of the PokéAPI proxy in the `config.json`:
   ```json
   {
     "proxies": {
       "pokeapi": {
         "base_url": "https://pokeapi.co/api/v2",
         "headers": {}
       }
     }
   }
   ```

2. Start Tufts Hub from inside the project's directory:
   ```bash
   cd example/proxy
   thub serve
   ```

3. Navigate to `http://localhost:8000/` and sign in / click "Continue", as in the
   previous example.

4. Enter a Pokémon name (try "pikachu", "charizard", or "mewtwo").

5. Watch the request log and see the Pokémon card appear!

### Technical Details

The example demonstrates:

* **API proxy usage**: Making authenticated requests through `/proxy/{api_name}/{path}`.
* **Request logging**: Displaying API calls in real-time.
* **Error handling**: 404 responses with friendly messages.
* **JSON data parsing**: Extracting and displaying structured API data.
* **Dynamic content**: Building complex UI elements from API responses.
* **Async operations**: Using `await` with `fetch` for API calls.
* **Multimedia**: Displaying images and playing audio.

### Why This Matters

This example shows how the proxy feature keeps API details server-side:

* No API keys exposed to the browser.
* Cleaner client code (just `/proxy/pokeapi/...`).
* Request logging for debugging.
* Consistent authentication handling.

## Programmatic Server Control (`/examples/server`)

Tufts Hub can be controlled programmatically from Python code, allowing
you to start and stop the server as part of automated workflows, testing,
or integration scripts.

The three examples in the `/examples/server` directory demonstrate some
idiomatic use cases, listed in order of increasing sophistication and
capability:

* `functional.py` - how to start and stop the Tufts Hub server
  programmatically using the `start_server()` and `stop_server()`
  functions.
* `context.py` - starting and stopping the Tufts Hub server using the
  `run_server()` context manager, which automatically handles cleanup
  even if errors occur.
* `realistic.py` - demonstrates a more realistic use case with
  `run_server()`: starting the server, making HTTP requests to it, then
  stopping it automatically when finished.

Technical details for the `thub.server` namespace (used to manage the
running of the server) can be found in the README.md in the root of this
project's repository. 
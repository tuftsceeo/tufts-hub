"""
Example: Advanced programmatic usage with HTTP requests.

This script demonstrates a more realistic use case: starting the server,
making HTTP requests to it, then stopping it.
"""

import time

import httpx

from thub.server import run_server


def main():
    """
    Start server, make HTTP requests, verify responses.
    """
    print("Starting Tufts Hub server...")

    with run_server(host="127.0.0.1", port=8000) as server:
        print(f"Server started! PID: {server.pid}")

        # Give server a moment to fully initialize.
        print("Waiting for server to initialize...")
        time.sleep(2)

        # Make HTTP requests to the server.
        base_url = "http://127.0.0.1:8000"

        print(f"\nMaking requests to {base_url}...")

        try:
            # Try accessing the login page.
            response = httpx.get(f"{base_url}/login", follow_redirects=True)
            print(f"  GET /login -> {response.status_code}")

            # Try accessing an example (will redirect to login).
            response = httpx.get(
                f"{base_url}/examples/test", follow_redirects=False
            )
            print(f"  GET /examples/test -> {response.status_code}")

            print("\n✓ Server is responding correctly!")

        except httpx.ConnectError:
            print("\n✗ Could not connect to server")

    print("\nServer stopped!")


if __name__ == "__main__":
    main()

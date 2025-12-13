"""
Example: Programmatic server control using functional API.

This script demonstrates starting and stopping the Tufts Hub server
programmatically using the start_server() and stop_server() functions.
"""

import time

from thub.server import start_server, stop_server


def main():
    """
    Start server, do some work, then stop it.
    """
    print("Starting Tufts Hub server...")

    # Start server in non-blocking mode (subprocess).
    server = start_server(
        host="127.0.0.1",
        port=8000,
        reload=False,  # Enable auto-reload during development.
        block=False,  # Don't block - returns immediately.
    )

    print("Server started!")
    print("Server is running in the background...")

    try:
        # Do your work here while server runs.
        print("\nDoing work for 10 seconds...")
        for i in range(10, 0, -1):
            print(f"  {i} seconds remaining...")
            time.sleep(1)

        print("\nWork complete!")

    finally:
        # Always stop the server when done.
        print("\nStopping server...")
        stop_server(server, timeout=5)
        print("Server stopped!")


if __name__ == "__main__":
    main()

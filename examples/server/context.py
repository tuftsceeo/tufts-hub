"""
Example: Programmatic server control using context manager.

This script demonstrates starting and stopping the Tufts Hub server
using the run_server() context manager, which automatically handles
cleanup even if errors occur.
"""

import time

from thub.server import run_server


def main():
    """
    Use context manager for automatic server lifecycle management.
    """
    print("Starting Tufts Hub server with context manager...")

    # Server automatically starts on entry and stops on exit.
    with run_server(host="127.0.0.1", port=8000, reload=False) as server:
        print("Server started!")
        print(f"Server process ID: {server.pid}")
        print("Server is running in the background...")

        # Do your work here while server runs.
        print("\nDoing work for 10 seconds...")
        for i in range(10, 0, -1):
            print(f"  {i} seconds remaining...")
            time.sleep(1)

        print("\nWork complete!")

    # Server automatically stopped here - even if exceptions occur!
    print("Server automatically stopped by context manager!")


def example_with_error_handling():
    """
    Demonstrate that context manager stops server even on errors.
    """
    print("\n" + "=" * 60)
    print("Example: Server cleanup with error handling")
    print("=" * 60)

    try:
        with run_server(host="127.0.0.1", port=8001) as server:
            print("Server started on port 8001")
            time.sleep(2)

            # Simulate an error occurring during work.
            print("Simulating an error...")
            raise ValueError("Something went wrong!")

    except ValueError as e:
        print(f"Caught error: {e}")
        print("Server was still stopped automatically!")


if __name__ == "__main__":
    # Run basic example.
    main()

    # Run error handling example.
    example_with_error_handling()

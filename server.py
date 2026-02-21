#!/usr/bin/env python3
"""
GenieGuard: Development Server
Simple HTTP server to serve the web simulator

Usage:
  python server.py          # Start server on port 8080
  python server.py --port 3000  # Start on custom port
"""

import http.server
import socketserver
import os
import sys
import webbrowser
from pathlib import Path


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Start GenieGuard development server')
    parser.add_argument('--port', type=int, default=1111, help='Port number (default: 1111)')
    parser.add_argument('--no-open', action='store_true', help="Don't open browser automatically")
    parser.add_argument('--dashboard', action='store_true', help='Open dashboard instead of simulator')

    args = parser.parse_args()

    # Change to web directory
    web_dir = Path(__file__).parent / 'web'
    os.chdir(web_dir)

    # Create handler
    handler = http.server.SimpleHTTPRequestHandler

    # Start server (try next ports if busy)
    socketserver.TCPServer.allow_reuse_address = True
    for port in range(args.port, args.port + 10):
        try:
            httpd = socketserver.TCPServer(("", port), handler)
            break
        except OSError:
            if port == args.port + 9:
                print(f"Error: ports {args.port}-{port} are all in use.")
                sys.exit(1)
            continue
    with httpd:
        url = f"http://localhost:{port}"
        page = "dashboard.html" if args.dashboard else "index.html"

        print(f"""
 GenieGuard Development Server
{'=' * 50}

  Simulator:  {url}/index.html
  Dashboard:  {url}/dashboard.html

{'=' * 50}
Press Ctrl+C to stop.
        """)

        if not args.no_open:
            webbrowser.open(f"{url}/{page}")

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n Server stopped.")


if __name__ == '__main__':
    main()

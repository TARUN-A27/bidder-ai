#!/usr/bin/env python3
"""Dependency-free same-origin host for BidGuard frontend development.

Serves repository static files and proxies /api/* to the local FastAPI
backend. This is development/demo infrastructure, not a production server.
"""

from __future__ import annotations

import argparse
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_BACKEND = "http://127.0.0.1:8000"
DEFAULT_ROOT = Path(__file__).resolve().parents[1]
FORWARDED_REQUEST_HEADERS = {"accept", "content-type"}
FORWARDED_RESPONSE_HEADERS = {"content-type", "content-length", "content-disposition"}


class BidGuardDevHandler(SimpleHTTPRequestHandler):
    backend_origin = DEFAULT_BACKEND

    def _is_api_request(self) -> bool:
        return self.path == "/api" or self.path.startswith("/api/")

    def _proxy_api(self) -> None:
        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length) if content_length else None
        headers = {
            name: value
            for name, value in self.headers.items()
            if name.lower() in FORWARDED_REQUEST_HEADERS
        }
        request = Request(
            f"{self.backend_origin}{self.path}",
            data=body,
            headers=headers,
            method=self.command,
        )
        try:
            with urlopen(request, timeout=900) as response:
                self._send_upstream(response.status, response.headers, response.read())
        except HTTPError as error:
            self._send_upstream(error.code, error.headers, error.read())
        except (URLError, TimeoutError):
            payload = json.dumps({"detail": "Backend service is unavailable"}).encode("utf-8")
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    def _send_upstream(self, status: int, headers, body: bytes) -> None:
        self.send_response(status)
        for name, value in headers.items():
            if name.lower() in FORWARDED_RESPONSE_HEADERS:
                self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        self._proxy_api() if self._is_api_request() else super().do_GET()

    def do_POST(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        if self._is_api_request():
            self._proxy_api()
        else:
            self.send_error(405, "POST is only supported for /api routes")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5500)
    parser.add_argument("--backend", default=DEFAULT_BACKEND)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = args.root.resolve()
    handler = lambda *handler_args, **kwargs: BidGuardDevHandler(  # noqa: E731
        *handler_args, directory=str(root), **kwargs
    )
    BidGuardDevHandler.backend_origin = args.backend.rstrip("/")
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"BidGuard frontend: http://{args.host}:{args.port}/dashboard.html", flush=True)
    print(f"Proxying /api/* to {BidGuardDevHandler.backend_origin}/api/*", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

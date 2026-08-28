"""Keeping operational authority in Python prevents browser state from becoming canonical."""
from __future__ import annotations

import argparse
import json
import logging
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Mapping, Optional
from urllib.parse import parse_qs, urlsplit

from aura_mas.operations.store import OperationalStore

log = logging.getLogger("aura.operations")


class OperationalApplication:
    def __init__(self, store: OperationalStore) -> None:
        self.store = store

    def handle(
        self, method: str, path: str, body: Optional[Mapping[str, Any]],
        query: Optional[Mapping[str, list[str]]] = None,
    ) -> tuple[int, dict[str, Any]]:
        body = dict(body or {})
        query = query or {}
        try:
            if method == "GET" and path == "/v1/state":
                return HTTPStatus.OK, self.store.snapshot()
            if method == "POST" and path == "/v1/policies":
                return HTTPStatus.CREATED, self.store.create_policy_version(
                    str(body.get("profile_name", "")), body.get("payload") or {},
                )
            if method == "POST" and path == "/v1/sessions":
                return HTTPStatus.CREATED, self.store.start_session(
                    str(body.get("mode", "")), str(body.get("policy_version_id", "")),
                    failure_reason=body.get("failure_reason"),
                    recording_id=body.get("recording_id"),
                    recording_checksum=body.get("recording_checksum"),
                    live_sources=body.get("live_sources"),
                )
            if method == "POST" and path.startswith("/v1/sessions/") and path.endswith("/end"):
                session_id = path.removeprefix("/v1/sessions/").removesuffix("/end").strip("/")
                return HTTPStatus.OK, self.store.end_session(
                    session_id, reason=str(body.get("reason", "")),
                )
            if method == "POST" and path == "/v1/observations":
                return HTTPStatus.CREATED, self.store.record_observation(
                    str(body.get("session_id", "")), body.get("observation") or {},
                )
            if method == "POST" and path == "/v1/verification-evidence":
                return HTTPStatus.CREATED, self.store.record_verification_evidence(
                    str(body.get("session_id", "")), body.get("evidence") or {},
                )
            if method == "POST" and path == "/v1/camera-health":
                return HTTPStatus.CREATED, self.store.record_camera_health(
                    str(body.get("session_id", "")), str(body.get("camera_id", "")),
                    body.get("physical_zone_id"), str(body.get("state", "")),
                    float(body.get("recorded_at", time.time())), reason=body.get("reason"),
                )
            if method == "POST" and path == "/v1/measurements":
                return HTTPStatus.CREATED, self.store.record_measurement(
                    str(body.get("session_id", "")), body.get("measurement") or {},
                )
            if method == "POST" and path.startswith("/v1/incidents/") and path.endswith("/actions"):
                incident_id = path.removeprefix("/v1/incidents/").removesuffix("/actions").strip("/")
                return HTTPStatus.OK, self.store.record_action(
                    incident_id, str(body.get("action", "")), str(body.get("actor", "operator")),
                    body.get("details") or {},
                )
            if method == "GET" and path == "/v1/search":
                return HTTPStatus.OK, self.store.search(
                    query.get("q", [""])[0], zone=query.get("zone", [None])[0],
                    verdict=query.get("verdict", [None])[0],
                )
            return HTTPStatus.NOT_FOUND, {"error": "not found"}
        except (ValueError, KeyError, TypeError) as error:
            return HTTPStatus.BAD_REQUEST, {"error": str(error)}


class OperationalHandler(BaseHTTPRequestHandler):
    server: "OperationalHTTPServer"

    def do_GET(self) -> None:
        parsed = urlsplit(self.path)
        if parsed.path == "/v1/events":
            self._stream_events()
            return
        self._respond(*self.server.application.handle(
            "GET", parsed.path, None, parse_qs(parsed.query),
        ))

    def do_POST(self) -> None:
        parsed = urlsplit(self.path)
        content_length = int(self.headers.get("Content-Length", "0"))
        try:
            body = json.loads(self.rfile.read(content_length) or b"{}")
        except json.JSONDecodeError:
            self._respond(HTTPStatus.BAD_REQUEST, {"error": "invalid JSON"})
            return
        self._respond(*self.server.application.handle("POST", parsed.path, body))

    def _respond(self, status: int, payload: Mapping[str, Any]) -> None:
        encoded = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)

    def _stream_events(self) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        try:
            while True:
                payload = json.dumps(self.server.application.store.snapshot(), separators=(",", ":"))
                self.wfile.write(f"event: state\ndata: {payload}\n\n".encode())
                self.wfile.flush()
                time.sleep(2)
        except (BrokenPipeError, ConnectionResetError):
            return

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        log.debug(format, *args)


class OperationalHTTPServer(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], application: OperationalApplication) -> None:
        self.application = application
        super().__init__(address, OperationalHandler)

    def service_actions(self) -> None:
        self.application.store.close_stale_evidence(time.time())


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the AURA-MAS operational API")
    parser.add_argument("--db", default="data/aura_operations.db")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8090)
    args = parser.parse_args()
    server = OperationalHTTPServer((args.host, args.port), OperationalApplication(OperationalStore(args.db)))
    log.info("operational API listening on http://%s:%d", args.host, args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

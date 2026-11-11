"""Local React host and JSON adapter, using Recoup only (design/02 §6).

Run: python -m recoup.ui.server --port 8501
"""

import argparse
import json
import mimetypes
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse
from uuid import uuid4

from recoup.app import RecoupConfig, build
from recoup.contracts.interfaces import GateError, TransientError
from recoup.ui.api import case_data, dashboard_data, mutate
from recoup.ui.reviewer import update_summary

DIST = Path(__file__).resolve().parent / "frontend/dist"
ROOT = Path(__file__).resolve().parents[2]


class UIHTTPServer(HTTPServer):
    def __init__(self, address, config: RecoupConfig):
        self.config = config
        super().__init__(address, UIHandler)


class UIHandler(BaseHTTPRequestHandler):
    server: UIHTTPServer

    def _json(self, data: dict, status: int = 200) -> None:
        content = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _api(self, path: str, payload: dict | None = None) -> None:
        config = self.server.config
        try:
            action = path.removeprefix("/api/")
            if payload is not None and action == "fresh":
                config = config.model_copy(
                    update={"db": str(ROOT / f"runs/simulation-{uuid4().hex}.db")}
                )
            elif payload is not None and action == "open_database":
                path_value = payload.get("database")
                if not isinstance(path_value, str) or not Path(path_value).is_file():
                    raise ValueError("Enter the path of an existing simulation database.")
                config = config.model_copy(update={"db": path_value})
            service = build(config)
            try:
                if payload is not None:
                    before = service.world.list_cases()
                    if action == "fresh":
                        mutate(service, "load", {})
                    elif action != "open_database":
                        mutate(service, action, payload)
                    result = {
                        "dashboard": dashboard_data(service),
                        "update": update_summary(before, service.world.list_cases()),
                    }
                    if case_id := payload.get("case_id"):
                        result["case"] = case_data(service, case_id)
                    # Switch only after a successful load/read; prior runs are preserved.
                    self.server.config = config
                elif path.startswith("/api/cases/"):
                    result = case_data(service, unquote(path.removeprefix("/api/cases/")))
                elif path == "/api/dashboard":
                    result = dashboard_data(service)
                else:
                    self._json({"error": "Unknown endpoint"}, 404)
                    return
                self._json(result)
            finally:
                service.world.close()
        except GateError as exc:
            self._json(
                {
                    "error": "Action needs review",
                    "issues": [row.model_dump() for row in exc.issues],
                },
                409,
            )
        except (ValueError, KeyError, LookupError, TypeError) as exc:
            self._json({"error": str(exc)}, 400)
        except (TransientError, OSError, sqlite3.Error) as exc:
            self._json({"error": str(exc)}, 503)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path.startswith("/api/"):
            self._api(path)
            return
        candidate = (DIST / unquote(path).lstrip("/")).resolve()
        if not candidate.is_relative_to(DIST.resolve()):
            self.send_error(404)
            return
        if not candidate.is_file():
            if path != "/":
                self.send_error(404)
                return
            candidate = DIST / "index.html"
        if not candidate.is_file():
            self._json(
                {"error": "Build the frontend first: npm --prefix recoup/ui/frontend run build"},
                503,
            )
            return
        content = candidate.read_bytes()
        self.send_response(200)
        self.send_header(
            "Content-Type", mimetypes.guess_type(candidate)[0] or "application/octet-stream"
        )
        self.send_header("Content-Length", str(len(content)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format, *args) -> None:
        # Old Streamlit tabs may still poll these retired endpoints after migration.
        if self.path.startswith("/_stcore/"):
            return
        super().log_message(format, *args)

    def do_POST(self) -> None:
        # This single-user host accepts JSON mutations from local UI origins only.
        origin = self.headers.get("Origin")
        if origin and urlparse(origin).hostname not in {"127.0.0.1", "localhost"}:
            self._json({"error": "Local UI origin required"}, 403)
            return
        if self.headers.get_content_type() != "application/json":
            self._json({"error": "JSON required"}, 415)
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size < 0 or size > 8 * 1024 * 1024:
                raise ValueError("Request exceeds the 8 MB limit.")
            payload = json.loads(self.rfile.read(size))
            if not isinstance(payload, dict):
                raise ValueError("Expected a JSON object.")
        except (ValueError, UnicodeDecodeError) as exc:
            self._json({"error": str(exc)}, 400)
            return
        self._api(urlparse(self.path).path, payload)


def main() -> None:
    parser = argparse.ArgumentParser(description="Recoup React + shadcn/ui workbench")
    parser.add_argument("--port", type=int, default=8501)
    parser.add_argument("--db", default="runs/your-demo.db")
    args = parser.parse_args()
    config = RecoupConfig.from_env().model_copy(update={"db": args.db})
    server = UIHTTPServer(("127.0.0.1", args.port), config)
    print(f"Recoup: http://127.0.0.1:{args.port} · LLM {config.llm} · SYNTHETIC / MOCK", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

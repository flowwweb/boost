"""Serve Boost's local control surface and its small local-first API."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = PLUGIN_ROOT / "assets"
DATA_ROOT = PLUGIN_ROOT / "data"
SCHEDULE_FILE = DATA_ROOT / "schedule.json"
CONFIG_FILE = PLUGIN_ROOT / "config.json"
EXAMPLE_CONFIG_FILE = PLUGIN_ROOT / "config.example.json"
MAX_BODY_BYTES = 256 * 1024
HANDLE_RE = re.compile(r"^@?[A-Za-z0-9_]{1,15}$")
DAY_KEYS = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}
ACTION_KEYS = {"post", "reply-others", "reply-own", "dm"}
CONNECTION_METHOD_KEYS = {"official-api", "browser"}
PLATFORM_KEYS = {"x", "linkedin", "instagram", "youtube", "threads"}
GENERIC_HANDLE_RE = re.compile(r"^\S{1,80}$")

parser = argparse.ArgumentParser()
parser.add_argument("--port", type=int, default=8765)
args = parser.parse_args()


def read_json(path: Path, fallback: dict) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else fallback
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return fallback


def write_json(path: Path, value: dict) -> None:
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.stem}.", suffix=".tmp", dir=DATA_ROOT)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def xurl_app() -> str | None:
    configured = read_json(CONFIG_FILE, read_json(EXAMPLE_CONFIG_FILE, {}))
    app = configured.get("xurl_app")
    return app if isinstance(app, str) and app.strip() else None


def xurl_status(handle: str | None) -> dict:
    """Return a privacy-safe auth probe; never returns xurl's raw output."""
    xurl = shutil.which("xurl")
    if not xurl:
        return {"provider": "x", "adapter": "xurl", "connected": False, "reason": "xurl is not installed"}
    try:
        command = [xurl]
        app = xurl_app()
        if app:
            command.extend(["--app", app])
        command.append("whoami")
        result = subprocess.run(command, capture_output=True, text=True, timeout=12, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return {"provider": "x", "adapter": "xurl", "connected": False, "reason": "xurl auth probe timed out"}
    if result.returncode != 0:
        return {"provider": "x", "adapter": "xurl", "connected": False, "reason": "X authorization required"}
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"provider": "x", "adapter": "xurl", "connected": False, "reason": "X returned an unreadable identity"}
    identity = payload.get("data", payload) if isinstance(payload, dict) else {}
    username = identity.get("username") if isinstance(identity, dict) else None
    normalized = (handle or "").lstrip("@").casefold()
    matched = isinstance(username, str) and (not normalized or username.casefold() == normalized)
    return {"provider": "x", "adapter": "xurl", "connected": matched, "reason": "Connected" if matched else "Authenticated account differs"}


def validate_schedule(payload: object) -> tuple[dict | None, str | None]:
    if not isinstance(payload, dict):
        return None, "schedule must be a JSON object"
    accounts = payload.get("accounts")
    cycles = payload.get("cycles")
    if not isinstance(accounts, list) or not isinstance(cycles, list):
        return None, "schedule must contain accounts and cycles lists"
    if len(accounts) > 100 or len(cycles) > 50:
        return None, "schedule is too large"
    for account in accounts:
        if not isinstance(account, dict) or not isinstance(account.get("id"), str) or not isinstance(account.get("cycles"), list):
            return None, "each account needs an id and cycles list"
        platform = account.get("provider", account.get("platform", "x"))
        if not isinstance(platform, str) or platform not in PLATFORM_KEYS:
            return None, "account platform is invalid"
        handle = account.get("handle", "")
        handle_pattern = HANDLE_RE if platform == "x" else GENERIC_HANDLE_RE
        if not isinstance(handle, str) or not handle_pattern.fullmatch(handle):
            return None, "account handle is invalid for its platform"
        if len(account["cycles"]) > 50 or any(not isinstance(item, str) for item in account["cycles"]):
            return None, "account cycle ids are invalid"
        project_name = account.get("projectName", "")
        if not isinstance(project_name, str) or len(project_name) > 80:
            return None, "project name is invalid"
        connection_method = account.get("connectionMethod", "official-api")
        if not isinstance(connection_method, str) or connection_method not in CONNECTION_METHOD_KEYS:
            return None, "connection method is invalid"
        for key, maximum in (("postsTarget", 100), ("repliesTarget", 500), ("tokenLimit", 100000000), ("spendAlert", 100)):
            if key in account and (not isinstance(account[key], (int, float)) or isinstance(account[key], bool) or account[key] < 0 or account[key] > maximum):
                return None, f"{key} is invalid"
        for key in ("scheduleEnabled", "usageAlerts", "codexTaskSync"):
            if key in account and not isinstance(account[key], bool):
                return None, f"{key} is invalid"
    for cycle in cycles:
        if not isinstance(cycle, dict) or not isinstance(cycle.get("id"), str) or not isinstance(cycle.get("name"), str):
            return None, "each cycle needs an id and name"
        description = cycle.get("description", "")
        if not isinstance(description, str):
            return None, "cycle description must be text"
        action = cycle.get("action", "post")
        if not isinstance(action, str) or action not in ACTION_KEYS:
            return None, "cycle action is invalid"
        if len(cycle["id"]) > 80 or len(cycle["name"]) > 120 or len(description) > 500:
            return None, "cycle text is too long"
        days = cycle.get("days", [])
        if not isinstance(days, list) or any(day not in DAY_KEYS for day in days):
            return None, "cycle days are invalid"
    timezone = payload.get("timezone", "UTC")
    if not isinstance(timezone, str) or len(timezone) > 80:
        return None, "timezone is invalid"
    return payload, None


class BoostHandler(SimpleHTTPRequestHandler):
    def __init__(self, *handler_args, **handler_kwargs):
        super().__init__(*handler_args, directory=str(ASSET_ROOT), **handler_kwargs)

    def _json(self, status: int, value: dict) -> None:
        payload = json.dumps(value).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def _body(self) -> tuple[object | None, str | None]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return None, "invalid content length"
        if length < 0 or length > MAX_BODY_BYTES:
            return None, "request body is too large"
        if self.headers.get("Content-Type", "").split(";", 1)[0].strip().casefold() != "application/json":
            return None, "content type must be application/json"
        try:
            return json.loads(self.rfile.read(length).decode("utf-8")), None
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None, "request body must be valid JSON"

    def _local_request(self) -> bool:
        host = self.headers.get("Host", "").split(":", 1)[0].casefold()
        return host in {"127.0.0.1", "localhost", "[::1]"}

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self._json(200, {"ok": True, "provider": "xurl", "xurlInstalled": bool(shutil.which("xurl"))})
            return
        if parsed.path == "/api/schedule":
            self._json(200, read_json(SCHEDULE_FILE, {"timezone": "UTC", "accounts": [], "cycles": []}))
            return
        if parsed.path == "/api/x/status":
            query = parse_qs(parsed.query)
            self._json(200, xurl_status(query.get("handle", [None])[0]))
            return
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path != "/api/schedule":
            self._json(404, {"ok": False, "error": "unknown endpoint"})
            return
        if not self._local_request():
            self._json(403, {"ok": False, "error": "local requests only"})
            return
        body, body_error = self._body()
        if body_error:
            self._json(400, {"ok": False, "error": body_error})
            return
        payload, validation_error = validate_schedule(body)
        if validation_error:
            self._json(400, {"ok": False, "error": validation_error})
            return
        write_json(SCHEDULE_FILE, payload)
        self._json(200, {"ok": True, "saved": str(SCHEDULE_FILE)})


server = ThreadingHTTPServer(("127.0.0.1", args.port), BoostHandler)
print(f"Boost: http://127.0.0.1:{args.port}/mockup.html")
try:
    server.serve_forever()
except KeyboardInterrupt:
    pass
finally:
    server.server_close()

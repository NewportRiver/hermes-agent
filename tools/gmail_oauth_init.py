#!/usr/bin/env python3
"""Owner-mediated, Gmail-readonly OAuth bootstrap for Hermes.

This helper deliberately does not use the broad Google Workspace setup script.
It prints only an authorization URL, then handles the local callback and stores
an authorized-user token with mode 0600.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import socketserver
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any

CLIENT_PATH = Path(os.path.expanduser("~/.config/hermes/gmail/credentials.json"))
TOKEN_PATH = Path(os.path.expanduser("~/.config/hermes/gmail/token.json"))
AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
PROFILE_ENDPOINT = "https://gmail.googleapis.com/gmail/v1/users/me/profile"
SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
EXPECTED_ACCOUNT = "hermesnewportriver@gmail.com"
TIMEOUT = 20
MAX_BYTES = 64_000


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RuntimeError(f"OAuth configuration is unreadable: {path.name}") from exc
    if not isinstance(value, dict):
        raise RuntimeError("OAuth configuration must be a JSON object")
    return value


def _client() -> tuple[str, str]:
    data = _read_json(CLIENT_PATH)
    installed = data.get("installed")
    if not isinstance(installed, dict):
        raise RuntimeError("credentials.json is not an installed-application client")
    client_id, client_secret = installed.get("client_id"), installed.get("client_secret")
    if not isinstance(client_id, str) or not isinstance(client_secret, str) or not client_id or not client_secret:
        raise RuntimeError("credentials.json lacks an installed-app client ID/secret")
    return client_id, client_secret


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def build_authorization_url(port: int, state: str, verifier: str, client_id: str) -> str:
    challenge = _b64(hashlib.sha256(verifier.encode("ascii")).digest())
    params = {
        "client_id": client_id,
        "redirect_uri": f"http://127.0.0.1:{port}/oauth2callback",
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "login_hint": EXPECTED_ACCOUNT,
    }
    return AUTH_ENDPOINT + "?" + urllib.parse.urlencode(params)


def _exchange(code: str, state: str, expected_state: str, verifier: str, port: int, client_id: str, client_secret: str) -> dict[str, Any]:
    if not secrets.compare_digest(state, expected_state):
        raise RuntimeError("OAuth state validation failed")
    body = urllib.parse.urlencode({
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": f"http://127.0.0.1:{port}/oauth2callback",
        "grant_type": "authorization_code",
        "code_verifier": verifier,
    }).encode("ascii")
    request = urllib.request.Request(TOKEN_ENDPOINT, data=body, method="POST")
    request.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            raw = response.read(MAX_BYTES + 1)
    except (urllib.error.HTTPError, urllib.error.URLError) as exc:
        raise RuntimeError("OAuth code exchange failed") from exc
    if len(raw) > MAX_BYTES:
        raise RuntimeError("OAuth token response exceeded bounded size")
    token = json.loads(raw.decode("utf-8"))
    granted = set(str(token.get("scope", "")).split())
    if SCOPE not in granted:
        raise RuntimeError("Google did not grant the required Gmail readonly scope")
    if any(scope != SCOPE for scope in granted):
        raise RuntimeError("Google granted an unexpected OAuth scope")
    token["type"] = "authorized_user"
    token["client_id"] = client_id
    token["client_secret"] = client_secret
    token["token_uri"] = TOKEN_ENDPOINT
    token["scopes"] = [SCOPE]
    token["created_at"] = int(time.time())
    return token


def _verify_account(access_token: str) -> str:
    request = urllib.request.Request(PROFILE_ENDPOINT, method="GET")
    request.add_header("Authorization", "Bearer " + access_token)
    request.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            raw = response.read(MAX_BYTES + 1)
    except (urllib.error.HTTPError, urllib.error.URLError) as exc:
        raise RuntimeError("Gmail account verification failed") from exc
    if len(raw) > MAX_BYTES:
        raise RuntimeError("Gmail profile response exceeded bounded size")
    profile = json.loads(raw.decode("utf-8"))
    account = profile.get("emailAddress")
    if account != EXPECTED_ACCOUNT:
        raise RuntimeError("OAuth account identity did not match the owner-approved account")
    return account


class _Callback(BaseHTTPRequestHandler):
    code: str | None = None
    state: str | None = None
    error: str | None = None

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/oauth2callback":
            self.send_error(404)
            return
        query = urllib.parse.parse_qs(parsed.query)
        type(self).code = query.get("code", [None])[0]
        type(self).state = query.get("state", [None])[0]
        type(self).error = query.get("error", [None])[0]
        body = b"OAuth callback received. You may close this browser tab."
        self.send_response(200 if not self.error else 400)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        return


def authorize(*, open_browser: bool = False) -> str:
    client_id, client_secret = _client()
    state = _b64(secrets.token_bytes(32))
    verifier = _b64(secrets.token_bytes(48))
    _Callback.code = _Callback.state = _Callback.error = None
    with socketserver.TCPServer(("127.0.0.1", 0), _Callback) as server:
        port = int(server.server_address[1])
        server.timeout = 1.0
        url = build_authorization_url(port, state, verifier, client_id)
        print(url, flush=True)
        if open_browser:
            webbrowser.open(url)
        deadline = time.monotonic() + float(os.environ.get("HERMES_GMAIL_OAUTH_TIMEOUT", "900"))
        while _Callback.code is None and _Callback.error is None and time.monotonic() < deadline:
            server.handle_request()
        if _Callback.error:
            raise RuntimeError("Owner denied OAuth authorization")
        if _Callback.code is None or _Callback.state is None:
            raise RuntimeError("OAuth callback timed out")
        token = _exchange(_Callback.code, _Callback.state, state, verifier, port, client_id, client_secret)
    account = _verify_account(str(token["access_token"]))
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(json.dumps(token, indent=2), encoding="utf-8")
    TOKEN_PATH.chmod(0o600)
    print(f"AUTHORIZED account={account} scope={SCOPE}", flush=True)
    return account


if __name__ == "__main__":
    authorize(open_browser=os.environ.get("HERMES_GMAIL_OPEN_BROWSER") == "1")

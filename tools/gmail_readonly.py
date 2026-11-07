"""Small, read-only Gmail connector for Hermes.

No OAuth flow is started here. Owner-mediated setup must create a separate
authorized-user token at ~/.config/hermes/gmail/token.json. The existing
credentials.json is preserved as the OAuth client configuration.
"""
from __future__ import annotations

import base64
import json
import os
import pathlib
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from tools.registry import registry

BASE = "https://gmail.googleapis.com/gmail/v1/users/me"
TOKEN_URI = "https://oauth2.googleapis.com/token"
GMAIL_HOME = pathlib.Path(os.path.expanduser("~/.config/hermes/gmail"))
CLIENT_FILE = GMAIL_HOME / "credentials.json"
TOKEN_FILE = pathlib.Path(os.environ.get("HERMES_GMAIL_TOKEN_FILE", str(GMAIL_HOME / "token.json")))
TIMEOUT = 15
MAX_BYTES = 512_000
MAX_RESULTS = 25
READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"


def _json(path: pathlib.Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RuntimeError(f"Gmail credential file is unreadable: {path.name}") from exc
    if not isinstance(value, dict):
        raise RuntimeError("Gmail credential file must contain an object")
    return value


def _client_id_secret() -> tuple[str, str]:
    data = _json(CLIENT_FILE)
    installed = data.get("installed") or data.get("web") or {}
    if not isinstance(installed, dict) or not installed.get("client_id") or not installed.get("client_secret"):
        raise RuntimeError("Gmail OAuth client credentials are not configured")
    return str(installed["client_id"]), str(installed["client_secret"])


def _access_token() -> str:
    data = _json(TOKEN_FILE)
    granted = set(str(data.get("scope", "")).split())
    granted.update(str(scope) for scope in data.get("scopes", []) if isinstance(data.get("scopes"), list))
    if granted != {"https://www.googleapis.com/auth/gmail.readonly"}:
        raise RuntimeError("Gmail token does not contain exactly the approved readonly scope")
    token = data.get("token") or data.get("access_token")
    expiry = data.get("expiry") or data.get("expires_at")
    if not expiry and data.get("created_at") and data.get("expires_in"):
        expiry = float(data["created_at"]) + float(data["expires_in"])
    if token and (not expiry or float(expiry) > time.time() + 30):
        return str(token)
    refresh = data.get("refresh_token")
    if not refresh:
        raise RuntimeError("Gmail OAuth authorization is incomplete or expired; owner consent is required")
    if data.get("token_uri", TOKEN_URI) != TOKEN_URI:
        raise RuntimeError("Gmail token endpoint is not the approved Google OAuth endpoint")
    client_id, client_secret = _client_id_secret()
    body = urllib.parse.urlencode({"client_id": client_id, "client_secret": client_secret, "refresh_token": refresh, "grant_type": "refresh_token"}).encode()
    request = urllib.request.Request(TOKEN_URI, data=body, method="POST")
    request.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            raw = response.read(MAX_BYTES + 1)
    except (urllib.error.URLError, urllib.error.HTTPError) as exc:
        raise RuntimeError("Gmail token refresh failed; authorization may be expired or revoked") from exc
    if len(raw) > MAX_BYTES:
        raise RuntimeError("Gmail token response exceeded bounded size")
    refreshed = json.loads(raw.decode("utf-8"))
    access = refreshed.get("access_token")
    if not access:
        raise RuntimeError("Gmail token refresh returned no access token")
    data.update(refreshed)
    data["token"] = access
    data["expiry"] = time.time() + float(refreshed.get("expires_in", 3600))
    data["scope"] = "https://www.googleapis.com/auth/gmail.readonly"
    TOKEN_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    TOKEN_FILE.chmod(0o600)
    return str(access)


def _call(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.startswith(BASE + "/") and path != BASE:
        raise ValueError("Only Gmail API paths are permitted")
    query = urllib.parse.urlencode(params or {}, doseq=True)
    request = urllib.request.Request(path + (("?" + query) if query else ""), method="GET")
    request.add_header("Authorization", "Bearer " + _access_token())
    request.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            raw = response.read(MAX_BYTES + 1)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Gmail API rejected read-only request ({exc.code})") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError("Gmail API unavailable") from exc
    if len(raw) > MAX_BYTES:
        raise RuntimeError("Gmail API response exceeded bounded size")
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("Gmail API returned an unexpected response")
    return value


def _headers(message: dict[str, Any]) -> dict[str, str]:
    return {str(h.get("name", "")).lower(): str(h.get("value", "")) for h in message.get("payload", {}).get("headers", []) if h.get("name")}


def _body(message: dict[str, Any]) -> str:
    payload = message.get("payload", {})
    candidates = [payload] + list(payload.get("parts", []))
    for part in candidates:
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", "replace")
    return ""


def gmail_search(query: str, max_results: int = 10, **_: Any) -> str:
    if not isinstance(query, str) or len(query) > 500:
        raise ValueError("query must be at most 500 characters")
    max_results = max(1, min(int(max_results), MAX_RESULTS))
    listed = _call(BASE + "/messages", {"q": query, "maxResults": max_results})
    output = []
    for item in listed.get("messages", [])[:max_results]:
        message = _call(BASE + "/messages/" + str(item["id"]), {"format": "metadata", "metadataHeaders": ["From", "To", "Subject", "Date"]})
        headers = _headers(message)
        output.append({"id": message.get("id"), "threadId": message.get("threadId"), "from": headers.get("from", ""), "to": headers.get("to", ""), "subject": headers.get("subject", ""), "date": headers.get("date", ""), "snippet": message.get("snippet", ""), "labels": message.get("labelIds", [])})
    return json.dumps(output, ensure_ascii=True)


def gmail_get(message_id: str, **_: Any) -> str:
    if not isinstance(message_id, str) or not message_id or len(message_id) > 200 or "/" in message_id:
        raise ValueError("message_id is invalid")
    message = _call(BASE + "/messages/" + message_id, {"format": "full"})
    headers = _headers(message)
    return json.dumps({"id": message.get("id"), "threadId": message.get("threadId"), "from": headers.get("from", ""), "to": headers.get("to", ""), "subject": headers.get("subject", ""), "date": headers.get("date", ""), "labels": message.get("labelIds", []), "body": _body(message)}, ensure_ascii=True)


# Explicit top-level registrations are required by Hermes AST-based discovery.
registry.register(name="gmail_search_readonly", toolset="gmail_readonly", schema={"name":"gmail_search_readonly","description":"Search Gmail and return bounded metadata only; never sends or modifies mail.","parameters":{"type":"object","properties":{"query":{"type":"string","maxLength":500},"max_results":{"type":"integer","minimum":1,"maximum":MAX_RESULTS}},"required":["query","max_results"]}}, handler=lambda args, **kw: gmail_search(**args, **kw), check_fn=lambda: CLIENT_FILE.exists() and TOKEN_FILE.exists(), max_result_size_chars=MAX_BYTES)
registry.register(name="gmail_get_readonly", toolset="gmail_readonly", schema={"name":"gmail_get_readonly","description":"Read one Gmail message body; never sends or modifies mail.","parameters":{"type":"object","properties":{"message_id":{"type":"string","minLength":1,"maxLength":200}},"required":["message_id"]}}, handler=lambda args, **kw: gmail_get(**args, **kw), check_fn=lambda: CLIENT_FILE.exists() and TOKEN_FILE.exists(), max_result_size_chars=MAX_BYTES)

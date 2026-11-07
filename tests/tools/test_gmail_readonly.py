import importlib.util
import json
import pathlib

MODULE = pathlib.Path(__file__).parents[2] / "tools" / "gmail_readonly.py"


def load_module(monkeypatch, tmp_path):
    spec = importlib.util.spec_from_file_location("gmail_readonly_test", MODULE)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setattr(pathlib.Path, "home", staticmethod(lambda: tmp_path))
    spec.loader.exec_module(module)
    return module


def test_connector_is_fail_closed_without_token(monkeypatch, tmp_path):
    module = load_module(monkeypatch, tmp_path)
    module.CLIENT_FILE = tmp_path / "credentials.json"
    module.TOKEN_FILE = tmp_path / "token.json"
    module.CLIENT_FILE.write_text(json.dumps({"installed": {"client_id": "id", "client_secret": "secret"}}))
    try:
        module.gmail_search("is:unread")
    except RuntimeError as exc:
        assert "authorization" in str(exc).lower() or "token" in str(exc).lower()
    else:
        raise AssertionError("connector must not call Gmail without owner-authorized token")


def test_read_only_shapes_and_api_allowlist(monkeypatch, tmp_path):
    module = load_module(monkeypatch, tmp_path)
    calls = []
    module._access_token = lambda: "redacted-test-token"
    def fake_call(path, params=None):
        calls.append((path, params))
        if path.endswith("/messages"):
            return {"messages": [{"id": "abc"}]}
        return {"id": "abc", "threadId": "thread", "snippet": "hello", "labelIds": ["UNREAD"], "payload": {"headers": [{"name": "Subject", "value": "Test"}]}}
    original_call = module._call
    module._call = fake_call
    result = json.loads(module.gmail_search("is:unread", 1))
    assert result[0]["subject"] == "Test"
    assert calls[0][0] == module.BASE + "/messages"
    assert module.gmail_get("abc")
    try:
        original_call("https://evil.example/messages")
    except ValueError:
        pass
    else:
        raise AssertionError("non-Gmail endpoint must be rejected")


def test_refreshes_token_created_by_oauth_helper(monkeypatch, tmp_path):
    module = load_module(monkeypatch, tmp_path)
    module.CLIENT_FILE = tmp_path / "credentials.json"
    module.TOKEN_FILE = tmp_path / "token.json"
    module.CLIENT_FILE.write_text(json.dumps({"installed": {"client_id": "id", "client_secret": "secret"}}))
    module.TOKEN_FILE.write_text(json.dumps({"access_token": "old", "refresh_token": "refresh", "scope": module.READONLY_SCOPE, "created_at": 1, "expires_in": 1, "token_uri": module.TOKEN_URI}))
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return None
        def read(self, _limit): return json.dumps({"access_token": "new", "expires_in": 3600}).encode()
    monkeypatch.setattr(module.urllib.request, "urlopen", lambda request, timeout: Response())
    assert module._access_token() == "new"
    saved = json.loads(module.TOKEN_FILE.read_text())
    assert saved["access_token"] == "new"
    assert saved["scope"] == module.READONLY_SCOPE
    assert oct(module.TOKEN_FILE.stat().st_mode & 0o777) == "0o600"


def test_rejects_unexpected_scope(monkeypatch, tmp_path):
    module = load_module(monkeypatch, tmp_path)
    module.CLIENT_FILE = tmp_path / "credentials.json"
    module.TOKEN_FILE = tmp_path / "token.json"
    module.TOKEN_FILE.write_text(json.dumps({"access_token": "token", "scope": "https://www.googleapis.com/auth/gmail.modify"}))
    try:
        module._access_token()
    except RuntimeError as exc:
        assert "scope" in str(exc).lower()
    else:
        raise AssertionError("unexpected Gmail scope must be rejected")

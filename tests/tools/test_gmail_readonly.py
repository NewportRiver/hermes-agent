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

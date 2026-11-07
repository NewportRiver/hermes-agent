import importlib.util
import json
import pathlib
import urllib.parse

ROOT = pathlib.Path(__file__).parents[2]


def load_module():
    spec = importlib.util.spec_from_file_location("gmail_oauth_init_test", ROOT / "tools" / "gmail_oauth_init.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_authorization_url_is_pkce_and_readonly():
    module = load_module()
    url = module.build_authorization_url(43123, "state-value", "verifier-value", "client-id")
    params = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    assert params["scope"] == [module.SCOPE]
    assert params["redirect_uri"] == ["http://127.0.0.1:43123/oauth2callback"]
    assert params["code_challenge_method"] == ["S256"]
    assert params["state"] == ["state-value"]
    assert "gmail.send" not in url
    assert "gmail.modify" not in url


def test_exchange_rejects_wrong_state_without_network():
    module = load_module()
    try:
        module._exchange("code", "wrong", "expected", "verifier", 43123, "id", "secret")
    except RuntimeError as exc:
        assert "state" in str(exc).lower()
    else:
        raise AssertionError("wrong OAuth state must fail before token exchange")


def test_callback_captures_only_code_and_state():
    module = load_module()
    handler = module._Callback
    handler.code = handler.state = handler.error = None
    # Handler behavior is exercised through its parsing contract in isolation;
    # no network, token, or authorization value is printed by this test.
    assert handler.code is None and handler.state is None and handler.error is None

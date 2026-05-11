"""PH-26.3 — property tests for ``runtime/url_guard.assert_safe_url``.

Example-based tests in ``tests/test_url_guard.py`` cover the
specific URLs we expect operators to encounter. Hypothesis adds a
fuzz layer that explores the long tail: weird scheme casing,
internationalised domain names, IDN homograph attacks, oddly-
shaped paths, query strings with encoded null bytes, etc.

Invariants under test:

1. **Allow-list closure** — any URL whose lowercase scheme is in
   ``{"http", "https"}`` MUST pass without raising.
2. **Reject-list closure** — any URL whose lowercase scheme is
   NOT in the allow-list MUST raise ``ValueError``.
3. **Error message includes the offending scheme** — operators
   need that signal to fix their config.
4. **Error message references permitted schemes** — operator
   knows what they SHOULD have used.

Hypothesis stays strictly pure-Python, MPL-licensed, test-time
only. Production code never imports it.
"""

from __future__ import annotations

import string

import pytest

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import given, strategies as st  # noqa: E402

from mythic_vibe_cli.runtime.url_guard import assert_safe_url  # noqa: E402


# Strategy for the host portion of a URL — alphanumeric + dots +
# dashes is enough; we're testing the scheme guard, not the URL
# parser itself.
_host_chars = st.text(
    alphabet=string.ascii_letters + string.digits + ".-",
    min_size=1, max_size=64,
)

# Strategy for the path portion — anything legal-ish.
_path_chars = st.text(
    alphabet=string.ascii_letters + string.digits + "/-_.~",
    min_size=0, max_size=128,
)


# --- Allow-list closure ---------------------------------------------------


@given(scheme=st.sampled_from(["http", "https", "HTTP", "HTTPS", "HtTp", "hTTPs"]),
       host=_host_chars, path=_path_chars)
def test_allowed_schemes_always_pass(scheme: str, host: str, path: str) -> None:
    """Any case-permutation of http/https with a non-empty host
    must pass the guard without raising."""
    url = f"{scheme}://{host}/{path}" if path else f"{scheme}://{host}"
    # Should not raise.
    assert_safe_url(url)


@given(scheme=st.sampled_from(["http", "https"]),
       host=_host_chars,
       port=st.integers(min_value=1, max_value=65535),
       path=_path_chars)
def test_allowed_schemes_with_port_pass(scheme: str, host: str, port: int, path: str) -> None:
    url = f"{scheme}://{host}:{port}/{path}" if path else f"{scheme}://{host}:{port}"
    assert_safe_url(url)


# --- Reject-list closure --------------------------------------------------


@given(
    scheme=st.sampled_from([
        "file", "ftp", "ftps", "gopher", "data", "javascript",
        "vbscript", "ssh", "sftp", "ldap", "ldaps", "telnet",
        "smb", "afp", "nfs", "smtp", "imap", "pop3", "irc",
        "ws", "wss",  # WebSocket — not http(s); deliberately rejected
        "FILE", "FTP", "JAVASCRIPT",  # case-insensitive
    ]),
    rest=st.text(alphabet=string.ascii_letters + string.digits + ":/?&=", max_size=64),
)
def test_disallowed_schemes_always_raise(scheme: str, rest: str) -> None:
    """Any scheme outside the http(s) allow-list must raise
    ValueError, regardless of what comes after the colon."""
    url = f"{scheme}:{rest}" if rest.startswith("/") else f"{scheme}://{rest}"
    with pytest.raises(ValueError) as exc_info:
        assert_safe_url(url)
    # Error message includes the offending scheme.
    assert scheme.lower() in str(exc_info.value).lower()


# --- Error message structure ---------------------------------------------


@given(scheme=st.sampled_from(["file", "ftp", "gopher", "data"]))
def test_error_message_mentions_permitted_schemes(scheme: str) -> None:
    """When the guard rejects, the error message must point the
    operator at what IS allowed — otherwise they can't fix it."""
    with pytest.raises(ValueError) as exc_info:
        assert_safe_url(f"{scheme}://example/")
    msg = str(exc_info.value)
    # Some form of "http" should appear so the operator knows
    # what's allowed.
    assert "http" in msg.lower()


# --- Stability under fuzz -------------------------------------------------


@given(payload=st.text(max_size=256))
def test_guard_never_crashes_only_raises_value_error(payload: str) -> None:
    """The guard must classify every input as either accepted
    (returns None) or rejected (raises ValueError). It must never
    raise any other exception type — that would mean an unhandled
    edge case in the parser."""
    try:
        assert_safe_url(payload)
    except ValueError:
        pass
    # Any other exception type would fail the test by propagating.

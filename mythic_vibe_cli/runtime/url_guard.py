"""URL scheme guard for ``urllib.request.urlopen`` (PH-24.5).

The Python stdlib URL opener accepts arbitrary schemes by default —
including ``file://`` (read local files) and ``ftp://`` (legacy
network protocol). Any code path that reaches ``urlopen`` with an
operator-influenced URL is therefore one mistake away from a local-
file-disclosure or unintended-protocol issue.

This module provides one tiny choke-point function — :func:`assert_safe_url` —
that every URL-opening site in the CLI must call before
``urlopen``. The fast path (URL starts with ``https://`` or
``http://``) is one string comparison; the slow path uses
``urllib.parse.urlsplit`` to extract the scheme and validate it.

Threat model:
- An operator-controlled config field (Matrix homeserver, Ollama
  endpoint, mythic-data import URL, etc.) becomes the URL.
- Bug or malicious config flips it to ``file:///etc/passwd``.
- Without this guard, the CLI would happily read the file and
  return its contents in a JSON response or log line.
- With this guard, the call raises :class:`ValueError` before
  ``urlopen`` is reached.

Cross-platform: pure stdlib (no platform-specific code).
"""

from __future__ import annotations

from urllib.parse import urlsplit


_ALLOWED_URL_SCHEMES: frozenset[str] = frozenset({"http", "https"})


def assert_safe_url(url: str) -> None:
    """Raise :class:`ValueError` if ``url`` is not http(s).

    The fast path (``url.startswith("https://")`` or ``"http://"``)
    is one comparison; the slow path parses the URL and checks the
    scheme case-insensitively.

    Args:
        url: The URL about to be opened.

    Raises:
        ValueError: When the URL's scheme is not in
            :data:`_ALLOWED_URL_SCHEMES`.
    """
    # Fast path: virtually every real call starts with https://.
    if url.startswith(("https://", "http://")):
        return
    # Slow path: parse + validate. Empty / invalid URLs land here too.
    parts = urlsplit(url)
    if parts.scheme.lower() not in _ALLOWED_URL_SCHEMES:
        raise ValueError(
            f"Refusing to open URL with scheme {parts.scheme!r}: "
            f"only http/https are permitted (url={url!r})."
        )


__all__ = ["assert_safe_url"]

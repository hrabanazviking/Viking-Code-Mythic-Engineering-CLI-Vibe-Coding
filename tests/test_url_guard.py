"""PH-24.5 — URL scheme guard tests.

Validates :func:`mythic_vibe_cli.runtime.url_guard.assert_safe_url`,
the shared choke-point that every ``urllib.request.urlopen`` call
in the CLI now passes through.

Threat being guarded:
- ``urllib.request.urlopen`` accepts ``file://``, ``ftp://``, and
  arbitrary custom schemes by default. An operator-controlled
  config field (Matrix homeserver, Ollama endpoint, mythic-data
  import URL) reaching ``urlopen`` with ``file:///etc/passwd`` would
  read a local file and surface its contents in a JSON response.
- The guard refuses any scheme outside ``http`` / ``https`` before
  ``urlopen`` is called.
"""

from __future__ import annotations

import unittest

from mythic_vibe_cli.runtime.url_guard import assert_safe_url


class AssertSafeUrlAcceptsHttpsTests(unittest.TestCase):
    def test_basic_https_url(self) -> None:
        assert_safe_url("https://api.example.com/v1/foo")

    def test_basic_http_url(self) -> None:
        assert_safe_url("http://localhost:8080/health")

    def test_https_with_query(self) -> None:
        assert_safe_url("https://api.example.com/v1/x?a=1&b=2")

    def test_https_with_userinfo(self) -> None:
        # Userinfo segment is rare but legal for http(s).
        assert_safe_url("https://user:pass@api.example.com/")

    def test_https_with_port(self) -> None:
        assert_safe_url("https://api.example.com:8443/v1/foo")


class AssertSafeUrlRejectsBadSchemesTests(unittest.TestCase):
    def test_file_scheme_is_rejected(self) -> None:
        """The whole point of the guard — operator-controlled URL
        attempting to read a local file."""
        with self.assertRaises(ValueError) as cm:
            assert_safe_url("file:///etc/passwd")
        self.assertIn("scheme", str(cm.exception).lower())
        self.assertIn("file", str(cm.exception))

    def test_ftp_scheme_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            assert_safe_url("ftp://anonymous:user@ftp.example.com/")

    def test_gopher_scheme_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            assert_safe_url("gopher://gopher.example.com/")

    def test_data_uri_is_rejected(self) -> None:
        """``data:`` URIs are technically valid for some uses, but
        the AI/chat bridge / mythic-data sites have no business
        opening one — refuse."""
        with self.assertRaises(ValueError):
            assert_safe_url("data:text/plain,hello")

    def test_javascript_uri_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            assert_safe_url("javascript:alert(1)")

    def test_empty_url_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            assert_safe_url("")

    def test_scheme_only_url_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            assert_safe_url("file:")

    def test_no_scheme_url_is_rejected(self) -> None:
        """A bare ``api.example.com/v1/foo`` (no scheme) parses with
        scheme="". Rejected — the caller should pass full URLs."""
        with self.assertRaises(ValueError):
            assert_safe_url("api.example.com/v1/foo")


class AssertSafeUrlCaseInsensitiveSchemeTests(unittest.TestCase):
    def test_uppercase_https_in_slow_path(self) -> None:
        """The fast path is case-sensitive; the slow path lowercases
        before comparison. ``HTTPS://`` should still pass."""
        assert_safe_url("HTTPS://api.example.com/")

    def test_mixed_case_http_in_slow_path(self) -> None:
        assert_safe_url("hTtP://localhost/")


class AssertSafeUrlErrorMessageTests(unittest.TestCase):
    """The error message must give the operator enough context to
    fix the misconfiguration without grepping the codebase."""

    def test_rejection_includes_offending_scheme(self) -> None:
        with self.assertRaises(ValueError) as cm:
            assert_safe_url("file:///etc/passwd")
        self.assertIn("file", str(cm.exception))

    def test_rejection_includes_url(self) -> None:
        with self.assertRaises(ValueError) as cm:
            assert_safe_url("ftp://example.com/x")
        self.assertIn("ftp://example.com/x", str(cm.exception))

    def test_rejection_mentions_permitted_schemes(self) -> None:
        with self.assertRaises(ValueError) as cm:
            assert_safe_url("ftp://example.com/x")
        msg = str(cm.exception)
        # Operator must know what IS allowed.
        self.assertIn("http", msg)


class IntegrationWithProviderPostJsonTests(unittest.TestCase):
    """The post_json path through ``ai/providers/base`` must reject
    bad-scheme URLs. Validates the wiring."""

    def test_post_json_refuses_file_url(self) -> None:
        from mythic_vibe_cli.ai.providers.base import post_json
        with self.assertRaises(ValueError) as cm:
            post_json("file:///etc/passwd", {}, {})
        self.assertIn("scheme", str(cm.exception).lower())


class IntegrationWithGitHubClientTests(unittest.TestCase):
    """GitHubClient.get_json must reject bad-scheme URLs."""

    def test_github_client_refuses_file_url(self) -> None:
        from mythic_vibe_cli.plunder.github import GitHubClient
        client = GitHubClient()
        with self.assertRaises(ValueError):
            client.get_json("file:///etc/passwd")


if __name__ == "__main__":
    unittest.main()

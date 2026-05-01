"""Tests for PH-11 Slice 11.6 — privacy mode."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mythic_vibe_cli.security.privacy import (
    PrivacyPolicy,
    filter_paths,
    filter_payload,
    is_path_allowed,
    resolve_privacy_policy,
)


def _write_config(root: Path, body: str) -> None:
    (root / "mythic").mkdir(exist_ok=True)
    (root / "mythic" / "security.toml").write_text(body, encoding="utf-8")


# ---- resolve_privacy_policy ------------------------------------------


class ResolvePolicyTests(unittest.TestCase):
    def test_no_config_returns_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            policy = resolve_privacy_policy(Path(tmp))
        self.assertFalse(policy.enabled)
        self.assertIn("not configured", policy.notes[0])

    def test_enabled_without_allow_list_warns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_config(root, "[privacy]\nenabled = true\n")
            policy = resolve_privacy_policy(root)
        self.assertTrue(policy.enabled)
        self.assertEqual(policy.allow_paths, ())
        self.assertTrue(any("empty allow_paths" in n for n in policy.notes))

    def test_enabled_with_allow_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_config(
                root,
                '[privacy]\nenabled = true\nallow_paths = ["src/", "docs/"]\n',
            )
            policy = resolve_privacy_policy(root)
        self.assertTrue(policy.enabled)
        self.assertEqual(policy.allow_paths, ("src/", "docs/"))


# ---- is_path_allowed -------------------------------------------------


class IsPathAllowedTests(unittest.TestCase):
    def test_disabled_policy_allows_everything(self) -> None:
        policy = PrivacyPolicy(enabled=False)
        self.assertTrue(is_path_allowed("anything", policy))

    def test_enabled_empty_allow_denies_everything(self) -> None:
        policy = PrivacyPolicy(enabled=True, allow_paths=())
        self.assertFalse(is_path_allowed("src/main.py", policy))

    def test_prefix_dir_match(self) -> None:
        policy = PrivacyPolicy(enabled=True, allow_paths=("src/", "docs/"))
        self.assertTrue(is_path_allowed("src/main.py", policy))
        self.assertTrue(is_path_allowed("docs/README.md", policy))
        self.assertFalse(is_path_allowed("tests/test_x.py", policy))

    def test_glob_match(self) -> None:
        policy = PrivacyPolicy(enabled=True, allow_paths=("*.py",))
        self.assertTrue(is_path_allowed("main.py", policy))
        self.assertFalse(is_path_allowed("README.md", policy))

    def test_exact_path_match(self) -> None:
        policy = PrivacyPolicy(enabled=True, allow_paths=("README.md",))
        self.assertTrue(is_path_allowed("README.md", policy))
        self.assertFalse(is_path_allowed("docs/README.md", policy))

    def test_prefix_dir_without_trailing_slash(self) -> None:
        """Allow rule "src" matches src/anything (the slash is
        added implicitly when the rule has no trailing slash)."""
        policy = PrivacyPolicy(enabled=True, allow_paths=("src",))
        self.assertTrue(is_path_allowed("src/main.py", policy))
        self.assertTrue(is_path_allowed("src", policy))
        self.assertFalse(is_path_allowed("source/main.py", policy))


# ---- filter_paths ----------------------------------------------------


class FilterPathsTests(unittest.TestCase):
    def test_split_allowed_denied(self) -> None:
        policy = PrivacyPolicy(enabled=True, allow_paths=("src/",))
        allowed, denied = filter_paths(
            ["src/a.py", "tests/b.py", "src/c.py", "docs/d.md"],
            policy,
        )
        self.assertEqual(allowed, ["src/a.py", "src/c.py"])
        self.assertEqual(denied, ["tests/b.py", "docs/d.md"])

    def test_disabled_policy_passes_all(self) -> None:
        policy = PrivacyPolicy(enabled=False)
        allowed, denied = filter_paths(["src/a.py", "anywhere.py"], policy)
        self.assertEqual(len(allowed), 2)
        self.assertEqual(denied, [])


# ---- filter_payload --------------------------------------------------


class FilterPayloadTests(unittest.TestCase):
    def test_disabled_passthrough(self) -> None:
        policy = PrivacyPolicy(enabled=False)
        self.assertEqual(
            filter_payload({"path": "src/main.py"}, policy),
            {"path": "src/main.py"},
        )

    def test_path_string_filtered(self) -> None:
        policy = PrivacyPolicy(enabled=True, allow_paths=("src/",))
        self.assertEqual(
            filter_payload("src/allowed.py", policy),
            "src/allowed.py",
        )
        self.assertEqual(
            filter_payload("private/secret.py", policy),
            "[PRIVACY:FILTERED]",
        )

    def test_non_path_string_passes(self) -> None:
        """Strings without slashes / with whitespace pass through —
        privacy mode doesn't try to redact arbitrary content."""
        policy = PrivacyPolicy(enabled=True, allow_paths=())
        self.assertEqual(
            filter_payload("hello world", policy), "hello world"
        )
        self.assertEqual(
            filter_payload("identifier_123", policy), "identifier_123"
        )

    def test_nested_dict_filtering(self) -> None:
        policy = PrivacyPolicy(enabled=True, allow_paths=("src/",))
        out = filter_payload(
            {
                "primary": "src/a.py",
                "secret": "private/b.py",
                "nested": {"path": "tests/c.py"},
            },
            policy,
        )
        self.assertEqual(out["primary"], "src/a.py")
        self.assertEqual(out["secret"], "[PRIVACY:FILTERED]")
        self.assertEqual(out["nested"]["path"], "[PRIVACY:FILTERED]")

    def test_list_filtering(self) -> None:
        policy = PrivacyPolicy(enabled=True, allow_paths=("src/",))
        out = filter_payload(["src/a.py", "private/b.py"], policy)
        self.assertEqual(out, ["src/a.py", "[PRIVACY:FILTERED]"])

    def test_tuple_filtering(self) -> None:
        policy = PrivacyPolicy(enabled=True, allow_paths=("src/",))
        out = filter_payload(("src/a.py", "private/b.py"), policy)
        self.assertIsInstance(out, tuple)
        self.assertEqual(out[1], "[PRIVACY:FILTERED]")

    def test_long_string_passes(self) -> None:
        """Strings > 256 chars are treated as content, not paths."""
        policy = PrivacyPolicy(enabled=True, allow_paths=())
        long_value = "x" * 300
        self.assertEqual(filter_payload(long_value, policy), long_value)


if __name__ == "__main__":
    unittest.main()

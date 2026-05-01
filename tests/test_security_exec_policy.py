"""Tests for PH-11 Slice 11.4 — sandbox execution policy."""

from __future__ import annotations

import platform
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from mythic_vibe_cli.security.exec_policy import (
    SandboxPolicy,
    enforce_directory_restriction,
    is_cwd_inside_root,
    resolve_sandbox_policy,
    wrap_argv_for_network_disabled,
)


def _write_security_toml(root: Path, body: str) -> None:
    (root / "mythic").mkdir(exist_ok=True)
    (root / "mythic" / "security.toml").write_text(body, encoding="utf-8")


# ---- resolve_sandbox_policy ------------------------------------------


class ResolveSandboxPolicyTests(unittest.TestCase):
    def test_no_config_returns_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            policy = resolve_sandbox_policy(Path(tmp))
        self.assertFalse(policy.enabled)
        self.assertFalse(policy.directory_restriction)
        self.assertFalse(policy.network_disabled)
        self.assertIn("not configured", policy.notes[0])

    def test_enabled_with_directory_restriction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_security_toml(
                root,
                "[sandbox]\nenabled = true\ndirectory_restriction = true\n",
            )
            policy = resolve_sandbox_policy(root)
        self.assertTrue(policy.enabled)
        self.assertTrue(policy.directory_restriction)
        self.assertFalse(policy.network_disabled)

    def test_network_disabled_advisory_when_no_unshare(self) -> None:
        """On platforms without unshare, network_disabled is
        advisory-only and we surface a note."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_security_toml(
                root,
                "[sandbox]\nenabled = true\nnetwork_disabled = true\n",
            )
            with mock.patch(
                "mythic_vibe_cli.security.exec_policy._is_linux_unshare_available",
                return_value=False,
            ):
                policy = resolve_sandbox_policy(root)
        self.assertTrue(policy.network_disabled)
        self.assertTrue(policy.network_advisory_only)
        self.assertTrue(any("advisory-only" in n for n in policy.notes))

    def test_network_disabled_enforced_on_linux_with_unshare(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_security_toml(
                root,
                "[sandbox]\nenabled = true\nnetwork_disabled = true\n",
            )
            with mock.patch(
                "mythic_vibe_cli.security.exec_policy._is_linux_unshare_available",
                return_value=True,
            ):
                policy = resolve_sandbox_policy(root)
        self.assertTrue(policy.network_disabled)
        self.assertFalse(policy.network_advisory_only)


# ---- is_cwd_inside_root ----------------------------------------------


class IsCwdInsideRootTests(unittest.TestCase):
    def test_cwd_at_root_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertTrue(is_cwd_inside_root(tmp, tmp))

    def test_cwd_under_root_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sub = Path(tmp) / "sub"
            sub.mkdir()
            self.assertTrue(is_cwd_inside_root(sub, tmp))

    def test_cwd_outside_root_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_a:
            with tempfile.TemporaryDirectory() as tmp_b:
                self.assertFalse(is_cwd_inside_root(tmp_a, tmp_b))


# ---- enforce_directory_restriction -----------------------------------


class EnforceDirectoryRestrictionTests(unittest.TestCase):
    def _policy(
        self, *, enabled: bool, restriction: bool, root: str
    ) -> SandboxPolicy:
        return SandboxPolicy(
            enabled=enabled,
            directory_restriction=restriction,
            network_disabled=False,
            network_advisory_only=True,
            project_root=root,
        )

    def test_disabled_policy_always_allows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            policy = self._policy(enabled=False, restriction=True, root=tmp)
            allowed, reason = enforce_directory_restriction(
                cwd="/anywhere", policy=policy
            )
            self.assertTrue(allowed)
            self.assertEqual(reason, "")

    def test_restriction_off_always_allows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            policy = self._policy(enabled=True, restriction=False, root=tmp)
            allowed, _reason = enforce_directory_restriction(
                cwd="/elsewhere", policy=policy
            )
            self.assertTrue(allowed)

    def test_restriction_on_inside_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            policy = self._policy(enabled=True, restriction=True, root=tmp)
            allowed, _reason = enforce_directory_restriction(
                cwd=tmp, policy=policy
            )
            self.assertTrue(allowed)

    def test_restriction_on_outside_root_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_a:
            with tempfile.TemporaryDirectory() as tmp_b:
                policy = self._policy(
                    enabled=True, restriction=True, root=tmp_b
                )
                allowed, reason = enforce_directory_restriction(
                    cwd=tmp_a, policy=policy
                )
                self.assertFalse(allowed)
                self.assertIn("blocked", reason)
                self.assertIn(tmp_b, reason)


# ---- wrap_argv_for_network_disabled ----------------------------------


class WrapArgvForNetworkDisabledTests(unittest.TestCase):
    def test_disabled_policy_passthrough(self) -> None:
        policy = SandboxPolicy(
            enabled=False,
            directory_restriction=False,
            network_disabled=True,
            network_advisory_only=False,
            project_root="/x",
        )
        self.assertEqual(
            wrap_argv_for_network_disabled(["pytest"], policy=policy),
            ["pytest"],
        )

    def test_advisory_only_passthrough(self) -> None:
        policy = SandboxPolicy(
            enabled=True,
            directory_restriction=False,
            network_disabled=True,
            network_advisory_only=True,  # platform can't enforce
            project_root="/x",
        )
        self.assertEqual(
            wrap_argv_for_network_disabled(["pytest"], policy=policy),
            ["pytest"],
        )

    def test_enforced_prepends_unshare(self) -> None:
        policy = SandboxPolicy(
            enabled=True,
            directory_restriction=False,
            network_disabled=True,
            network_advisory_only=False,
            project_root="/x",
        )
        result = wrap_argv_for_network_disabled(["pytest", "-q"], policy=policy)
        self.assertEqual(result[:3], ["unshare", "-n", "--"])
        self.assertEqual(result[3:], ["pytest", "-q"])


class PlatformAwareUnshareDetectionTests(unittest.TestCase):
    def test_returns_false_on_non_linux(self) -> None:
        # On Windows / macOS the helper must always return False
        # without inspecting PATH. Tests assert the Windows path
        # explicitly when running there.
        from mythic_vibe_cli.security.exec_policy import (
            _is_linux_unshare_available,
        )

        if platform.system().lower() == "linux":
            self.skipTest("Linux-host invariant covered by other tests")
        self.assertFalse(_is_linux_unshare_available())


if __name__ == "__main__":
    unittest.main()

"""Tests for the hardware profile detector + CLI (PH-06 slice 6.6)."""

from __future__ import annotations

import argparse
import builtins
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from mythic_vibe_cli.app import build_parser
from mythic_vibe_cli.commands import COMMAND_HANDLERS
from mythic_vibe_cli.exit_codes import SUCCESS
from mythic_vibe_cli.hardware import (
    DEFAULT_PROFILE_FILENAME,
    DEFAULT_PROFILE_JSON_FILENAME,
    HardwareProfile,
    detect_platform_tags,
    detect_profile,
    is_raspberry_pi,
    is_termux,
    is_wsl,
    render_profile_markdown,
    render_profile_text,
    write_profile,
)
from mythic_vibe_cli.runtime.slash_commands import BUILTIN_SLASH_COMMANDS


# ---- HardwareProfile dataclass ---------------------------------------


class HardwareProfileTests(unittest.TestCase):
    def test_to_dict_round_trip(self) -> None:
        profile = HardwareProfile(
            detected_at="t",
            os="Linux",
            os_release="6.0",
            arch="x86_64",
            cpu="x86_64 unspecified",
            logical_cpus=8,
            physical_cpus=4,
            ram_total_mb=16000,
            ram_available_mb=8000,
            python_version="3.11.0",
            platform="Linux-6.0-x86_64",
            notes=["nothing surprising"],
        )
        payload = profile.to_dict()
        for key in {
            "detected_at",
            "os",
            "os_release",
            "arch",
            "cpu",
            "logical_cpus",
            "physical_cpus",
            "ram_total_mb",
            "ram_available_mb",
            "python_version",
            "platform",
            "notes",
        }:
            self.assertIn(key, payload)
        self.assertEqual(payload["notes"], ["nothing surprising"])


# ---- detect_profile ---------------------------------------------------


class DetectProfileTests(unittest.TestCase):
    def test_returns_profile_with_basic_fields(self) -> None:
        profile = detect_profile()
        self.assertIsInstance(profile, HardwareProfile)
        self.assertTrue(profile.detected_at)
        # OS / arch / python should always populate.
        self.assertTrue(profile.os)
        self.assertTrue(profile.python_version)
        self.assertTrue(profile.platform)
        # logical_cpus should be > 0 on any real test runner; if it
        # is 0 the detector recorded a note.
        if profile.logical_cpus == 0:
            self.assertTrue(
                any("os.cpu_count" in n for n in profile.notes),
                f"expected note about os.cpu_count when 0, got {profile.notes}",
            )

    def test_psutil_missing_records_note(self) -> None:
        """When psutil is not importable, the detector must still
        complete and note the gap. Use mock to simulate the missing
        import."""
        real_import = builtins.__import__

        def fake_import(name: str, *args: object, **kwargs: object) -> object:
            if name == "psutil":
                raise ImportError("simulated absence")
            return real_import(name, *args, **kwargs)

        # Drop any cached psutil so the patched __import__ is the path
        # that runs.
        cached = sys.modules.pop("psutil", None)
        try:
            with mock.patch("builtins.__import__", side_effect=fake_import):
                profile = detect_profile()
        finally:
            if cached is not None:
                sys.modules["psutil"] = cached

        self.assertEqual(profile.ram_total_mb, 0)
        self.assertEqual(profile.ram_available_mb, 0)
        self.assertEqual(profile.physical_cpus, 0)
        self.assertTrue(
            any("psutil not installed" in note for note in profile.notes),
            f"expected psutil-not-installed note, got {profile.notes}",
        )

    def test_psutil_failure_during_call_is_noted(self) -> None:
        """Even when psutil imports successfully, individual calls
        may fail on locked-down environments. The detector wraps
        each call so failures land in notes, not exceptions."""
        try:
            import psutil  # noqa: F401  # type: ignore[import-not-found]
        except ImportError:
            self.skipTest("psutil not installed in this environment")

        with mock.patch(
            "psutil.virtual_memory", side_effect=OSError("denied")
        ):
            profile = detect_profile()

        self.assertEqual(profile.ram_total_mb, 0)
        self.assertEqual(profile.ram_available_mb, 0)
        self.assertTrue(
            any("psutil.virtual_memory" in note for note in profile.notes),
            f"expected virtual_memory note, got {profile.notes}",
        )


# ---- Renderers --------------------------------------------------------


class RenderProfileTests(unittest.TestCase):
    def _profile(self) -> HardwareProfile:
        return HardwareProfile(
            detected_at="2026-04-29T12:00:00Z",
            os="Linux",
            os_release="6.0",
            arch="x86_64",
            cpu="Intel Tester",
            logical_cpus=8,
            physical_cpus=4,
            ram_total_mb=16000,
            ram_available_mb=8000,
            python_version="3.11.0",
            platform="Linux-6.0-x86_64",
            notes=["test note"],
        )

    def test_text_includes_every_field(self) -> None:
        rendered = render_profile_text(self._profile())
        self.assertIn("Hardware profile", rendered)
        self.assertIn("Intel Tester", rendered)
        self.assertIn("Logical CPUs: 8", rendered)
        self.assertIn("16000 MB", rendered)
        self.assertIn("3.11.0", rendered)
        self.assertIn("test note", rendered)

    def test_text_handles_unknowns(self) -> None:
        empty = HardwareProfile()
        rendered = render_profile_text(empty)
        # Several fields should fall back to "unknown" or "(unknown)".
        self.assertIn("unknown", rendered.lower())

    def test_markdown_table_shape(self) -> None:
        rendered = render_profile_markdown(self._profile())
        self.assertTrue(rendered.startswith("# Hardware profile"))
        self.assertIn("| Field | Value |", rendered)
        self.assertIn("| OS | `Linux 6.0` |", rendered)
        self.assertIn("| RAM total | 16000 MB |", rendered)
        self.assertIn("## Notes", rendered)


# ---- write_profile ----------------------------------------------------


class WriteProfileTests(unittest.TestCase):
    def test_writes_md_and_json_under_docs_dir(self) -> None:
        profile = HardwareProfile(
            detected_at="t",
            os="Linux",
            arch="x86_64",
            python_version="3.11.0",
            platform="Linux-6.0",
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            md_path, json_path = write_profile(root, profile)
            self.assertEqual(md_path.parent, root / "docs")
            self.assertEqual(md_path.name, DEFAULT_PROFILE_FILENAME)
            self.assertEqual(json_path.name, DEFAULT_PROFILE_JSON_FILENAME)
            md_text = md_path.read_text(encoding="utf-8")
            json_payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertIn("Hardware profile", md_text)
            self.assertEqual(json_payload["os"], "Linux")

    def test_overwrites_existing_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir()
            stale = root / "docs" / DEFAULT_PROFILE_FILENAME
            stale.write_text("# stale", encoding="utf-8")
            md_path, _ = write_profile(
                root, HardwareProfile(os="Linux", python_version="3.11.0")
            )
            self.assertIn("Hardware profile", md_path.read_text(encoding="utf-8"))
            self.assertNotIn("# stale", md_path.read_text(encoding="utf-8"))


# ---- CLI subcommand --------------------------------------------------


class CmdHardwareTests(unittest.TestCase):
    def test_handler_registered(self) -> None:
        from mythic_vibe_cli.commands import cmd_hardware

        self.assertIs(COMMAND_HANDLERS["hardware"], cmd_hardware)

    def test_argparse_accepts_write_flag(self) -> None:
        parser = build_parser()
        ns = parser.parse_args(["hardware", "--write"])
        self.assertEqual(ns.command, "hardware")
        self.assertTrue(ns.write)

    def test_text_output_without_write(self) -> None:
        from mythic_vibe_cli.commands import cmd_hardware

        with tempfile.TemporaryDirectory() as tmp:
            ns = argparse.Namespace(path=tmp, write=False, json=False)
            buf = io.StringIO()
            with redirect_stdout(buf):
                exit_code = cmd_hardware(ns)
        self.assertEqual(exit_code, SUCCESS)
        self.assertIn("Hardware profile", buf.getvalue())
        # No file written.
        self.assertFalse(
            (Path(tmp) / "docs" / DEFAULT_PROFILE_FILENAME).exists()
        )

    def test_json_envelope_without_write(self) -> None:
        from mythic_vibe_cli.commands import cmd_hardware

        with tempfile.TemporaryDirectory() as tmp:
            ns = argparse.Namespace(path=tmp, write=False, json=True)
            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_hardware(ns)
            payload = json.loads(buf.getvalue())
        self.assertEqual(payload["command"], "hardware")
        self.assertFalse(payload["written"])
        self.assertIn("profile", payload)
        self.assertIn("os", payload["profile"])

    def test_write_persists_to_docs(self) -> None:
        from mythic_vibe_cli.commands import cmd_hardware

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ns = argparse.Namespace(path=str(root), write=True, json=True)
            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_hardware(ns)
            payload = json.loads(buf.getvalue())
            self.assertTrue(payload["written"])
            md_path = Path(payload["markdown_path"])
            json_path = Path(payload["json_path"])
            self.assertTrue(md_path.is_file())
            self.assertTrue(json_path.is_file())
            self.assertEqual(md_path.parent, root / "docs")


# ---- Slash catalog + TUI runner --------------------------------------


class HardwareSlashCatalogTests(unittest.TestCase):
    def test_slash_catalog_contains_hardware(self) -> None:
        names = {entry.name for entry in BUILTIN_SLASH_COMMANDS}
        self.assertIn("hardware", names)

    def test_tui_runner_forwards_path_for_hardware(self) -> None:
        from mythic_vibe_cli.tui.runner import command_for_builtin

        with tempfile.TemporaryDirectory() as tmp:
            spec = command_for_builtin("hardware", project_root=Path(tmp))
        self.assertIn("--path", spec.argv)
        self.assertIn(str(Path(tmp)), spec.argv)


# ---- PH-21.9 platform tag detection -----------------------------------


class IsTermuxTests(unittest.TestCase):
    """PH-21.9 — Termux runtime detection.

    Two independent signals: ``TERMUX_VERSION`` env var, and the
    ``/data/data/com.termux/files/usr`` filesystem prefix. Either
    triggers ``is_termux()``. Both being absent returns False, which
    is the expected non-Termux case for every CI runner."""

    def test_returns_true_when_termux_version_env_set(self) -> None:
        with mock.patch.dict("os.environ", {"TERMUX_VERSION": "0.118.0"}, clear=False):
            with mock.patch("os.path.isdir", return_value=False):
                self.assertTrue(is_termux())

    def test_returns_true_when_termux_prefix_dir_exists(self) -> None:
        env_without_termux = {
            k: v for k, v in __import__("os").environ.items()
            if k != "TERMUX_VERSION"
        }
        with mock.patch.dict("os.environ", env_without_termux, clear=True):
            with mock.patch(
                "os.path.isdir",
                lambda p: p == "/data/data/com.termux/files/usr",
            ):
                self.assertTrue(is_termux())

    def test_returns_false_on_normal_host(self) -> None:
        env_without_termux = {
            k: v for k, v in __import__("os").environ.items()
            if k != "TERMUX_VERSION"
        }
        with mock.patch.dict("os.environ", env_without_termux, clear=True):
            with mock.patch("os.path.isdir", return_value=False):
                self.assertFalse(is_termux())


class IsWslTests(unittest.TestCase):
    """PH-21.9 — WSL detection via uname().release substring."""

    def test_detects_wsl1_signature(self) -> None:
        fake_uname = mock.MagicMock()
        fake_uname.release = "4.4.0-19041-Microsoft"
        with mock.patch("platform.uname", return_value=fake_uname):
            self.assertTrue(is_wsl())

    def test_detects_wsl2_signature(self) -> None:
        fake_uname = mock.MagicMock()
        fake_uname.release = "5.15.90.1-microsoft-standard-WSL2"
        with mock.patch("platform.uname", return_value=fake_uname):
            self.assertTrue(is_wsl())

    def test_returns_false_on_native_linux(self) -> None:
        fake_uname = mock.MagicMock()
        fake_uname.release = "6.5.0-21-generic"
        with mock.patch("platform.uname", return_value=fake_uname):
            self.assertFalse(is_wsl())

    def test_returns_false_when_uname_raises(self) -> None:
        with mock.patch("platform.uname", side_effect=OSError("denied")):
            self.assertFalse(is_wsl())


class IsRaspberryPiTests(unittest.TestCase):
    """PH-21.9 — Raspberry Pi detection via /proc/device-tree/model."""

    def test_detects_pi_model_string(self) -> None:
        fake_path = mock.MagicMock()
        fake_path.is_file.return_value = True
        fake_path.read_text.return_value = "Raspberry Pi 5 Model B Rev 1.0"
        with mock.patch("mythic_vibe_cli.hardware.Path", return_value=fake_path):
            self.assertTrue(is_raspberry_pi())

    def test_returns_false_when_model_file_missing(self) -> None:
        fake_path = mock.MagicMock()
        fake_path.is_file.return_value = False
        with mock.patch("mythic_vibe_cli.hardware.Path", return_value=fake_path):
            self.assertFalse(is_raspberry_pi())

    def test_returns_false_when_read_raises(self) -> None:
        fake_path = mock.MagicMock()
        fake_path.is_file.return_value = True
        fake_path.read_text.side_effect = OSError("denied")
        with mock.patch("mythic_vibe_cli.hardware.Path", return_value=fake_path):
            self.assertFalse(is_raspberry_pi())


class DetectPlatformTagsTests(unittest.TestCase):
    """PH-21.9 — composite platform-tag detector.

    The function returns a deterministic ordered list. Adding a new
    tag is additive; the test asserts existing tags appear in the
    documented order so future additions land at well-defined
    positions."""

    def test_no_tags_on_normal_host(self) -> None:
        env_without_termux = {
            k: v for k, v in __import__("os").environ.items()
            if k != "TERMUX_VERSION"
        }
        fake_uname = mock.MagicMock()
        fake_uname.release = "6.5.0-21-generic"
        with mock.patch.dict("os.environ", env_without_termux, clear=True):
            with mock.patch("os.path.isdir", return_value=False):
                with mock.patch("platform.uname", return_value=fake_uname):
                    with mock.patch("platform.machine", return_value="x86_64"):
                        # Pi detector path patch — ensure no-Pi return.
                        fake_pi_path = mock.MagicMock()
                        fake_pi_path.is_file.return_value = False
                        with mock.patch(
                            "mythic_vibe_cli.hardware.Path",
                            return_value=fake_pi_path,
                        ):
                            tags = detect_platform_tags()
        self.assertEqual(tags, [])

    def test_termux_only(self) -> None:
        with mock.patch.dict(
            "os.environ", {"TERMUX_VERSION": "0.118.0"}, clear=False
        ):
            with mock.patch("os.path.isdir", return_value=False):
                fake_uname = mock.MagicMock()
                fake_uname.release = "5.10.0-android"
                with mock.patch("platform.uname", return_value=fake_uname):
                    with mock.patch("platform.machine", return_value="x86_64"):
                        fake_pi = mock.MagicMock()
                        fake_pi.is_file.return_value = False
                        with mock.patch(
                            "mythic_vibe_cli.hardware.Path",
                            return_value=fake_pi,
                        ):
                            tags = detect_platform_tags()
        self.assertIn("termux", tags)

    def test_arm64_emitted_when_machine_is_aarch64(self) -> None:
        env_without_termux = {
            k: v for k, v in __import__("os").environ.items()
            if k != "TERMUX_VERSION"
        }
        with mock.patch.dict("os.environ", env_without_termux, clear=True):
            with mock.patch("os.path.isdir", return_value=False):
                fake_uname = mock.MagicMock()
                fake_uname.release = "6.5.0"
                with mock.patch("platform.uname", return_value=fake_uname):
                    with mock.patch("platform.machine", return_value="aarch64"):
                        fake_pi = mock.MagicMock()
                        fake_pi.is_file.return_value = False
                        with mock.patch(
                            "mythic_vibe_cli.hardware.Path",
                            return_value=fake_pi,
                        ):
                            tags = detect_platform_tags()
        self.assertEqual(tags, ["arm64"])


class HardwareProfileTagsIntegrationTests(unittest.TestCase):
    """PH-21.9 — verify platform_tags propagates through detect_profile,
    to_dict, and renderers."""

    def test_profile_includes_platform_tags_field(self) -> None:
        profile = detect_profile()
        # The field exists on the dataclass and serializes via to_dict.
        self.assertIsInstance(profile.platform_tags, list)
        self.assertIn("platform_tags", profile.to_dict())

    def test_text_renderer_emits_platform_tags_line(self) -> None:
        # Empty case shows "(none)" so the field is always visible.
        empty = HardwareProfile()
        self.assertIn("Platform tags:", render_profile_text(empty))
        self.assertIn("(none)", render_profile_text(empty))

    def test_text_renderer_lists_tags_when_present(self) -> None:
        tagged = HardwareProfile(
            os="Linux",
            python_version="3.11.0",
            platform_tags=["termux", "arm64"],
        )
        rendered = render_profile_text(tagged)
        self.assertIn("termux", rendered)
        self.assertIn("arm64", rendered)

    def test_markdown_renderer_emits_platform_tags_row(self) -> None:
        empty = HardwareProfile()
        md = render_profile_markdown(empty)
        self.assertIn("| Platform tags |", md)
        self.assertIn("(none)", md)

    def test_markdown_renderer_lists_tags_when_present(self) -> None:
        tagged = HardwareProfile(
            os="Linux",
            python_version="3.11.0",
            platform_tags=["wsl"],
        )
        md = render_profile_markdown(tagged)
        self.assertIn("| Platform tags | wsl |", md)


if __name__ == "__main__":
    unittest.main()

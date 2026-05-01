"""Tests for PH-10 Slice 10.1 — entry-point discovery + install."""

from __future__ import annotations

import argparse
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from mythic_vibe_cli.exit_codes import SUCCESS, USER_INPUT_ERROR
from mythic_vibe_cli.plugins.entry_points import (
    ENTRY_POINT_GROUP,
    EntryPointRecord,
    _split_value,
    discover_entry_points,
    find_entry_point,
)
from mythic_vibe_cli.plugins.registry import PluginRegistry


def _fake_metadata(entries: list[SimpleNamespace], group: str = ENTRY_POINT_GROUP):
    """Build a fake importlib.metadata stand-in returning ``entries``
    when called with ``group=group``, else an empty tuple."""

    def entry_points_fn(group: str | None = None):  # noqa: ANN001 — test helper
        if group is None:
            return {ENTRY_POINT_GROUP: tuple(entries)}
        if group == ENTRY_POINT_GROUP:
            return tuple(entries)
        return ()

    return SimpleNamespace(entry_points=entry_points_fn)


def _ep(
    name: str,
    value: str,
    *,
    distribution: str = "",
    version: str = "",
) -> SimpleNamespace:
    """Synthetic entry-point object shaped like importlib.metadata's."""
    dist = (
        SimpleNamespace(name=distribution, version=version)
        if distribution
        else None
    )
    return SimpleNamespace(name=name, value=value, dist=dist)


# ---- _split_value -----------------------------------------------------


class SplitValueTests(unittest.TestCase):
    def test_module_attr(self) -> None:
        self.assertEqual(_split_value("pkg.mod:obj"), ("pkg.mod", "obj"))

    def test_bare_module(self) -> None:
        self.assertEqual(_split_value("pkg.mod"), ("pkg.mod", ""))

    def test_strips_whitespace(self) -> None:
        self.assertEqual(_split_value("  pkg.mod : obj "), ("pkg.mod", "obj"))


# ---- EntryPointRecord -------------------------------------------------


class EntryPointRecordTests(unittest.TestCase):
    def test_entrypoint_string_with_attr(self) -> None:
        record = EntryPointRecord(
            name="x", value="pkg.mod:obj", module="pkg.mod", attr="obj"
        )
        self.assertEqual(record.entrypoint_string, "pkg.mod:obj")

    def test_entrypoint_string_bare_module(self) -> None:
        record = EntryPointRecord(
            name="x", value="pkg.mod", module="pkg.mod", attr=""
        )
        self.assertEqual(record.entrypoint_string, "pkg.mod")

    def test_to_dict_round_trip(self) -> None:
        record = EntryPointRecord(
            name="my_plugin",
            value="pkg.mod:obj",
            module="pkg.mod",
            attr="obj",
            distribution="pkg",
            version="1.2.3",
        )
        payload = record.to_dict()
        self.assertEqual(payload["name"], "my_plugin")
        self.assertEqual(payload["entrypoint_string"], "pkg.mod:obj")
        self.assertEqual(payload["distribution"], "pkg")


# ---- discover_entry_points -------------------------------------------


class DiscoverEntryPointsTests(unittest.TestCase):
    def test_empty_when_no_entries(self) -> None:
        fake = _fake_metadata([])
        records = discover_entry_points(metadata_module=fake)
        self.assertEqual(records, [])

    def test_returns_records_for_each_entry(self) -> None:
        fake = _fake_metadata(
            [
                _ep(
                    "alpha",
                    "alpha_pkg.mod:plugin",
                    distribution="alpha-pkg",
                    version="0.1",
                ),
                _ep("beta", "beta_pkg.mod:plugin"),
            ]
        )
        records = discover_entry_points(metadata_module=fake)
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0].name, "alpha")
        self.assertEqual(records[0].entrypoint_string, "alpha_pkg.mod:plugin")
        self.assertEqual(records[0].distribution, "alpha-pkg")
        self.assertEqual(records[0].version, "0.1")
        self.assertEqual(records[1].name, "beta")
        self.assertEqual(records[1].distribution, "")  # no dist info

    def test_skips_malformed_entries(self) -> None:
        fake = _fake_metadata(
            [
                _ep("", "pkg:obj"),  # missing name
                _ep("ok", ""),  # missing value
                _ep("good", "pkg.mod:obj"),
            ]
        )
        records = discover_entry_points(metadata_module=fake)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].name, "good")

    def test_falls_back_to_dict_signature(self) -> None:
        """Older Python signatures return a dict; the discoverer
        handles both shapes."""

        def older_signature_fn(group: str | None = None):  # noqa: ANN001 — test helper
            if group is not None:
                raise TypeError("group kwarg not supported in this version")
            return {ENTRY_POINT_GROUP: (_ep("x", "pkg:obj"),)}

        fake = SimpleNamespace(entry_points=older_signature_fn)
        records = discover_entry_points(metadata_module=fake)
        self.assertEqual(len(records), 1)

    def test_swallows_metadata_exceptions(self) -> None:
        """A broken environment shouldn't crash discovery."""

        def angry_fn(group: str | None = None):  # noqa: ANN001 — test helper
            raise RuntimeError("metadata exploded")

        fake = SimpleNamespace(entry_points=angry_fn)
        records = discover_entry_points(metadata_module=fake)
        self.assertEqual(records, [])


# ---- find_entry_point ------------------------------------------------


class FindEntryPointTests(unittest.TestCase):
    def test_match_by_name(self) -> None:
        fake = _fake_metadata([_ep("alpha", "pkg:obj"), _ep("beta", "pkg:obj2")])
        record = find_entry_point("alpha", metadata_module=fake)
        self.assertIsNotNone(record)
        assert record is not None
        self.assertEqual(record.name, "alpha")

    def test_match_by_module_attr(self) -> None:
        fake = _fake_metadata([_ep("alpha", "pkg.mod:obj")])
        record = find_entry_point("pkg.mod:obj", metadata_module=fake)
        self.assertIsNotNone(record)

    def test_returns_none_for_unknown(self) -> None:
        fake = _fake_metadata([_ep("alpha", "pkg:obj")])
        self.assertIsNone(find_entry_point("ghost", metadata_module=fake))

    def test_blank_input_returns_none(self) -> None:
        fake = _fake_metadata([_ep("alpha", "pkg:obj")])
        self.assertIsNone(find_entry_point("", metadata_module=fake))


# ---- cmd_plugin_discover ---------------------------------------------


class CmdPluginDiscoverTests(unittest.TestCase):
    def test_empty_state(self) -> None:
        from mythic_vibe_cli.commands import cmd_plugin_discover

        with mock.patch(
            "mythic_vibe_cli.plugins.entry_points.discover_entry_points",
            return_value=[],
        ):
            ns = argparse.Namespace(path=".", json=True)
            buf = io.StringIO()
            with redirect_stdout(buf):
                exit_code = cmd_plugin_discover(ns)
            payload = json.loads(buf.getvalue())
        self.assertEqual(exit_code, SUCCESS)
        self.assertEqual(payload["count"], 0)
        self.assertEqual(payload["entry_points"], [])

    def test_lists_records(self) -> None:
        from mythic_vibe_cli.commands import cmd_plugin_discover

        records = [
            EntryPointRecord(
                name="alpha",
                value="pkg.mod:obj",
                module="pkg.mod",
                attr="obj",
                distribution="alpha-pkg",
                version="1.0",
            )
        ]
        with mock.patch(
            "mythic_vibe_cli.plugins.entry_points.discover_entry_points",
            return_value=records,
        ):
            ns = argparse.Namespace(path=".", json=True)
            buf = io.StringIO()
            with redirect_stdout(buf):
                exit_code = cmd_plugin_discover(ns)
            payload = json.loads(buf.getvalue())
        self.assertEqual(exit_code, SUCCESS)
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["entry_points"][0]["name"], "alpha")


# ---- cmd_plugin_install ----------------------------------------------


class CmdPluginInstallTests(unittest.TestCase):
    def test_missing_argument(self) -> None:
        from mythic_vibe_cli.commands import cmd_plugin_install

        ns = argparse.Namespace(path=".", name="", json=True, dry_run=False)
        from contextlib import redirect_stderr

        with redirect_stderr(io.StringIO()):
            with redirect_stdout(io.StringIO()):
                exit_code = cmd_plugin_install(ns)
        self.assertEqual(exit_code, USER_INPUT_ERROR)

    def test_unknown_entrypoint(self) -> None:
        from mythic_vibe_cli.commands import cmd_plugin_install

        with mock.patch(
            "mythic_vibe_cli.plugins.entry_points.find_entry_point",
            return_value=None,
        ):
            from contextlib import redirect_stderr

            ns = argparse.Namespace(
                path=".", name="ghost", json=True, dry_run=False
            )
            with redirect_stderr(io.StringIO()):
                with redirect_stdout(io.StringIO()):
                    exit_code = cmd_plugin_install(ns)
        self.assertEqual(exit_code, USER_INPUT_ERROR)

    def test_install_writes_to_registry(self) -> None:
        from mythic_vibe_cli.commands import cmd_plugin_install

        record = EntryPointRecord(
            name="alpha",
            value="pkg.mod:obj",
            module="pkg.mod",
            attr="obj",
            distribution="alpha-pkg",
            version="1.0",
        )
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch(
                "mythic_vibe_cli.plugins.entry_points.find_entry_point",
                return_value=record,
            ):
                ns = argparse.Namespace(
                    path=tmp,
                    name="alpha",
                    json=True,
                    dry_run=False,
                )
                buf = io.StringIO()
                with redirect_stdout(buf):
                    exit_code = cmd_plugin_install(ns)
                payload = json.loads(buf.getvalue())
            self.assertEqual(exit_code, SUCCESS)
            self.assertTrue(payload["added"])
            registry = PluginRegistry(Path(tmp))
            records = registry.list()
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].entrypoint, "pkg.mod:obj")
            self.assertEqual(records[0].version, "1.0")

    def test_install_dry_run_skips_write(self) -> None:
        from mythic_vibe_cli.commands import cmd_plugin_install

        record = EntryPointRecord(
            name="alpha",
            value="pkg.mod:obj",
            module="pkg.mod",
            attr="obj",
        )
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch(
                "mythic_vibe_cli.plugins.entry_points.find_entry_point",
                return_value=record,
            ):
                ns = argparse.Namespace(
                    path=tmp,
                    name="alpha",
                    json=True,
                    dry_run=True,
                )
                with redirect_stdout(io.StringIO()):
                    exit_code = cmd_plugin_install(ns)
            self.assertEqual(exit_code, SUCCESS)
            registry = PluginRegistry(Path(tmp))
            self.assertEqual(registry.list(), [])  # registry untouched

    def test_install_idempotent(self) -> None:
        from mythic_vibe_cli.commands import cmd_plugin_install

        record = EntryPointRecord(
            name="alpha",
            value="pkg.mod:obj",
            module="pkg.mod",
            attr="obj",
        )
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch(
                "mythic_vibe_cli.plugins.entry_points.find_entry_point",
                return_value=record,
            ):
                ns = argparse.Namespace(
                    path=tmp, name="alpha", json=True, dry_run=False
                )
                with redirect_stdout(io.StringIO()):
                    cmd_plugin_install(ns)
                buf = io.StringIO()
                with redirect_stdout(buf):
                    cmd_plugin_install(ns)
                payload = json.loads(buf.getvalue())
            self.assertFalse(payload["added"])  # second call is a no-op
            registry = PluginRegistry(Path(tmp))
            self.assertEqual(len(registry.list()), 1)


# ---- argparse --------------------------------------------------------


class PluginEntryPointArgparseTests(unittest.TestCase):
    def test_discover_parses(self) -> None:
        from mythic_vibe_cli.app import build_parser

        parser = build_parser()
        ns = parser.parse_args(["plugin", "discover"])
        self.assertEqual(ns.command, "plugin")
        self.assertEqual(ns.plugin_command, "discover")

    def test_install_parses(self) -> None:
        from mythic_vibe_cli.app import build_parser

        parser = build_parser()
        ns = parser.parse_args(["plugin", "install", "alpha"])
        self.assertEqual(ns.plugin_command, "install")
        self.assertEqual(ns.name, "alpha")


if __name__ == "__main__":
    unittest.main()

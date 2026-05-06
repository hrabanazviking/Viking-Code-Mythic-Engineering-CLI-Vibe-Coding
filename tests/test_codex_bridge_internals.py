"""PH-25.2 — Direct coverage of codex_bridge internals.

The packet-creation flow has solid integration tests already
(tests/test_config_and_bridge.py). This module exercises the
helper paths existing tests skip:

- Output-format string mappings (claude / aider / gemini / roo /
  goose / copy-paste / generic fallback)
- ``_ingest_text_from_metadata`` fallback chain
  (packet_path → .md sibling → .json sibling → inline text →
  FileNotFoundError)
- ``_next_packet_id`` malformed-suffix handling
- ``_parse_packet_metadata`` line-by-line tolerance

Goal: take ``codex_bridge.py`` from 82% to 90%+.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from mythic_vibe_cli.codex_bridge import PacketBuilder


class OutputFormatMappingTests(unittest.TestCase):
    """``_required_output_format`` covers a tiny lookup table —
    no integration test ever passes any of the alternate formats so
    the lookup branches are uncovered."""

    def _builder(self) -> PacketBuilder:
        return PacketBuilder(Path(tempfile.gettempdir()))

    def test_json_format_returns_strict_json(self) -> None:
        b = self._builder()
        self.assertEqual(b._required_output_format("json"), "strict JSON")

    def test_claude_format_returns_claude_task(self) -> None:
        self.assertEqual(self._builder()._required_output_format("claude"), "Claude Code task")

    def test_aider_format_returns_aider_prompt(self) -> None:
        self.assertEqual(self._builder()._required_output_format("aider"), "Aider prompt")

    def test_gemini_format_returns_gemini_task(self) -> None:
        self.assertEqual(self._builder()._required_output_format("gemini"), "Gemini CLI task")

    def test_roo_format_returns_roo_prompt(self) -> None:
        self.assertEqual(self._builder()._required_output_format("roo"), "Roo prompt")

    def test_goose_format_returns_goose_prompt(self) -> None:
        self.assertEqual(self._builder()._required_output_format("goose"), "Goose prompt")

    def test_copy_paste_format_returns_chatgpt_label(self) -> None:
        self.assertEqual(
            self._builder()._required_output_format("copy-paste"),
            "ChatGPT/Codex copy-paste",
        )

    def test_unknown_format_falls_back_to_generic_markdown(self) -> None:
        self.assertEqual(
            self._builder()._required_output_format("not-a-real-format"),
            "generic Markdown",
        )

    def test_format_lookup_is_case_insensitive(self) -> None:
        """The function lower-cases its input — uppercase passes."""
        self.assertEqual(self._builder()._required_output_format("CLAUDE"), "Claude Code task")
        self.assertEqual(self._builder()._required_output_format("Aider"), "Aider prompt")


class IngestTextFromMetadataTests(unittest.TestCase):
    """The ingestion fallback chain has 4 paths + a final raise.
    Existing tests only ever pass markdown sources so most branches
    are uncovered."""

    def test_relative_packet_path_resolves_against_source_parent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packet_md = root / "actual.md"
            packet_md.write_text("# Real packet body", encoding="utf-8")
            source_json = root / "source.json"
            source_json.write_text(json.dumps({"packet_path": "actual.md"}), encoding="utf-8")

            builder = PacketBuilder(root)
            text = builder._ingest_text_from_metadata(
                source_json, {"packet_path": "actual.md"}
            )
        self.assertIn("Real packet body", text)

    def test_md_sidecar_takes_precedence_over_inline_text(self) -> None:
        """When ``packet_path`` is missing but a ``.md`` sidecar
        exists next to the source, the sidecar wins over inline."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_json = root / "source.json"
            source_json.write_text("{}", encoding="utf-8")
            sidecar_md = root / "source.md"
            sidecar_md.write_text("# From sidecar", encoding="utf-8")

            builder = PacketBuilder(root)
            text = builder._ingest_text_from_metadata(
                source_json, {"text": "inline ignored"}
            )
        self.assertEqual(text, "# From sidecar")

    def test_json_sidecar_takes_precedence_over_inline_text(self) -> None:
        """When the .md sibling is missing but a .json sibling
        exists, the .json sibling wins over inline text."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sibling_json = root / "src.json"
            sibling_json.write_text("{\"a\": 1}", encoding="utf-8")
            # Source path whose .md sibling does NOT exist but
            # .json sibling does.
            source_dummy = root / "src.txt"
            builder = PacketBuilder(root)
            text = builder._ingest_text_from_metadata(
                source_dummy, {"text": "inline ignored"}
            )
        self.assertIn("\"a\": 1", text)

    def test_inline_text_used_when_no_sidecars_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "ghost.json"
            # No file written — but ``_ingest_text_from_metadata``
            # only checks the with-suffix paths against actual file
            # existence, which won't find anything either.
            builder = PacketBuilder(root)
            text = builder._ingest_text_from_metadata(
                source, {"text": "inline body"}
            )
        self.assertEqual(text, "inline body")

    def test_raises_file_not_found_when_no_payload_anywhere(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "nothing.json"
            builder = PacketBuilder(root)
            with self.assertRaises(FileNotFoundError):
                builder._ingest_text_from_metadata(source, {})


class NextPacketIdTests(unittest.TestCase):
    """``_next_packet_id`` parses existing packet ids and handles
    malformed suffixes by skipping (not crashing)."""

    def test_first_id_when_directory_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            builder = PacketBuilder(Path(tmp))
            self.assertEqual(builder._next_packet_id(), "PKT-000001")

    def test_skips_malformed_suffix_in_existing_packet_ids(self) -> None:
        """A leftover .meta.json with a non-numeric suffix must not
        crash the next-id calculation."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            builder = PacketBuilder(root)
            builder.packet_dir.mkdir(parents=True, exist_ok=True)
            # Two records — one valid, one with non-numeric suffix.
            (builder.packet_dir / "PKT-000005.meta.json").write_text(
                json.dumps({"packet_id": "PKT-000005", "created_at": "x", "phase": "p", "role": "r", "task": "t", "audience": "a", "packet_path": "x", "metadata_path": "y", "output_format": "markdown"}),
                encoding="utf-8",
            )
            (builder.packet_dir / "PKT-XYZABC.meta.json").write_text(
                json.dumps({"packet_id": "PKT-XYZABC", "created_at": "x", "phase": "p", "role": "r", "task": "t", "audience": "a", "packet_path": "x", "metadata_path": "y", "output_format": "markdown"}),
                encoding="utf-8",
            )
            next_id = builder._next_packet_id()
        # Only PKT-000005 should have been counted; next is PKT-000006.
        self.assertEqual(next_id, "PKT-000006")


class IngestPacketRoundTripTests(unittest.TestCase):
    """End-to-end ingest with a JSON source — exercises
    ``_read_ingest_source`` JSON branch + ``_write_ingested_record``
    + the packet-text fallback chain together."""

    def test_ingest_from_json_source_with_inline_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.json"
            source.write_text(
                json.dumps({
                    "phase": "build",
                    "role": "Forge Worker",
                    "task": "round-trip ingest test",
                    "audience": "advanced",
                    "text": "## Body\nbody body\n",
                }),
                encoding="utf-8",
            )
            builder = PacketBuilder(root)
            record = builder.ingest_packet(source)
            self.assertTrue(record.packet_id.startswith("PKT-"))
            self.assertEqual(record.task, "round-trip ingest test")
            self.assertEqual(record.role, "Forge Worker")
            # Canonical packet file in the packet dir holds the
            # inline text. Suffix may vary; check via glob.
            packet_dir = builder.packet_dir
            canonical_files = list(packet_dir.glob(f"{record.packet_id}.*"))
            # Filter out the metadata sidecars.
            body_files = [
                p for p in canonical_files if p.suffix not in {".json"}
            ] + [p for p in canonical_files if p.name.endswith(".meta.json")]
            self.assertTrue(any("Body" in p.read_text(encoding="utf-8") for p in body_files))

    def test_ingest_raises_for_missing_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            builder = PacketBuilder(Path(tmp))
            with self.assertRaises(FileNotFoundError):
                builder.ingest_packet(Path(tmp) / "nope.json")


if __name__ == "__main__":
    unittest.main()

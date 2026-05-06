"""PH-26.3 — property tests for ``runtime/atomic_write.atomic_write_text``.

Example-based tests cover the deterministic happy + cleanup paths
(``tests/test_atomic_write.py``). Hypothesis explores the long
tail of arbitrary Unicode + newline patterns to verify the PH-24.4
byte-stable invariant holds across a much wider input space than
hand-picked examples.

Invariants under test:

1. **Byte-exact round-trip.** ``read_bytes()`` after
   ``atomic_write_text(content)`` must equal ``content.encode("utf-8")``.
2. **No newline translation.** Content with ``\\n`` separators must
   round-trip to the same ``\\n`` separators on every platform —
   no Windows-style ``\\r\\n`` injection.
3. **No partial-write artifacts.** A successful write leaves the
   target file with the exact final content; no ``.tmp`` siblings
   remain in the directory.

Hypothesis stays strictly pure-Python, MPL-licensed, test-time only.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import given, settings, strategies as st  # noqa: E402

from mythic_vibe_cli.runtime.atomic_write import atomic_write_text  # noqa: E402


# Strategy for arbitrary text — full BMP including newlines, tabs,
# emoji, runes, RTL marks. Cap size at 4 KB so test runs stay fast.
_text_payload = st.text(min_size=0, max_size=4096)


@given(content=_text_payload)
@settings(max_examples=100)
def test_byte_exact_round_trip(content: str) -> None:
    """Whatever bytes we wrote, ``read_bytes`` returns identically.
    Catches any platform-specific newline mangling."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "out.txt"
        atomic_write_text(target, content)
        actual = target.read_bytes()
        expected = content.encode("utf-8")
        assert actual == expected


@given(content=st.text(
    alphabet="abc\n\r\t",  # Heavy on newline-style chars
    min_size=0, max_size=512,
))
@settings(max_examples=100)
def test_newline_preservation_under_arbitrary_eol_chars(content: str) -> None:
    """Content mixing \\n, \\r, \\t in any combination must
    round-trip byte-exact. This is the regression test for the
    PH-24.4 Windows newline-translation defect."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "out.txt"
        atomic_write_text(target, content)
        actual = target.read_bytes()
        expected = content.encode("utf-8")
        assert actual == expected, (
            f"newline mangling: content={content!r} -> bytes={actual!r}, "
            f"expected={expected!r}"
        )


@given(content=_text_payload)
@settings(max_examples=50)
def test_no_orphan_tmp_files_after_successful_write(content: str) -> None:
    """A clean atomic write leaves the target + nothing else.
    The .tmp sibling must be cleaned up via os.replace."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        target = root / "out.txt"
        atomic_write_text(target, content)
        children = list(root.iterdir())
        # Just the target — no leftover .tmp.
        assert len(children) == 1
        assert children[0].name == "out.txt"


@given(
    content=_text_payload,
    encoding=st.sampled_from(["utf-8", "utf-16-le", "utf-16-be"]),
)
@settings(max_examples=50)
def test_explicit_encoding_round_trips(content: str, encoding: str) -> None:
    """Explicit non-utf-8 encodings must round-trip exactly to
    their corresponding byte sequence — no double-decoding."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "out.txt"
        try:
            content.encode(encoding)
        except UnicodeEncodeError:
            # Skip — not all content is valid in all encodings.
            pytest.skip(f"content not encodable as {encoding}")
        atomic_write_text(target, content, encoding=encoding)
        actual = target.read_bytes()
        expected = content.encode(encoding)
        assert actual == expected

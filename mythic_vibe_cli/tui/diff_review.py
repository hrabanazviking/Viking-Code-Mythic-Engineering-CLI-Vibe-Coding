"""Diff review screen — per-hunk accept/reject for AI-generated changes.

PH-04 slice 4.5. Implements Law 4 ("AI output is never automatically
trusted") at the TUI level: every hunk in an AI-suggested patch is
displayed for explicit operator review. Decisions land in a typed
:class:`DiffReviewSession` that callers can persist or feed into a
future apply step.

This slice ships the *review* half (parser + screen + decision
state). Applying accepted hunks to disk is a separate concern and
is deliberately out of scope — slice 4.5 records what the operator
chose; a follow-on slice can wire the actual apply.

The parser handles standard unified-diff text (the same format
``git diff`` and ``diff -u`` produce). It does not handle binary
diffs, mode changes, or rename markers; those skip cleanly without
breaking the parser.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any, Literal


# ---- Data layer ---------------------------------------------------------


DiffLineKind = Literal["context", "addition", "deletion", "header"]
HunkDecision = Literal["pending", "accepted", "rejected", "skipped"]

_VALID_DECISIONS: tuple[HunkDecision, ...] = (
    "pending",
    "accepted",
    "rejected",
    "skipped",
)


@dataclass(frozen=True)
class DiffLine:
    """One line within a hunk, classified for colour-coded rendering."""

    kind: DiffLineKind
    text: str

    def to_dict(self) -> dict[str, str]:
        return {"kind": self.kind, "text": self.text}


@dataclass(frozen=True)
class DiffHunk:
    """One unified-diff hunk (an ``@@`` header plus its body)."""

    file_path: str
    header: str
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: tuple[DiffLine, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_path": self.file_path,
            "header": self.header,
            "old_start": self.old_start,
            "old_count": self.old_count,
            "new_start": self.new_start,
            "new_count": self.new_count,
            "lines": [line.to_dict() for line in self.lines],
        }


@dataclass
class DiffReviewSession:
    """Mutable orchestration state for one operator review pass.

    The session owns a list of decisions parallel to the hunk list.
    Tests and consumers manipulate it through :meth:`record_decision`,
    :meth:`advance`, and :meth:`retreat`.
    """

    hunks: tuple[DiffHunk, ...]
    decisions: list[HunkDecision] = field(default_factory=list)
    current_index: int = 0

    def __post_init__(self) -> None:
        if not self.decisions:
            self.decisions = ["pending"] * len(self.hunks)
        elif len(self.decisions) != len(self.hunks):
            raise ValueError(
                "DiffReviewSession.decisions length must match hunks length"
            )

    @property
    def total(self) -> int:
        return len(self.hunks)

    @property
    def decided_count(self) -> int:
        return sum(1 for d in self.decisions if d != "pending")

    @property
    def is_complete(self) -> bool:
        return self.total == 0 or self.decided_count == self.total

    @property
    def current_hunk(self) -> DiffHunk | None:
        if not self.hunks:
            return None
        return self.hunks[self.current_index]

    def record_decision(self, decision: HunkDecision) -> None:
        """Set the current hunk's decision, validating against the
        canonical set. Does not advance the index — callers chain
        :meth:`advance` if they want move-to-next semantics."""
        if decision not in _VALID_DECISIONS:
            raise ValueError(
                f"Unknown hunk decision: {decision!r}. "
                f"Valid: {', '.join(_VALID_DECISIONS)}"
            )
        if not self.hunks:
            return
        self.decisions[self.current_index] = decision

    def advance(self) -> bool:
        """Move to the next hunk. Returns True when the index moved,
        False when already at the last hunk (caller can use this to
        decide whether to close the screen)."""
        if self.current_index + 1 >= self.total:
            return False
        self.current_index += 1
        return True

    def retreat(self) -> bool:
        """Move to the previous hunk. Returns False when already at
        the first hunk."""
        if self.current_index <= 0:
            return False
        self.current_index -= 1
        return True

    def accepted_hunks(self) -> tuple[DiffHunk, ...]:
        """Return only the hunks the operator accepted (ordered by
        their original position)."""
        return tuple(
            hunk
            for hunk, decision in zip(self.hunks, self.decisions)
            if decision == "accepted"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "hunks": [hunk.to_dict() for hunk in self.hunks],
            "decisions": list(self.decisions),
            "current_index": self.current_index,
            "decided_count": self.decided_count,
            "is_complete": self.is_complete,
        }


# ---- Parser -------------------------------------------------------------

# Match a hunk header like:  @@ -12,7 +12,9 @@ optional context
_HUNK_HEADER_RE = re.compile(
    r"^@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@(?:\s+(.*))?$"
)
# Match the file-path lines: `+++ b/path/to/file` or `+++ path/to/file`
_NEW_FILE_RE = re.compile(r"^\+\+\+\s+(?:b/)?(.+)$")
# Match the old-file marker: `--- a/path/to/file` (we only use the new path)
_OLD_FILE_RE = re.compile(r"^---\s+(?:a/)?(.+)$")


def parse_unified_diff(text: str) -> list[DiffHunk]:
    """Parse unified-diff ``text`` into a list of :class:`DiffHunk`.

    Robust to:
    - empty input → empty list
    - non-diff text → empty list (we just ignore lines that don't
      match diff conventions)
    - multi-file diffs (each ``+++ ...`` resets the active file path)
    - hunk headers without explicit count (``@@ -N +N @@`` ⇒ count=1)
    - mode-change / rename markers (silently skipped)
    - trailing partial hunks (no closing line) → emitted as-is

    Not supported (silently skipped):
    - binary patches
    - "no newline at end of file" markers (rendered as context)
    """
    if not text.strip():
        return []

    lines = text.splitlines()
    hunks: list[DiffHunk] = []

    current_file = "unknown"
    current_hunk_header: str | None = None
    current_hunk_old_start = 0
    current_hunk_old_count = 0
    current_hunk_new_start = 0
    current_hunk_new_count = 0
    current_hunk_body: list[DiffLine] = []

    def flush_current_hunk() -> None:
        nonlocal current_hunk_header, current_hunk_body
        if current_hunk_header is None:
            return
        hunks.append(
            DiffHunk(
                file_path=current_file,
                header=current_hunk_header,
                old_start=current_hunk_old_start,
                old_count=current_hunk_old_count,
                new_start=current_hunk_new_start,
                new_count=current_hunk_new_count,
                lines=tuple(current_hunk_body),
            )
        )
        current_hunk_header = None
        current_hunk_body = []

    for line in lines:
        # New-file marker: reset active file path.
        new_match = _NEW_FILE_RE.match(line)
        if new_match:
            flush_current_hunk()
            current_file = new_match.group(1).strip() or "unknown"
            continue
        # Old-file marker: ignore (we only need the new path).
        if _OLD_FILE_RE.match(line):
            continue
        # Hunk header.
        header_match = _HUNK_HEADER_RE.match(line)
        if header_match:
            flush_current_hunk()
            old_start = int(header_match.group(1))
            old_count = int(header_match.group(2)) if header_match.group(2) else 1
            new_start = int(header_match.group(3))
            new_count = int(header_match.group(4)) if header_match.group(4) else 1
            current_hunk_header = line
            current_hunk_old_start = old_start
            current_hunk_old_count = old_count
            current_hunk_new_start = new_start
            current_hunk_new_count = new_count
            continue
        # In-hunk body line.
        if current_hunk_header is None:
            # Not inside a hunk; skip (mode changes, "diff --git", etc.).
            continue
        if line.startswith("+") and not line.startswith("+++"):
            current_hunk_body.append(DiffLine(kind="addition", text=line[1:]))
        elif line.startswith("-") and not line.startswith("---"):
            current_hunk_body.append(DiffLine(kind="deletion", text=line[1:]))
        elif line.startswith(" "):
            current_hunk_body.append(DiffLine(kind="context", text=line[1:]))
        elif line.startswith(r"\ "):
            # "\ No newline at end of file" — render as context with the
            # marker preserved so the operator sees it.
            current_hunk_body.append(DiffLine(kind="context", text=line))
        else:
            # An empty separator line inside a hunk (rare, but
            # tolerable) — treat as context.
            current_hunk_body.append(DiffLine(kind="context", text=line))

    flush_current_hunk()
    return hunks


# ---- Screen (PH-04 slice 4.5) ------------------------------------------

# The screen is imported lazily so non-Textual contexts (e.g. unit tests
# of the parser alone) don't pay the Textual import cost.

DIFF_REVIEW_BINDINGS_TEXT = (
    "a accept · r reject · s skip · j/down next · k/up prev · q quit · ? help"
)


def _format_hunk_for_review(hunk: DiffHunk) -> str:
    """Render one hunk with Rich tags (green additions, red deletions)."""
    lines = [
        f"[b]{hunk.file_path}[/b]",
        f"[dim]{hunk.header}[/dim]",
        "",
    ]
    for line in hunk.lines:
        if line.kind == "addition":
            lines.append(f"[green]+ {line.text}[/green]")
        elif line.kind == "deletion":
            lines.append(f"[red]- {line.text}[/red]")
        else:
            lines.append(f"  {line.text}")
    return "\n".join(lines)


def _format_review_progress(session: DiffReviewSession) -> str:
    """Header line for the review screen."""
    if session.total == 0:
        return "[dim]No hunks to review.[/dim]"
    accepted = sum(1 for d in session.decisions if d == "accepted")
    rejected = sum(1 for d in session.decisions if d == "rejected")
    skipped = sum(1 for d in session.decisions if d == "skipped")
    pending = sum(1 for d in session.decisions if d == "pending")
    return (
        f"Hunk {session.current_index + 1} / {session.total}  ·  "
        f"[green]{accepted} accepted[/green]  ·  "
        f"[red]{rejected} rejected[/red]  ·  "
        f"[yellow]{skipped} skipped[/yellow]  ·  "
        f"[dim]{pending} pending[/dim]"
    )


def _lazy_textual_imports() -> tuple[Any, Any, Any, Any, Any, Any, Any]:
    """Resolve the Textual symbols only when the screen is actually
    instantiated. Lets the parser + dataclasses be importable without
    Textual installed (matters for non-TUI consumers and for tests of
    the parser alone)."""
    from textual.app import ComposeResult  # noqa: WPS433
    from textual.binding import Binding  # noqa: WPS433
    from textual.containers import Vertical  # noqa: WPS433
    from textual.screen import Screen  # noqa: WPS433
    from textual.widgets import Footer, Header, Static  # noqa: WPS433

    return ComposeResult, Binding, Vertical, Screen, Footer, Header, Static


try:
    (
        _ComposeResult,
        _Binding,
        _Vertical,
        _Screen,
        _Footer,
        _Header,
        _Static,
    ) = _lazy_textual_imports()
except ImportError:  # pragma: no cover - exercised when Textual is absent
    _Screen = None  # type: ignore[assignment]


if _Screen is not None:

    class DiffReviewScreen(_Screen):  # type: ignore[misc, valid-type]
        """Per-hunk accept / reject screen.

        Shows the current hunk with green / red highlighting and a
        progress header. Each keypress updates the
        :class:`DiffReviewSession` that the screen wraps. The screen
        does *not* apply the accepted hunks to disk — that is a
        deliberate slice-4.5 boundary (see module docstring).

        Bindings:

        * ``a`` — accept current hunk and advance
        * ``r`` — reject current hunk and advance
        * ``s`` — skip current hunk and advance
        * ``j`` / ``down`` — next hunk (no decision change)
        * ``k`` / ``up``   — previous hunk
        * ``q`` / ``escape`` — pop the screen
        * ``?`` — toggle the inline bindings hint
        """

        BINDINGS = [
            _Binding("a", "accept", "Accept"),
            _Binding("r", "reject", "Reject"),
            _Binding("s", "skip", "Skip"),
            _Binding("j", "next", "Next"),
            _Binding("down", "next", "Next", show=False),
            _Binding("k", "prev", "Prev"),
            _Binding("up", "prev", "Prev", show=False),
            _Binding("question_mark", "toggle_help", "Help"),
            _Binding("q", "app.pop_screen", "Quit"),
            _Binding("escape", "app.pop_screen", "Quit", show=False),
        ]

        DEFAULT_CSS = """
        DiffReviewScreen {
            layout: vertical;
        }

        #diff-review-body {
            padding: 1 1;
            height: 1fr;
        }

        #diff-review-header {
            padding: 0 1;
            height: auto;
        }

        #diff-review-hunk {
            border: round $secondary;
            padding: 1 2;
            height: 1fr;
        }

        #diff-review-help {
            padding: 0 1;
            height: auto;
            color: $text-muted;
        }
        """

        def __init__(self, session: DiffReviewSession) -> None:
            super().__init__()
            self.session = session
            self._show_help = False
            self._header_widget: Any = None
            self._hunk_widget: Any = None
            self._help_widget: Any = None

        def compose(self) -> Any:
            yield _Header(show_clock=False)
            self._header_widget = _Static(id="diff-review-header")
            self._hunk_widget = _Static(id="diff-review-hunk")
            self._hunk_widget.border_title = "Diff hunk"
            self._help_widget = _Static(id="diff-review-help")
            with _Vertical(id="diff-review-body"):
                yield self._header_widget
                yield self._hunk_widget
                yield self._help_widget
            yield _Footer()

        def on_mount(self) -> None:
            self._refresh()

        def _refresh(self) -> None:
            if self._header_widget is None or self._hunk_widget is None:
                return
            self._header_widget.update(_format_review_progress(self.session))
            current = self.session.current_hunk
            if current is None:
                self._hunk_widget.update("[dim]No hunks to review.[/dim]")
            else:
                self._hunk_widget.update(_format_hunk_for_review(current))
            if self._help_widget is not None:
                if self._show_help:
                    self._help_widget.update(f"[dim]{DIFF_REVIEW_BINDINGS_TEXT}[/dim]")
                else:
                    self._help_widget.update("")

        def _decide_and_advance(self, decision: HunkDecision) -> None:
            self.session.record_decision(decision)
            self.session.advance()
            self._refresh()

        def action_accept(self) -> None:
            self._decide_and_advance("accepted")

        def action_reject(self) -> None:
            self._decide_and_advance("rejected")

        def action_skip(self) -> None:
            self._decide_and_advance("skipped")

        def action_next(self) -> None:
            self.session.advance()
            self._refresh()

        def action_prev(self) -> None:
            self.session.retreat()
            self._refresh()

        def action_toggle_help(self) -> None:
            self._show_help = not self._show_help
            self._refresh()


__all__ = [
    "DIFF_REVIEW_BINDINGS_TEXT",
    "DiffHunk",
    "DiffLine",
    "DiffLineKind",
    "DiffReviewSession",
    "HunkDecision",
    "parse_unified_diff",
    "_format_hunk_for_review",
    "_format_review_progress",
]

if _Screen is not None:
    __all__.append("DiffReviewScreen")

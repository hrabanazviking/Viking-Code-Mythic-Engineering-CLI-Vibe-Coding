"""Knowledge-graph auto-population (PH-05 follow-up).

Side-effect helpers wired into ``cmd_checkin`` and ``cmd_scan`` so
the slice 5.7 packet retriever and slice 5.4 rehydrator have fresh
data without requiring an explicit ``mythic-vibe graph`` invocation
between every command.

Defensive throughout: any sqlite / I/O failure during the upsert
phase is logged silently and never crashes the parent command. The
``cmd_*`` callers should treat these helpers as fire-and-forget —
they return :class:`AutoPopulateResult` so tests can assert on
counts, but the parent command should ignore the return.

Cross-platform: pure stdlib + GraphStore (which is already
stdlib-only).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .graph import GraphStore
from .scanner import ProjectIndex


@dataclass
class AutoPopulateResult:
    """Counts what landed in the graph during one call. Tests assert
    on the totals; parent commands typically discard."""

    entities_upserted: int = 0
    tags_added: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "entities_upserted": self.entities_upserted,
            "tags_added": self.tags_added,
            "errors": list(self.errors),
            "ok": self.ok,
        }


def populate_from_scan(
    root: Path,
    index: ProjectIndex,
) -> AutoPopulateResult:
    """Walk a :class:`ProjectIndex` and upsert one entity per doc /
    test / important-file (with ``mythic_vibe_cli/`` paths treated as
    Python modules). Tags follow the slice 5.3 retriever's
    ``kind:<x>`` / ``language:<x>`` convention.

    Best-effort: a sqlite failure surfaces in ``result.errors`` but
    never raises. Parent callers should ignore the return."""
    result = AutoPopulateResult()
    try:
        store = GraphStore.open(root)
    except Exception as exc:  # noqa: BLE001 — never crash the scan
        result.errors.append(f"open graph store: {exc}")
        return result

    try:
        # Documentation entities — kind "doc", tag kind:doc.
        for doc in index.docs or []:
            path = str(doc.get("path", "") or "")
            if not path:
                continue
            try:
                entity = store.upsert_entity(
                    kind="doc",
                    name=path,
                    path=path,
                    metadata={
                        "size": int(doc.get("size", 0) or 0),
                        "language": str(doc.get("language", "") or ""),
                    },
                )
                store.add_tag(entity.id, "kind:doc")
                result.entities_upserted += 1
                result.tags_added += 1
            except Exception as exc:  # noqa: BLE001 — log + keep walking
                result.errors.append(f"upsert doc {path!r}: {exc}")

        # Test entities — kind "test", tag kind:test.
        for test in index.tests or []:
            path = str(test.get("path", "") or "")
            if not path:
                continue
            try:
                entity = store.upsert_entity(
                    kind="test",
                    name=path,
                    path=path,
                    metadata={"size": int(test.get("size", 0) or 0)},
                )
                store.add_tag(entity.id, "kind:test")
                result.entities_upserted += 1
                result.tags_added += 1
            except Exception as exc:  # noqa: BLE001
                result.errors.append(f"upsert test {path!r}: {exc}")

        # Important files / Python modules — heuristic: any
        # important_files entry with a `.py` suffix becomes a module.
        for entry in getattr(index, "important_files", None) or []:
            path = str(entry.get("path", "") or "")
            if not path or not path.endswith(".py"):
                continue
            module_name = path[: -len(".py")].replace("/", ".").replace("\\", ".")
            try:
                entity = store.upsert_entity(
                    kind="module",
                    name=module_name,
                    path=path,
                    metadata={
                        "size": int(entry.get("size", 0) or 0),
                        "reason": str(entry.get("reason", "") or ""),
                    },
                )
                store.add_tag(entity.id, "kind:module")
                store.add_tag(entity.id, "language:python")
                result.entities_upserted += 1
                result.tags_added += 2
            except Exception as exc:  # noqa: BLE001
                result.errors.append(f"upsert module {module_name!r}: {exc}")
    finally:
        try:
            store.close()
        except Exception as exc:  # noqa: BLE001
            result.errors.append(f"close graph store: {exc}")

    return result


def populate_from_checkin(
    root: Path,
    *,
    phase: str,
    update_text: str,
    timestamp: str,
    status_path: str | Path = "",
    devlog_path: str | Path = "",
) -> AutoPopulateResult:
    """Upsert one ``checkin`` entity per successful Mythic check-in.
    Tagged ``phase:<phase>`` so the slice 5.3 retriever can surface
    recent activity alongside its module / doc / test signals.

    Best-effort: a sqlite failure surfaces in ``result.errors`` but
    never raises."""
    result = AutoPopulateResult()
    try:
        store = GraphStore.open(root)
    except Exception as exc:  # noqa: BLE001
        result.errors.append(f"open graph store: {exc}")
        return result

    try:
        name = f"{phase}-{timestamp}"
        try:
            entity = store.upsert_entity(
                kind="checkin",
                name=name,
                path=str(status_path) if status_path else "",
                metadata={
                    "phase": phase,
                    "update_text": update_text,
                    "timestamp": timestamp,
                    "status_file": str(status_path) if status_path else "",
                    "devlog_file": str(devlog_path) if devlog_path else "",
                },
            )
            store.add_tag(entity.id, f"phase:{phase}")
            store.add_tag(entity.id, "kind:checkin")
            result.entities_upserted += 1
            result.tags_added += 2
        except Exception as exc:  # noqa: BLE001
            result.errors.append(f"upsert checkin {name!r}: {exc}")
    finally:
        try:
            store.close()
        except Exception as exc:  # noqa: BLE001
            result.errors.append(f"close graph store: {exc}")

    return result


__all__ = [
    "AutoPopulateResult",
    "populate_from_checkin",
    "populate_from_scan",
]

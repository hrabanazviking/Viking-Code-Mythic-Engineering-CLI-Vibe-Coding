# Portions adapted from badlogic/pi-mono (packages/coding-agent/src/core/source-info.ts).
# Upstream project: pi (pi-coding-agent), licensed under the MIT License.
# Copyright (c) 2025 Mario Zechner.
# Adapted by Volmarr / RuneForgeAI, 2026.
# This file is licensed under the Apache License, Version 2.0; the upstream
# MIT permission notice is preserved in THIRD_PARTY_NOTICES.md at the repo root.
"""Provenance type for extension / skill / prompt / plugin-contributed
artifacts.

This module ports pi's :file:`core/source-info.ts` minus the
``create_source_info(path, metadata)`` factory. Pi's factory unpacks a
``PathMetadata`` object whose origin is the package-manager subsystem
(``core/package-manager.ts``); we do not port that subsystem in this slice
because its concept of "Pi packages" doesn't translate cleanly without an
npm-style ecosystem. The synthetic factory below is self-contained and
covers every Mythic-relevant case.

Public surface:

- :data:`SourceScope` — Literal: ``"user" | "project" | "temporary"``
- :data:`SourceOrigin` — Literal: ``"package" | "top-level"``
- :class:`SourceInfo` — frozen dataclass: path, source, scope, origin,
  optional base_dir
- :func:`synthetic_source_info` — factory with sensible defaults
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional


SourceScope = Literal["user", "project", "temporary"]
SourceOrigin = Literal["package", "top-level"]


@dataclass(frozen=True)
class SourceInfo:
    path: str
    source: str
    scope: SourceScope
    origin: SourceOrigin
    base_dir: Optional[str] = None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "path": self.path,
            "source": self.source,
            "scope": self.scope,
            "origin": self.origin,
        }
        if self.base_dir is not None:
            payload["base_dir"] = self.base_dir
        return payload


def synthetic_source_info(
    path: str,
    *,
    source: str,
    scope: SourceScope = "temporary",
    origin: SourceOrigin = "top-level",
    base_dir: Optional[str] = None,
) -> SourceInfo:
    """Construct a SourceInfo without a PathMetadata round-trip.

    Mirrors pi's ``createSyntheticSourceInfo`` — used when a contributed
    artifact's location is not coming from a package-manager-resolved
    metadata object. Defaults match pi's: ``scope="temporary"`` and
    ``origin="top-level"``.
    """
    return SourceInfo(
        path=path,
        source=source,
        scope=scope,
        origin=origin,
        base_dir=base_dir,
    )

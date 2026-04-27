from __future__ import annotations

from dataclasses import dataclass


COMPATIBLE_LICENSES = {
    "apache-2.0": "Apache-2.0",
    "mit": "MIT",
    "bsd-2-clause": "BSD-2-Clause",
    "bsd-3-clause": "BSD-3-Clause",
}

INCOMPATIBLE_LICENSES = {
    "agpl-3.0",
    "gpl-2.0",
    "gpl-3.0",
    "lgpl-2.1",
    "lgpl-3.0",
}


@dataclass(frozen=True)
class LicensePosture:
    spdx_id: str
    name: str
    compatible: bool
    warning: str
    notes: list[str]

    def to_dict(self) -> dict[str, object]:
        return {
            "spdx_id": self.spdx_id,
            "name": self.name,
            "compatible": self.compatible,
            "warning": self.warning,
            "notes": list(self.notes),
        }


def classify_license(spdx_id: str | None, name: str | None = None) -> LicensePosture:
    normalized = (spdx_id or "").strip()
    key = normalized.lower()
    display_name = name or normalized or "Unknown"

    if key in COMPATIBLE_LICENSES:
        canonical = COMPATIBLE_LICENSES[key]
        return LicensePosture(
            spdx_id=canonical,
            name=display_name,
            compatible=True,
            warning="",
            notes=[
                f"{canonical} is generally compatible with Apache-2.0 reuse when notices and attribution are preserved.",
                "Keep source provenance and modification notes with the imported file.",
            ],
        )

    if key in INCOMPATIBLE_LICENSES:
        return LicensePosture(
            spdx_id=normalized or "Unknown",
            name=display_name,
            compatible=False,
            warning="Do not plunder: copyleft license requires explicit review before reuse in this project.",
            notes=["Use inspiration only, or get a deliberate licensing decision before importing code."],
        )

    return LicensePosture(
        spdx_id=normalized or "Unknown",
        name=display_name,
        compatible=False,
        warning="Do not plunder: license is unknown or not on the approved Apache/MIT/BSD compatibility list.",
        notes=["Inspect the upstream license manually before importing this file."],
    )

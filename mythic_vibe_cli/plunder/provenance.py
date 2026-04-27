from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def manifest_path(root: Path) -> Path:
    return root / "mythic" / "imports" / "plunder_manifest.json"


def plan_path(root: Path) -> Path:
    return root / "mythic" / "imports" / "plunder_plan.json"


def cache_path_for(root: Path, repo: str, source_file: str, ref: str) -> Path:
    return root / "mythic" / "imports" / "cache" / repo.replace("/", "__") / ref / source_file


@dataclass(frozen=True)
class PlunderPlan:
    repo: str
    source_file: str
    destination: str
    ref: str
    source_sha: str
    license_spdx_id: str
    license_name: str
    license_compatible: bool
    license_warning: str
    notes: list[str] = field(default_factory=list)
    modifications: str = "Unmodified import planned."
    created_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, object]:
        return {
            "repo": self.repo,
            "source_file": self.source_file,
            "destination": self.destination,
            "ref": self.ref,
            "source_sha": self.source_sha,
            "license": {
                "spdx_id": self.license_spdx_id,
                "name": self.license_name,
                "compatible": self.license_compatible,
                "warning": self.license_warning,
                "notes": list(self.notes),
            },
            "modifications": self.modifications,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> PlunderPlan:
        license_payload = payload.get("license") if isinstance(payload.get("license"), dict) else {}
        return cls(
            repo=str(payload.get("repo") or ""),
            source_file=str(payload.get("source_file") or payload.get("source") or ""),
            destination=str(payload.get("destination") or ""),
            ref=str(payload.get("ref") or "main"),
            source_sha=str(payload.get("source_sha") or ""),
            license_spdx_id=str(license_payload.get("spdx_id") or "Unknown"),
            license_name=str(license_payload.get("name") or "Unknown"),
            license_compatible=bool(license_payload.get("compatible", False)),
            license_warning=str(license_payload.get("warning") or ""),
            notes=[str(item) for item in license_payload.get("notes", []) if str(item)],
            modifications=str(payload.get("modifications") or "Unmodified import planned."),
            created_at=str(payload.get("created_at") or utc_now()),
        )


@dataclass(frozen=True)
class PlunderRecord:
    repo: str
    source_file: str
    source_ref: str
    source_sha: str
    license_spdx_id: str
    destination: str
    modifications: str
    recorded_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, str]:
        return {
            "repo": self.repo,
            "source_file": self.source_file,
            "source_ref": self.source_ref,
            "source_sha": self.source_sha,
            "license": self.license_spdx_id,
            "destination": self.destination,
            "modifications": self.modifications,
            "recorded_at": self.recorded_at,
        }


def write_plan(root: Path, plan: PlunderPlan) -> Path:
    path = plan_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plan.to_dict(), indent=2) + "\n", encoding="utf-8")
    return path


def load_plan(root: Path, path: Path | None = None) -> PlunderPlan:
    source = path or plan_path(root)
    payload = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Plunder plan must be a JSON object: {source}")
    return PlunderPlan.from_dict(payload)


def read_manifest(root: Path) -> dict[str, object]:
    path = manifest_path(root)
    if not path.exists():
        return {"schema_version": 1, "imports": []}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Plunder manifest must be a JSON object: {path}")
    if not isinstance(payload.get("imports"), list):
        payload["imports"] = []
    payload.setdefault("schema_version", 1)
    return payload


def append_record(root: Path, record: PlunderRecord) -> Path:
    path = manifest_path(root)
    payload = read_manifest(root)
    imports = payload.setdefault("imports", [])
    if not isinstance(imports, list):
        raise ValueError(f"Plunder manifest imports must be a list: {path}")
    imports.append(record.to_dict())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def record_from_plan(plan: PlunderPlan, *, modifications: str | None = None) -> PlunderRecord:
    return PlunderRecord(
        repo=plan.repo,
        source_file=plan.source_file,
        source_ref=plan.ref,
        source_sha=plan.source_sha,
        license_spdx_id=plan.license_spdx_id,
        destination=plan.destination,
        modifications=modifications or plan.modifications,
    )


def notice_entry(record: PlunderRecord) -> str:
    return (
        f"- {record.destination}: imported from {record.repo}/{record.source_file} "
        f"at {record.source_ref} ({record.source_sha or 'unknown sha'}), license {record.license_spdx_id}. "
        f"Modifications: {record.modifications}"
    )


def update_notice(root: Path, record: PlunderRecord) -> Path:
    path = root / "NOTICE"
    entry = notice_entry(record)
    if path.exists():
        text = path.read_text(encoding="utf-8")
        if entry in text:
            return path
        if not text.endswith("\n"):
            text += "\n"
        text += entry + "\n"
    else:
        text = "Third-party notices\n\n" + entry + "\n"
    path.write_text(text, encoding="utf-8")
    return path

from __future__ import annotations

from pathlib import Path


REQUIRED_MARKERS = [
    "## [Unreleased]",
    "### Added",
    "### Changed",
]


def main() -> int:
    path = Path("CHANGELOG.md")
    if not path.exists():
        print("Missing CHANGELOG.md")
        return 1

    text = path.read_text(encoding="utf-8")
    missing = [marker for marker in REQUIRED_MARKERS if marker not in text]
    if missing:
        print("CHANGELOG.md is missing required release marker(s):")
        for marker in missing:
            print(f"- {marker}")
        return 1

    unreleased = text.split("## [Unreleased]", 1)[1]
    if "Stage 13" not in unreleased and "Packaging" not in unreleased:
        print("CHANGELOG.md [Unreleased] should mention the current packaging/release work before release.")
        return 1

    print("CHANGELOG.md release gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

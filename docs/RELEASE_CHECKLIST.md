# Release Checklist

Use this checklist before tagging or publishing Mythic Vibe CLI.

## Version And History

- [ ] Update `pyproject.toml` version.
- [ ] Move `CHANGELOG.md` entries from `[Unreleased]` into a dated release section.
- [ ] Confirm `DEVLOG.md` has the latest implementation rationale.
- [ ] Run `python scripts/check_changelog.py`.

## Local Verification

- [ ] `python -m mythic_vibe_cli --help`
- [ ] `mythic-vibe --version`
- [ ] `pytest -q`
- [ ] `pytest -q --cov=mythic_vibe_cli --cov-report=term-missing`
- [ ] `ruff check mythic_vibe_cli tests scripts`
- [ ] `mypy mythic_vibe_cli`
- [ ] `python -m build`
- [ ] `twine check dist/*`

## Install Checks

- [ ] Fresh venv install works on Windows PowerShell.
- [ ] Fresh venv install works on Linux.
- [ ] Fresh venv install works on macOS.
- [ ] `uv pip install -e ".[dev]"` works.
- [ ] `pipx install --editable .` works.

## Artifact Checks

- [ ] Wheel and sdist are generated in `dist/`.
- [ ] Wheel contains `mythic_vibe_cli/resources/schemas/*.json`.
- [ ] Console scripts resolve:
- [ ] `mythic-vibe`
- [ ] `mythic`
- [ ] CI passes on the release branch.

## Release Notes

- [ ] Summarize user-facing changes.
- [ ] Mention any migration notes.
- [ ] Mention any known limitations.
- [ ] Link the release to the matching commit SHA.

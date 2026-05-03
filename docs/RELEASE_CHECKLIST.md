# Release Checklist

Use this checklist before tagging or publishing Mythic Vibe CLI.

## Version And History

- [ ] Update `pyproject.toml` version.
- [ ] Update `mythic_vibe_cli/__init__.py:__version__` to match (CI smoke test verifies this).
- [ ] (For v1.0+ majors only) Update the `Development Status` classifier in `pyproject.toml`.
- [ ] Move `CHANGELOG.md` entries from `[Unreleased]` into a dated release section. Prepend a fresh empty `[Unreleased]` block.
- [ ] Confirm `DEVLOG.md` has the latest implementation rationale (entry dated for the release session).
- [ ] Run `python scripts/check_changelog.py` (release gate).
- [ ] Run `python scripts/check_changelog.py --classify` and confirm the Unclassified count is 0 (PH-20.F — every entry uses a conventional-commit prefix).

## Local Verification

- [ ] `python -m mythic_vibe_cli --help`
- [ ] `mythic-vibe --version` (matches the pyproject + `__init__` version)
- [ ] `pytest -q` (must be green; v1.0.0 baseline: 2224 passed, 1 skipped, 109 subtests passed)
- [ ] `pytest -q --cov=mythic_vibe_cli --cov-report=term-missing` (≥ 82%)
- [ ] `ruff check mythic_vibe_cli tests scripts tools`
- [ ] `mypy mythic_vibe_cli`
- [ ] `python tools/contract_audit.py --strict` (every argparse handler must be documented, or in the baseline allowlist)
- [ ] `python -m build`
- [ ] `twine check dist/*`
- [ ] `python scripts/regenerate_sbom.py` (re-roll `docs/security/sbom.json`; release pipeline re-rolls it again at tag time)

## Install Checks

- [ ] Fresh venv install works on Windows PowerShell.
- [ ] Fresh venv install works on Linux.
- [ ] Fresh venv install works on macOS.
- [ ] `uv pip install -e ".[dev]"` works.
- [ ] `pipx install --editable .` works.
- [ ] Each documented extra installs cleanly: `python -m pip install -e ".[ai]"`, `".[tui]"`, `".[ux]"`, `".[otel]"`, `".[test]"` (a quick smoke per extra catches dep-floor regressions).

## Artifact Checks

- [ ] Wheel and sdist are generated in `dist/`.
- [ ] Wheel contains `mythic_vibe_cli/resources/schemas/*.json`.
- [ ] Console scripts resolve:
- [ ] `mythic-vibe`
- [ ] `mythic`
- [ ] CI passes on the release branch (3 OS × 3 Python + Linux aarch64 row, plus the cross-platform smoke step).
- [ ] `tests/test_packaging_templates.py` is green (PH-19.7 sanity for the Homebrew formula + Scoop manifest templates + release.yml shape).
- [ ] `tests/test_sbom_committed.py` is green (PH-19.5 SBOM well-formedness).

## Compatibility-Policy Review (v1.0+)

- [ ] Walk every change in `[Unreleased]` against `docs/compatibility_policy.md` §3 stability tiers. Anything Stable that changed needs the right SemVer bump (or a deprecation cycle per §5).
- [ ] If a Stable surface is being removed: confirm it carried a `DeprecationWarning` for at least one full minor cycle BEFORE this release.
- [ ] If a new optional flag / field / subcommand was added: confirm the bump is MINOR (or PATCH if it's an internal-only tweak).
- [ ] If `requires-python` changed: also update `docs/compatibility_policy.md` §1 + the CI matrix in `.github/workflows/ci.yml`.

## Security / Supply Chain (v1.0+)

- [ ] If a new attack surface landed (network endpoint, persisted state, credential input, plugin extension point): `docs/security/threat_model.md` §5 has a new row for it (per its §8 update procedure).
- [ ] `docs/security/sbom.json` regenerated and committed for this release.

## Release Notes

- [ ] Summarize user-facing changes.
- [ ] Mention any migration notes.
- [ ] Mention any known limitations.
- [ ] Link the release to the matching commit SHA.
- [ ] Include the `pytest -q` test count + coverage at the release cut (operator-trust signal).

---

## Tag-driven distribution (PH-19.7, 2026-05-02)

Once everything above is green, the release pipeline runs on a
single trigger: `git push origin v<X.Y.Z>`. The workflow at
`.github/workflows/release.yml` then:

- [ ] Builds wheel + sdist + wheelhouse + SBOM (clean isolated venv).
- [ ] Validates dist with `twine check`.
- [ ] Publishes wheel + sdist to PyPI via OIDC trusted publishing
      (no long-lived API token in repo secrets).
- [ ] Creates a GitHub Release with wheel, sdist, wheelhouse
      tarball, SBOM, and `SHA256SUMS` / `SHA512SUMS` attached.
- [ ] Opens a bump PR against the `homebrew-mythic` tap with the
      rendered formula.
- [ ] Opens a bump PR against the `scoop-mythic` bucket with the
      rendered manifest.

Per-release manual steps after the workflow finishes:

- [ ] Compatibility-policy review — does this release violate
      anything in `docs/compatibility_policy.md` §3 / §5? If yes,
      it must be a major bump with a deprecation note in CHANGELOG.
- [ ] Approve and merge the auto-generated Homebrew tap PR.
- [ ] Approve and merge the auto-generated Scoop bucket PR.
- [ ] Verify `pip install mythic-vibe-cli==<VERSION>` from PyPI.
- [ ] Verify `brew install hrabanazviking/mythic/mythic-vibe`.
- [ ] Verify `scoop install mythic-vibe` (from scoop-mythic bucket).
- [ ] Verify the wheelhouse install path documented in
      `packaging/WHEELHOUSE.md` works against the released tarball.

Rehearsal mode: run the workflow via the Actions UI's
`workflow_dispatch` trigger (not a tag push). The
`publish-pypi`, `github-release`, `update-homebrew`, and
`update-scoop` jobs are gated on `startsWith(github.ref,
'refs/tags/v')` so they no-op during rehearsal — only the
`build` job exercises end-to-end.

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

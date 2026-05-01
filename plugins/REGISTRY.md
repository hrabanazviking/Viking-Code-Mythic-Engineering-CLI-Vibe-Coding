# Mythic Vibe CLI — Plugin Registry

A curated index of community plugins for the Mythic Vibe CLI.

> **This is not an installer.** It's a discovery surface. To install a plugin:
> 1. `pip install <package-name>` (resolves the package + its `mythic_vibe.plugins` entry-points).
> 2. `mythic-vibe plugin install <name>` (registers the entry-point in your project's `mythic/plugins.json`).

---

## How to get listed here

Open a pull request adding a row to the table below. Inclusion criteria:

- **Open-source license** — MIT, Apache-2.0, BSD-2/3-Clause, MPL-2.0, or comparable.
- **ME laws compliance** — see [`MYTHIC_ENGINEERING.md`](../MYTHIC_ENGINEERING.md). At minimum: stdlib-first; optional deps gated; no silent network calls; cross-platform where possible.
- **Tests pass** — your plugin's own test suite passes on the latest tagged Mythic Vibe CLI release. CI badge in your README is a plus.
- **Authoring guide compliance** — your plugin matches the [PLUGIN_AUTHORING_GUIDE](../docs/PLUGIN_AUTHORING_GUIDE.md) shape (entry-point in `mythic_vibe.plugins`, declared `MYTHIC_HOOKS`, etc.).
- **Provenance noted** — if your plugin wraps another vendor SDK or copies code from a third-party project, ship an ADR documenting the boundary.

PRs are reviewed for license + technical sanity only. Listing is **not** an endorsement of plugin quality, security posture, or maintenance.

---

## Listed plugins

| Plugin | Repository | Extension Points | License | Author | Notes |
|---|---|---|---|---|---|
| `mythic_vibe_example_plugin` | [`examples/plugins/mythic_vibe_example_plugin`](../examples/plugins/mythic_vibe_example_plugin/) | All six | MIT | Mythic Vibe CLI maintainers | Reference plugin shipped with the CLI. Demonstrates every extension point + hook. Use as a starting template. |

---

## Validation checklist (for reviewers + plugin authors)

Before submitting, run:

```bash
# Discovery
pip install -e .
mythic-vibe plugin discover
mythic-vibe plugin install <your-plugin-name>
mythic-vibe plugin inspect <your-plugin-name>

# Health check via the sandbox
python -c "from mythic_vibe_cli.plugins.sandbox import safe_call; \
  from your_pkg import plugin; \
  r = safe_call(plugin.before_scan, {'path': '.'}, timeout_sec=1.0); \
  print(r.to_dict())"

# Tests
pytest -q
```

If any of these fail, fix before submitting the PR.

---

## Removing a plugin

Plugins are removed from the registry when:

- The repository is deleted, archived for >12 months without revival, or made private.
- The license is changed to a non-permissive form.
- A clear, documented security issue goes unaddressed for >30 days after disclosure.
- The author requests removal.

Removal does not affect installations — operators can keep using older versions of removed plugins, but new operators won't discover them through this index.

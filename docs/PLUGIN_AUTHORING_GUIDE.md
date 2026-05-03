# Plugin Authoring Guide

This guide walks you through writing a plugin for the Mythic Vibe
CLI. By the end you'll have a real installable Python package
that hooks into the CLI's event bus, contributes to one or more
of the six extension points, ships under PyPI / pip-installable
shape, and satisfies the sandbox contract.

> **Companion code**: every code sample here mirrors a real,
> runnable example in
> [`examples/plugins/mythic_vibe_example_plugin/`](../examples/plugins/mythic_vibe_example_plugin/).
> Clone it, install it with `pip install -e`, and watch it light
> up via `mythic-vibe plugin discover`.

---

## 1. The mental model

A plugin is a **Python object** (instance, class, or module) that
the CLI can locate via either:

1. **A `pyproject.toml` entry-point** in the
   `mythic_vibe.plugins` group. Operators install your package
   via `pip install`, then run `mythic-vibe plugin install
   <name>` to register it.
2. **A direct entry-point string** like `my_pkg.module:plugin_obj`
   added to a project's `mythic/plugins.json` registry.

The CLI:

- **Loads** your object via `importlib.import_module` +
  `getattr`.
- **Subscribes** any callable named after a known hook (e.g.
  `before_scan`, `after_verify`) to the event bus.
- **Discovers** any callable named `slash_commands` and merges
  its return value into the global slash catalogue.
- **Inspects** your object's declared `MYTHIC_HOOKS`, `__version__`,
  and Protocol membership (slice 10.3) to surface a health
  record via `mythic-vibe plugin inspect`.

Your plugin **never** imports CLI internals (no `from
mythic_vibe_cli...`). The contract is defined by the Protocol
shapes in
[`mythic_vibe_cli/plugins/extension_points.py`](../mythic_vibe_cli/plugins/extension_points.py)
plus the hook names in
[`mythic_vibe_cli/plugins/api.py`](../mythic_vibe_cli/plugins/api.py).

---

## 2. The eight hooks

Hooks are emitted at well-defined moments by the CLI. Your
plugin attaches a callable named exactly after the hook to react.

| Hook | When | Payload |
|---|---|---|
| `before_scan` | Just before `mythic-vibe scan` walks the tree | `{"path": str, "changed_only": bool, "docs_only": bool, ...}` |
| `after_scan` | After the scan index is built | `{"path": str, "changed_files": int, "languages": int, ...}` |
| `before_packet` | Before a codex packet is built | `{"path": str, "packet_id": str, ...}` |
| `after_packet` | After a packet is written | `{"path": str, "packet_id": str, ...}` |
| `before_verify` | Before `mythic-vibe verify` runs checks | `{"path": str, "selected": dict}` |
| `after_verify` | After verification completes | `{"path": str, "result": str, "level": str, ...}` |
| `before_reflect` | Before `mythic-vibe reflect` runs | `{"path": str, ...}` |
| `after_reflect` | After reflection completes | `{"path": str, "handoff_id": str, ...}` |

Declare the hooks your plugin handles via the optional
`MYTHIC_HOOKS` attribute (used by `plugin inspect` to detect
typos):

```python
class MyPlugin:
    MYTHIC_HOOKS = ["before_scan", "after_verify"]

    def before_scan(self, payload):
        ...

    def after_verify(self, payload):
        ...
```

---

## 3. The six extension points

Beyond hooks, plugins can contribute to six typed categories
(see
[`extension_points.py`](../mythic_vibe_cli/plugins/extension_points.py)):

### 3.1 RitualPlugin

```python
class MyRitualPlugin:
    def rituals(self):
        return ["my_ritual"]
```

### 3.2 ProviderPlugin

```python
class MyProviderPlugin:
    def providers(self):
        return {"my_provider": MyProvider()}
```

`MyProvider` must satisfy the `AIProvider` Protocol from
`mythic_vibe_cli.ai.providers.base` (a `validate_config()` /
`estimate()` / `run()` triple).

### 3.3 ScannerPlugin

```python
class MyScannerPlugin:
    def scanner_rules(self):
        return [{"pattern": "*.foo", "kind": "config"}]
```

### 3.4 VerificationGatePlugin

```python
class MyGatePlugin:
    def verification_gates(self):
        return {"my_gate": my_gate_runner}

def my_gate_runner(plan, agent_input, agent_output, root):
    from mythic_vibe_cli.workflow_agents import VerificationResult
    return VerificationResult(name="my_gate", passed=True, detail="ok")
```

### 3.5 ArtifactTemplatePlugin

```python
class MyTemplatePlugin:
    def artifact_templates(self):
        return {"my_artefact": "# {title}\n\n{body}\n"}
```

### 3.6 SlashCommandPlugin

```python
from mythic_vibe_cli.runtime.slash_commands import SlashCommandInfo

class MySlashPlugin:
    def slash_commands(self):
        return [
            SlashCommandInfo(
                name="my_cmd",
                description="My slash command",
                source="plugin:my_pkg",
                argv=("my_cmd", "--path", "."),
            ),
        ]
```

---

## 4. Packaging

Your plugin is a regular Python package. Minimum `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "mythic-vibe-my-plugin"
version = "0.1.0"
description = "My plugin for the Mythic Vibe CLI"
requires-python = ">=3.10"
license = {text = "MIT"}

[project.entry-points."mythic_vibe.plugins"]
my_plugin = "my_plugin:plugin"
```

The entry-point value `my_plugin:plugin` resolves at runtime to
`getattr(importlib.import_module("my_plugin"), "plugin")` — so
your `my_plugin/__init__.py` must define a top-level
`plugin = MyPlugin()` (or a class/module the CLI can dispatch
against).

### 4.1 Declaring capabilities (v1.0)

When your plugin is registered in a project's
`mythic/plugins.json`, you can declare which runtime capabilities
your code uses. This is **operator-visible documentation** that
shows up in `mythic-vibe plugin doctor` — operators can spot
plugins asking for more than they should need before enabling
them.

```json
{
  "schema_version": 2,
  "plugin_records": [
    {
      "entrypoint": "my_pkg.MyPlugin",
      "enabled": true,
      "hooks": ["before_scan", "after_scan"],
      "version": "1.0.0",
      "added_at": "2026-05-03T12:00:00Z",
      "capabilities": ["read", "file-write"]
    }
  ]
}
```

The fixed vocabulary is in
`mythic_vibe_cli/plugins/capabilities.py:KNOWN_CAPABILITIES`:

| Capability | Meaning |
|---|---|
| `read` | Read project files inside the operator's repo |
| `network` | Outbound HTTP / TCP / etc. |
| `subprocess` | Spawn child processes |
| `file-write` | Write files outside the plugin's own context dir |

**Default-deny.** A plugin with no `capabilities` field — or an
explicitly empty list — is treated as **read-own-context only**.
The CLI does NOT enforce capabilities at the OS level today (no
portable in-process Python sandbox exists), but declaring narrowly
communicates intent to reviewers and gives the future enforcement
layer something to build on.

If your plugin name shows up in `plugin doctor` output with an
**unknown capability** warning, you have a typo (e.g. `subproccess`
instead of `subprocess`). Fix the manifest entry, not the plugin
code.

---

## 5. Sandbox contract

Plugins are local Python code — the CLI cannot fully sandbox
them. The sandbox layer in
[`plugins/sandbox.py`](../mythic_vibe_cli/plugins/sandbox.py)
provides:

- **Exception isolation**: every hook call is wrapped in
  try/except. Your hook may raise; the orchestrator continues.
- **Optional timing budget**: when operators set
  `MYTHIC_PLUGIN_TIMEOUT_SEC=N`, your hooks run on a worker
  thread with an `N`-second deadline. **You cannot be force-
  killed**; respect the budget voluntarily.
- **Resource probe** (POSIX only): operators can read process
  rusage via `probe_resource_caps()` to spot misbehaving plugins.
- **Soft circuit breaker (v1.0)**: when the dispatcher passes a
  `breaker=` argument to `safe_call`, every result is recorded
  per `plugin_id`. After `MYTHIC_PLUGIN_BREAKER_THRESHOLD`
  consecutive failures (default **3**), the breaker trips and
  the dispatcher can skip your plugin proactively on subsequent
  invocations. The breaker is **soft** — it does not modify the
  registry or disable your plugin; that decision stays with the
  operator via `mythic-vibe plugin disable`. Surfaces in
  `mythic-vibe plugin doctor`.

Best practices:

- Keep hook handlers fast. The bus is synchronous — slow plugins
  slow the CLI.
- No network calls in hooks unless explicitly opted in **and
  declared in your `capabilities` array**. Operators reading
  `plugin doctor` should see what they're consenting to.
- Write any I/O to the project's `mythic/` directory
  (`payload["path"]`) rather than the operator's home.
- Catch your own exceptions and report via the payload or your
  own log file in `mythic/plugins/<name>/`.
- **A successful invocation resets the breaker counter.** If your
  plugin can fail transiently, recover on the next call rather
  than entering a permanent error state.

---

## 6. Testing your plugin

Pytest works out of the box. Use the sandbox helper to confirm
your hook is well-behaved:

```python
from mythic_vibe_cli.plugins.sandbox import safe_call
from mythic_vibe_cli.plugins.circuit_breaker import CircuitBreaker

def test_my_hook_is_fast():
    result = safe_call(
        my_plugin.before_scan,
        {"path": "."},
        timeout_sec=0.5,
        plugin_id="my_pkg.MyPlugin",
    )
    assert result.ok
    assert result.elapsed_ms < 100


def test_my_hook_does_not_trip_breaker(tmp_path):
    """v1.0: ensure repeated normal invocations stay closed."""
    breaker = CircuitBreaker(threshold=3)
    for _ in range(10):
        safe_call(
            my_plugin.before_scan,
            {"path": str(tmp_path)},
            plugin_id="my_pkg.MyPlugin",
            breaker=breaker,
        )
    assert not breaker.is_tripped("my_pkg.MyPlugin")
```

For end-to-end validation, install your package in editable mode
and run the CLI's plugin commands:

```bash
pip install -e .
mythic-vibe plugin discover
mythic-vibe plugin install my_plugin
mythic-vibe plugin inspect my_plugin
mythic-vibe plugin doctor          # v1.0: capability + breaker audit
mythic-vibe plugin doctor --json   # CI-friendly
```

---

## 7. Publishing

1. Bump version in `pyproject.toml`.
2. Build sdist + wheel: `python -m build`.
3. `twine upload dist/*`.
4. Submit a PR adding your plugin to
   [`plugins/REGISTRY.md`](../plugins/REGISTRY.md) so other
   operators can find it.

The registry's inclusion criteria:

- Open-source license (MIT / Apache-2.0 / BSD).
- Mythic Engineering laws compliance (see
  `MYTHIC_ENGINEERING.md`).
- Tests pass on the latest Mythic Vibe CLI tag.
- ADR if the plugin crosses a non-trivial boundary (e.g. wraps
  another vendor SDK).

---

## 8. Reference

- **Protocols**: `mythic_vibe_cli/plugins/extension_points.py`
- **Hooks**: `mythic_vibe_cli/plugins/api.py:PLUGIN_HOOKS`
- **Sandbox**: `mythic_vibe_cli/plugins/sandbox.py`
- **Capabilities** (v1.0): `mythic_vibe_cli/plugins/capabilities.py:KNOWN_CAPABILITIES`
- **Circuit breaker** (v1.0): `mythic_vibe_cli/plugins/circuit_breaker.py:CircuitBreaker`
- **Manifest schema**: `mythic_vibe_cli/resources/schemas/plugin_manifest.schema.json` (capability vocabulary is coordinated with `KNOWN_CAPABILITIES`)
- **Operator audit command** (v1.0): `mythic-vibe plugin doctor`
- **Registry**: `mythic/plugins.json` per project
- **Example**: `examples/plugins/mythic_vibe_example_plugin/`
- **Mythic Engineering laws**: `MYTHIC_ENGINEERING.md`
- **Operator-facing companion guide**: [`docs/plugins.md`](plugins.md) (sections 9a / 9b / 9c cover the v1.0 capability + breaker + doctor surfaces from the operator's angle)

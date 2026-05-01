# mythic-vibe-example-plugin

Reference plugin for the [Mythic Vibe CLI](https://github.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding).

This plugin **exercises every extension point and every event-bus hook** the CLI exposes (PH-10). It's meant to be cloned, renamed, and edited as a starting template for your own plugin.

## What it does

- Implements all six extension-point Protocols from `mythic_vibe_cli.plugins.extension_points` (most return empty / minimal payloads — it's a demonstration of the *contract*, not a working router).
- Subscribes to all eight CLI hooks (`before_scan` / `after_scan` / `before_packet` / `after_packet` / `before_verify` / `after_verify` / `before_reflect` / `after_reflect`).
- On every hook, appends a one-line entry to `<project>/mythic/plugins/example.log` so operators can confirm hooks fired.
- Contributes one always-pass verification gate, one markdown template, and one slash command.

## Try it

```bash
# From the repo root
pip install -e examples/plugins/mythic_vibe_example_plugin

# Confirm pip resolved the entry-point
mythic-vibe plugin discover

# Register it in a project
cd /path/to/your/project
mythic-vibe plugin install mythic_vibe_example
mythic-vibe plugin inspect mythic_vibe_example

# Trigger some hooks
mythic-vibe scan --json
mythic-vibe verify --invariants

# Check the log
cat mythic/plugins/example.log
```

## Author your own

Read [`docs/PLUGIN_AUTHORING_GUIDE.md`](../../../docs/PLUGIN_AUTHORING_GUIDE.md) — every section there cross-references the corresponding pattern in this plugin's `__init__.py`.

## License

MIT.

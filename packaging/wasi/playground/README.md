# WASI browser playground (PH-23.16)

Foundation-level. A static HTML + JS page that operators can host (via GitHub Pages, a docs site, or any static-file server) to preview the WASI runtime UX. Today the runtime stub is a JS-only mock; a future slice replaces `stub_run()` in `playground.js` with the real WASI shim invocation.

## What's here

| File | Purpose |
|---|---|
| `index.html` | Page shell with command input, quick-pick buttons, output panel, and download-artifacts section. Self-contained CSS — no external font / icon CDN. |
| `playground.js` | Stub command runner + UI wiring. Returns JSON-shaped output for the v2.0-supported commands (`--version`, `--help`, `doctor --json`, `status --json`, `packet list --json`). |
| `README.md` | This file. |

## Running locally

```bash
# Any static server works:
cd packaging/wasi/playground
python -m http.server 8000

# Open http://localhost:8000/
```

## Hosting on GitHub Pages

The PH-23.1 docs site (`mkdocs.yml` at repo root) already deploys to GitHub Pages on `main` push. To include the playground:

1. Copy `packaging/wasi/playground/` into `docs/wasi-playground/` at release time (or via a workflow step).
2. The mkdocs build picks it up as static content.
3. Operators visit `https://hrabanazviking.github.io/...mythic-vibe.../wasi-playground/`.

This integration is deferred to PH-23.x — the page works standalone today; mkdocs integration is a 5-minute follow-up slice.

## What the stub demonstrates

- The supported v2.0 WASI command surface (5 read-only JSON-emitting commands).
- The argparse error path (typing an unsupported command yields a helpful message naming the supported set).
- The download-artifacts UX pattern operators will see once the wiring is real.
- The styling + page chrome — dark theme matching mkdocs-material's slate palette so the playground feels native to the docs site.

## What's NOT real yet

- **Actual WASI execution.** `stub_run()` returns canned strings instead of running the real `.wasm + .pyz`. The Wasmtime-style host bindings for browser WASI execution (`@bjorn3/browser_wasi_shim` or the Pyodide-style module loader) need to be integrated. Estimated ~4-6 hours of focused JS work plus careful testing of the `--dir` mount semantics in browser WASI.
- **Download links.** Hash-anchor stubs today. A future slice generates URLs pointing at the latest GitHub Release assets for the page's host version (a templated `data-version` attribute on each link, populated at build time).
- **Streaming stdout.** The stub returns full output in one shot. Real WASI execution should stream stdout/stderr line-by-line into the output panel for long-running commands (though the v2.0 WASI scope is read-only JSON-emitting commands, all of which complete in milliseconds).

## Why ship the foundation now?

Three reasons the page is useful even with a stub runner:

1. **Operator discovery.** A page exists at a real URL. Operators can land on it, see what the WASI runtime promises, and bookmark it for the day execution lights up.
2. **Documentation surface.** The supported-command list is rendered visually rather than buried in a markdown table. Operators reading the docs site see the v2.0 scope concretely.
3. **UX iteration in isolation.** The page's layout, colors, command-pick UX can be tuned without touching the WASI build pipeline. When the real runtime arrives it drops into the existing UI shell unchanged.

The foundation pattern matches the rest of the PH-22/23 work: ship the bones first, fill in the implementation as upstream tooling matures.

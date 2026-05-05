// playground.js — Mythic Vibe CLI WASI browser playground (PH-23.16).
//
// Foundation-level: provides the UI shell + stub command runner.
// A future slice replaces stub_run() with the real WASI shim
// invocation that loads + executes the .wasm artifact.
//
// The stub runner intentionally produces JSON-shaped output for
// commands the v2.0 WASI scope supports (--version, --help,
// doctor --json, status --json, packet list --json) so operators
// can preview the page UX before the real wasi runtime is wired.

(function () {
    "use strict";

    // ---- DOM refs ------------------------------------------------------

    const cmdInput = document.getElementById("cmd-input");
    const runBtn = document.getElementById("run-btn");
    const statusEl = document.getElementById("status");
    const outputEl = document.getElementById("output");

    // ---- Stub command runner -------------------------------------------

    /**
     * Stub command runner. Returns a string output for the
     * requested command. Real WASI execution lands in a future
     * slice that integrates @bjorn3/browser_wasi_shim or
     * equivalent.
     */
    async function stub_run(commandLine) {
        // Trim + tokenize to identify the command shape.
        const trimmed = (commandLine || "").trim();
        if (!trimmed) {
            return {
                ok: false,
                output: "Empty command.",
                exitCode: 2,
            };
        }

        // Mimic argparse-style parsing for the supported subset.
        if (trimmed === "--version") {
            return {
                ok: true,
                output: "mythic-vibe-cli 1.0.0 (WASI playground stub)",
                exitCode: 0,
            };
        }

        if (trimmed === "--help") {
            return {
                ok: true,
                output: [
                    "usage: mythic-vibe [--version] [--help] <command> ...",
                    "",
                    "WASI-supported commands (v2.0 scope):",
                    "  doctor --json     project diagnostics in JSON",
                    "  status --json     workflow status snapshot",
                    "  packet list --json  enumerate intent packets",
                    "",
                    "Most other commands work in the pip-installed CLI but",
                    "require subprocess/git/filesystem-write paths that the",
                    "WASI runtime does not yet expose.",
                ].join("\n"),
                exitCode: 0,
            };
        }

        if (trimmed === "doctor --json") {
            return {
                ok: true,
                output: JSON.stringify({
                    ok: true,
                    errors: [],
                    warnings: [
                        "WASI playground stub — no real project on disk to diagnose.",
                    ],
                    sections: {
                        required_artifacts: [],
                        state: [],
                        docs: [],
                        boundary: [],
                    },
                }, null, 2),
                exitCode: 0,
            };
        }

        if (trimmed === "status --json") {
            return {
                ok: true,
                output: JSON.stringify({
                    goal: "WASI playground demo",
                    current_phase: "intent",
                    completed_phases: [],
                    progress_percent: 0,
                }, null, 2),
                exitCode: 0,
            };
        }

        if (trimmed === "packet list --json") {
            return {
                ok: true,
                output: JSON.stringify({
                    packets: [],
                    count: 0,
                    note: "WASI playground stub — no project root mounted.",
                }, null, 2),
                exitCode: 0,
            };
        }

        // Unsupported command — surface a helpful error.
        return {
            ok: false,
            output: [
                `Unknown or unsupported command in WASI scope: ${trimmed}`,
                "",
                "Supported commands in the v2.0 WASI runtime:",
                "  --version, --help, doctor --json, status --json, packet list --json",
                "",
                "Other commands work in the pip-installed CLI but require",
                "subprocess/git/file-write paths the WASI runtime does",
                "not yet expose.",
            ].join("\n"),
            exitCode: 2,
        };
    }

    // ---- UI wiring ----------------------------------------------------

    async function runCurrentCommand() {
        const cmd = cmdInput.value;
        runBtn.disabled = true;
        statusEl.textContent = "Running...";
        statusEl.className = "status loading";

        try {
            const result = await stub_run(cmd);
            outputEl.textContent = result.output;
            statusEl.textContent = result.ok
                ? `Done. Exit code: ${result.exitCode}`
                : `Failed. Exit code: ${result.exitCode}`;
            statusEl.className = result.ok ? "status ready" : "status error";
        } catch (err) {
            outputEl.textContent = `Stub runner error: ${err && err.message}`;
            statusEl.textContent = "Error";
            statusEl.className = "status error";
        } finally {
            runBtn.disabled = false;
        }
    }

    runBtn.addEventListener("click", runCurrentCommand);
    cmdInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
            event.preventDefault();
            runCurrentCommand();
        }
    });

    // Quick-pick command buttons set the input + run.
    document.querySelectorAll(".commands-grid button[data-cmd]").forEach((btn) => {
        btn.addEventListener("click", () => {
            cmdInput.value = btn.getAttribute("data-cmd") || "";
            runCurrentCommand();
        });
    });

    // Download links — wired to stub paths today; a future build
    // hook generates URLs pointing at the latest GitHub Release
    // assets for the page's host version. Intentionally hash-only
    // so unwired links don't 404 — they just no-op.
    document.getElementById("download-wasm").addEventListener("click", (e) => {
        e.preventDefault();
        statusEl.textContent =
            "Foundation-level: download wiring lands in PH-23.x once " +
            "the playground is hosted next to release artifacts.";
        statusEl.className = "status loading";
    });
    document.getElementById("download-pyz").addEventListener("click", (e) => {
        e.preventDefault();
        statusEl.textContent =
            "Foundation-level: download wiring lands in PH-23.x once " +
            "the playground is hosted next to release artifacts.";
        statusEl.className = "status loading";
    });

    // Page is ready.
    statusEl.textContent = "Stub runner ready. Pick a command or type one.";
    statusEl.className = "status ready";
})();

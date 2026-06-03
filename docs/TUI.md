# Terminal UI (CockpitScreen)

For users who prefer a structured, visual interface over a scrolling REPL, Mythic provides a Textual-based **Terminal UI (TUI)** known as the Cockpit.

## Launching the TUI

You can enter the TUI directly from the interactive shell by typing:
```bash
/tui
```

## TUI Layout

The Cockpit is a tabbed interface offering several distinct views of your project and session state:
- **Chat:** The primary conversation view, bridging the standard REPL loop into a visual chat window using asynchronous worker threads.
- **Files:** A tree view of the files currently tracked or loaded in context.
- **Diff:** A dedicated visual review screen for staging and approving patch proposals.
- **Memory:** A timeline of the SQLite memory spine.
- **Knowledge:** Status and search interface for attached private knowledge sources.
- **Tasks:** An overview of active workflows or tasks.
- **Model:** Status of the active LLM provider, token usage, and connection health.

The TUI provides a dashboard experience while retaining the core natural language workflow.\n
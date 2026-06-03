# Interactive Shell

Mythic operates as an interactive terminal-based coding companion. The primary interface is the interactive shell.

## Starting the Shell

To start the interactive shell, simply run:
```bash
mythic
```

## The Conversation Loop

Once the shell is active, it begins a continuous conversation loop:
1. **Input:** You type natural language requests, questions, or instructions.
2. **Context:** Mythic quietly inspects your current repository, reads tracked files, checks git branch status, and looks up relevant project memory.
3. **Reasoning:** Mythic processes your request along with the gathered context to formulate a plan or a code patch.
4. **Action:** Mythic may propose file modifications, run tests, create branches, or summarize knowledge. For sensitive or persistent actions, it will ask for your approval.
5. **Memory:** The interaction and resulting changes are written to local project memory (`.mythic/memory.sqlite`) so Mythic can recall this session later.

The companion shell acts as your pair programmer, minimizing the need to manually invoke dozens of complex CLI subcommands.\n
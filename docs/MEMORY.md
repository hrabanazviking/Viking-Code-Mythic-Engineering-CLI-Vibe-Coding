# Project Memory

Mythic utilizes a local SQLite database to maintain a persistent **Memory Spine** across all of your interactive sessions.

## The Memory Spine

Located by default at `.mythic/memory.sqlite` in your project root, the memory spine records:
- **Session Summaries:** What was accomplished during an interaction.
- **Decisions:** Architectural choices and why they were made.
- **File Edits:** Which files were modified and the nature of the changes.
- **Failures & Fixes:** Bugs encountered and how they were patched.

## Utilizing Memory

The interactive shell automatically queries the memory spine. You can simply ask:
> "What were we doing last time?"

Mythic will retrieve the most recent session summaries and re-orient itself (and you) to the task at hand.

You can also use slash commands to interact with memory directly:
- `/memory` queries the spine.
- `mythic admin memory spine` allows raw inspection.\n
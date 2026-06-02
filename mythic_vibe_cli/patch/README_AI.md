# Patch Proposal System

The `mythic_vibe_cli/patch` module implements Phase 8 of the Mythic Vibe CLI Rebirth Roadmap. It enables a conversational patch approval workflow.

## Rules for AI Agents

When modifying user code:
1. Do not overwrite files directly behind the user's back.
2. Use the `PatchManager` to stage your proposed changes.
3. Prompt the user: "I found the likely fix. Here is the diff. Apply it?"
4. The user can then type `/diff` to view, `/apply` to accept, or `/reject` to discard.

## Usage

```python
from mythic_vibe_cli.patch import PatchManager

manager = PatchManager()

# 1. Propose a patch
manager.propose("path/to/file.py", new_content)

# 2. Check the diff
diff = manager.get_diff()
print(diff)

# 3. Apply the patch
manager.apply_active()
```

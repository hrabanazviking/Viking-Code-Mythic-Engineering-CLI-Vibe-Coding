import sys
from pathlib import Path

# Mock args
class Args:
    path = "."
    file = "test.txt"
    content = "hello world"
    json = False

from mythic_vibe_cli.commands import cmd_patch_propose
from mythic_vibe_cli.patch.manager import PatchManager

Path("test.txt").write_text("old text", encoding="utf-8")
res = cmd_patch_propose(Args())
print("Result:", res)

pm = PatchManager(".")
diff = pm.get_diff()
print("Diff:", diff)

pm.apply_active()
print("File content:", Path("test.txt").read_text(encoding="utf-8"))

Path("test.txt").unlink()

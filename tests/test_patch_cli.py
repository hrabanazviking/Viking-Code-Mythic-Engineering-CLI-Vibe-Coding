import io
from pathlib import Path
from mythic_vibe_cli.patch.manager import PatchManager
from mythic_vibe_cli.repl import _handle_patch_command


def test_handle_patch_command_diff(tmp_path: Path):
    manager = PatchManager()
    target = tmp_path / "test.py"
    target.write_text("a\nb\n", encoding="utf-8")
    manager.propose(target, "a\nc\n")
    
    stdout = io.StringIO()
    stderr = io.StringIO()
    _handle_patch_command("/diff", manager, stdout, stderr)
    
    out = stdout.getvalue()
    assert "---" in out
    assert "-b" in out
    assert "+c" in out


def test_handle_patch_command_apply(tmp_path: Path):
    manager = PatchManager()
    target = tmp_path / "test.py"
    target.write_text("a\nb\n", encoding="utf-8")
    manager.propose(target, "a\nc\n")
    
    stdout = io.StringIO()
    stderr = io.StringIO()
    _handle_patch_command("/apply", manager, stdout, stderr)
    
    assert "Patch applied successfully" in stdout.getvalue()
    assert target.read_text(encoding="utf-8") == "a\nc\n"
    assert manager.get_active() is None


def test_handle_patch_command_reject(tmp_path: Path):
    manager = PatchManager()
    target = tmp_path / "test.py"
    target.write_text("a\nb\n", encoding="utf-8")
    manager.propose(target, "a\nc\n")
    
    stdout = io.StringIO()
    stderr = io.StringIO()
    _handle_patch_command("/reject", manager, stdout, stderr)
    
    assert "Patch rejected" in stdout.getvalue()
    assert target.read_text(encoding="utf-8") == "a\nb\n"
    assert manager.get_active() is None


def test_handle_patch_command_no_active():
    manager = PatchManager()
    stdout = io.StringIO()
    stderr = io.StringIO()
    _handle_patch_command("/apply", manager, stdout, stderr)
    assert "No active patch to apply." in stderr.getvalue()

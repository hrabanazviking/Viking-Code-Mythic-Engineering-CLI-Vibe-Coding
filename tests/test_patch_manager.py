from pathlib import Path
import pytest
from mythic_vibe_cli.patch.manager import PatchManager, PatchProposal


def test_propose_patch(tmp_path: Path):
    manager = PatchManager()
    target_file = tmp_path / "test.txt"
    target_file.write_text("hello world\n", encoding="utf-8")
    
    proposal = manager.propose(target_file, "hello universe\n")
    
    assert isinstance(proposal, PatchProposal)
    assert proposal.original_content == "hello world\n"
    assert proposal.proposed_content == "hello universe\n"
    assert manager.get_active() is proposal


def test_generate_diff(tmp_path: Path):
    manager = PatchManager()
    target_file = tmp_path / "test.txt"
    target_file.write_text("hello world\n", encoding="utf-8")
    
    manager.propose(target_file, "hello universe\n")
    diff = manager.get_diff()
    
    assert "---" in diff
    assert "+++" in diff
    assert "-hello world" in diff
    assert "+hello universe" in diff


def test_apply_patch(tmp_path: Path):
    manager = PatchManager()
    target_file = tmp_path / "test.txt"
    target_file.write_text("hello world\n", encoding="utf-8")
    
    manager.propose(target_file, "hello universe\n")
    assert manager.apply_active() is True
    
    assert target_file.read_text(encoding="utf-8") == "hello universe\n"
    assert manager.get_active() is None


def test_reject_patch(tmp_path: Path):
    manager = PatchManager()
    target_file = tmp_path / "test.txt"
    target_file.write_text("hello world\n", encoding="utf-8")
    
    manager.propose(target_file, "hello universe\n")
    assert manager.reject_active() is True
    
    assert target_file.read_text(encoding="utf-8") == "hello world\n"
    assert manager.get_active() is None


def test_apply_no_active_patch():
    manager = PatchManager()
    assert manager.apply_active() is False
    assert manager.reject_active() is False
    assert manager.get_diff() == "No active patch proposal."

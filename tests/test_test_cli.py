from pathlib import Path
import io
import pytest

from mythic_vibe_cli.repl import run_shell

def test_test_command_not_found(tmp_path: Path):
    stdin = io.StringIO("/test\n/exit\n")
    stdout = io.StringIO()
    stderr = io.StringIO()
    
    # Run the shell in a directory without tests
    code = run_shell(
        stdin=stdin,
        stdout=stdout,
        stderr=stderr,
        project_root=tmp_path,
        main=lambda argv: 0
    )
    
    assert code == 0
    out = stdout.getvalue()
    err = stderr.getvalue()
    
    assert "Running default test suite..." in out
    # Assuming test runner prints "No test commands discovered" warning or summary says ok
    assert "All tests passed successfully." in out

def test_test_last_empty(tmp_path: Path):
    stdin = io.StringIO("/test last\n/exit\n")
    stdout = io.StringIO()
    stderr = io.StringIO()
    
    code = run_shell(
        stdin=stdin,
        stdout=stdout,
        stderr=stderr,
        project_root=tmp_path,
        main=lambda argv: 0
    )
    
    assert code == 0
    err = stderr.getvalue()
    assert "No previous test run recorded in this session." in err

"""Unit tests for the REPL loop in isolation.

Drives ``run_shell()`` with injected stdin/stdout/stderr file objects so the
loop is exercised without monkey-patching ``sys.*``. The ``main`` callable is
also injected so the loop can be tested without re-entering the real CLI."""

from __future__ import annotations

import io
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from mythic_vibe_cli.exit_codes import SUCCESS, USER_INPUT_ERROR
from mythic_vibe_cli.repl import BANNER, PROMPT, run_shell


class _FakeMain:
    def __init__(self, return_codes: list[int] | None = None) -> None:
        self.calls: list[list[str]] = []
        self._codes = list(return_codes) if return_codes is not None else []

    def __call__(self, argv: list[str]) -> int:
        self.calls.append(list(argv))
        if self._codes:
            return self._codes.pop(0)
        return SUCCESS


class ReplLoopTests(unittest.TestCase):
    def _drive(self, lines: list[str], main: _FakeMain | None = None) -> tuple[int, str, str]:
        # Append a final empty line to simulate EOF after the input.
        text = "".join(lines)
        stdin = io.StringIO(text)
        stdout = io.StringIO()
        stderr = io.StringIO()
        result = run_shell(
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
            main=main if main is not None else _FakeMain(),
            project_root=Path("."),
        )
        return result, stdout.getvalue(), stderr.getvalue()

    def test_eof_exits_cleanly_with_success(self) -> None:
        code, out, _err = self._drive([])
        self.assertEqual(code, SUCCESS)
        self.assertIn(BANNER, out)
        self.assertIn(PROMPT, out)
        self.assertIn("Project:", out)
        self.assertIn("Branch:", out)
        self.assertIn("Model:", out)
        self.assertIn("Knowledge:", out)

    def test_quit_exits_cleanly(self) -> None:
        code, out, _err = self._drive(["/quit\n"])
        self.assertEqual(code, SUCCESS)
        self.assertIn(BANNER, out)

    def test_exit_alias_exits_cleanly(self) -> None:
        code, _out, _err = self._drive(["/exit\n"])
        self.assertEqual(code, SUCCESS)

    def test_help_lists_builtin_catalog(self) -> None:
        code, out, _err = self._drive(["/help\n", "/quit\n"])
        self.assertEqual(code, SUCCESS)
        for required in {"/help", "/model", "/status", "/scan", "/quit"}:
            self.assertIn(required, out)

    def test_model_local_reports_current_fallback_model(self) -> None:
        code, out, _err = self._drive(["/model\n", "/quit\n"])
        self.assertEqual(code, SUCCESS)
        self.assertIn("Provider: copy-paste", out)
        self.assertIn("Model: manual", out)

    def test_model_list_reports_provider_registry(self) -> None:
        code, out, _err = self._drive(["/model list\n", "/quit\n"])
        self.assertEqual(code, SUCCESS)
        self.assertIn("Model providers", out)
        self.assertIn("copy-paste", out)

    def test_model_set_persists_project_json_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stdin = io.StringIO("/model set openai gpt-4o-mini\n/model\n/quit\n")
            stdout = io.StringIO()

            code = run_shell(
                stdin=stdin,
                stdout=stdout,
                stderr=io.StringIO(),
                main=_FakeMain(),
                project_root=root,
            )

            payload = json.loads((root / ".mythic-vibe.json").read_text(encoding="utf-8"))

        self.assertEqual(code, SUCCESS)
        self.assertEqual(payload["ai"]["provider"], "openai")
        self.assertEqual(payload["ai"]["model"], "gpt-4o-mini")
        self.assertIn("Provider: openai", stdout.getvalue())
        self.assertIn("Model: gpt-4o-mini", stdout.getvalue())

    def test_natural_project_question_returns_context_without_dispatch(self) -> None:
        fake = _FakeMain()
        code, out, _err = self._drive(["What project am I in?\n", "/quit\n"], main=fake)
        self.assertEqual(code, SUCCESS)
        self.assertIn("You are in this project context", out)
        self.assertIn("Project:", out)
        self.assertEqual(fake.calls, [])

    def test_natural_find_request_runs_context_scan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pyproject.toml").write_text("[project]\nname='example'\n", encoding="utf-8")
            (root / "mythic_vibe_cli" / "memory").mkdir(parents=True)
            (root / "mythic_vibe_cli" / "memory" / "store.py").write_text(
                "memory recall logic\n",
                encoding="utf-8",
            )
            stdin = io.StringIO("Find the memory system in this repo.\n/quit\n")
            stdout = io.StringIO()
            fake = _FakeMain()

            code = run_shell(
                stdin=stdin,
                stdout=stdout,
                stderr=io.StringIO(),
                main=fake,
                project_root=root,
            )

        self.assertEqual(code, SUCCESS)
        self.assertIn("Repository context", stdout.getvalue())
        self.assertIn("mythic_vibe_cli/memory/store.py", stdout.getvalue())
        self.assertEqual(fake.calls, [])

    def test_generic_natural_prompt_uses_selected_model_fallback(self) -> None:
        fake = _FakeMain()
        code, out, _err = self._drive(["Tell me a short plan.\n", "/quit\n"], main=fake)
        self.assertEqual(code, SUCCESS)
        self.assertIn("Model: copy-paste/manual", out)
        self.assertIn("Provider-ready prompt", out)
        self.assertIn("Tell me a short plan.", out)
        self.assertEqual(fake.calls, [])

    def test_generic_natural_prompt_records_memory_spine(self) -> None:
        from mythic_vibe_cli.memory.spine import list_memory

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stdin = io.StringIO("Tell me a short plan.\n/quit\n")
            stdout = io.StringIO()
            fake = _FakeMain()

            code = run_shell(
                stdin=stdin,
                stdout=stdout,
                stderr=io.StringIO(),
                main=fake,
                project_root=root,
            )
            entries = list_memory(root)

        self.assertEqual(code, SUCCESS)
        self.assertTrue(any(entry.kind == "task" for entry in entries))
        self.assertTrue(
            any("Tell me a short plan." in entry.content for entry in entries)
        )
        self.assertEqual(fake.calls, [])

    def test_last_time_question_uses_memory_spine(self) -> None:
        from mythic_vibe_cli.memory.spine import record_memory

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            record_memory(root, "session_summary", "We were wiring Phase 5 memory.")
            stdin = io.StringIO("What were we doing last time?\n/quit\n")
            stdout = io.StringIO()
            fake = _FakeMain()

            code = run_shell(
                stdin=stdin,
                stdout=stdout,
                stderr=io.StringIO(),
                main=fake,
                project_root=root,
            )

        self.assertEqual(code, SUCCESS)
        self.assertIn("Last remembered work", stdout.getvalue())
        self.assertIn("We were wiring Phase 5 memory.", stdout.getvalue())
        self.assertEqual(fake.calls, [])

    def test_knowledge_prompt_searches_private_sqlite_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db_path = root / "knowledge.sqlite"
            with sqlite3.connect(db_path) as conn:
                conn.execute("CREATE TABLE notes(title TEXT, body TEXT, source TEXT)")
                conn.execute(
                    "INSERT INTO notes(title, body, source) VALUES (?, ?, ?)",
                    (
                        "Hermes memory",
                        "Earlier ideas linked Hermes memory to private notes.",
                        "tailnet",
                    ),
                )
            (root / ".mythic-vibe.json").write_text(
                json.dumps(
                    {
                        "knowledge": {
                            "sources": [
                                {
                                    "name": "tailnet-notes",
                                    "type": "sqlite",
                                    "path": str(db_path),
                                    "table": "notes",
                                }
                            ]
                        }
                    }
                ),
                encoding="utf-8",
            )
            stdin = io.StringIO(
                "Search my knowledge database for earlier ideas about Hermes memory.\n/quit\n"
            )
            stdout = io.StringIO()
            fake = _FakeMain()

            code = run_shell(
                stdin=stdin,
                stdout=stdout,
                stderr=io.StringIO(),
                main=fake,
                project_root=root,
            )

        self.assertEqual(code, SUCCESS)
        self.assertIn("Knowledge search:", stdout.getvalue())
        self.assertIn("Earlier ideas linked Hermes memory", stdout.getvalue())
        self.assertEqual(fake.calls, [])

    def test_workspace_prompt_proposes_without_dispatch(self) -> None:
        fake = _FakeMain()
        code, out, _err = self._drive(
            ["Clone https://github.com/acme/hermes and make a branch for fixing memory.\n", "/quit\n"],
            main=fake,
        )
        self.assertEqual(code, SUCCESS)
        self.assertIn("Workspace proposal", out)
        self.assertIn("No changes were made", out)
        self.assertEqual(fake.calls, [])

    def test_empty_lines_do_not_dispatch(self) -> None:
        fake = _FakeMain()
        code, _out, _err = self._drive(["\n", "\n", "\n", "/quit\n"], main=fake)
        self.assertEqual(code, SUCCESS)
        self.assertEqual(fake.calls, [])

    def test_real_command_dispatches_through_main(self) -> None:
        fake = _FakeMain()
        code, _out, _err = self._drive(["/scan --path .\n", "/quit\n"], main=fake)
        self.assertEqual(code, SUCCESS)
        self.assertEqual(len(fake.calls), 1)
        self.assertEqual(fake.calls[0], ["scan", "--path", "."])

    def test_bare_command_dispatches_through_main(self) -> None:
        """A line without a leading slash is also dispatched."""
        fake = _FakeMain()
        code, _out, _err = self._drive(["status --json\n", "/quit\n"], main=fake)
        self.assertEqual(code, SUCCESS)
        self.assertEqual(fake.calls, [["status", "--json"]])

    def test_non_zero_exit_code_is_surfaced_but_loop_continues(self) -> None:
        fake = _FakeMain(return_codes=[USER_INPUT_ERROR])
        code, out, _err = self._drive(["/scan --bad-flag\n", "/quit\n"], main=fake)
        self.assertEqual(code, SUCCESS)
        self.assertIn(f"exit code: {USER_INPUT_ERROR}", out)

    def test_main_systemexit_is_caught_loop_continues(self) -> None:
        def raising_main(_argv: list[str]) -> int:
            raise SystemExit(2)

        stdin = io.StringIO("/scan --bogus\n/quit\n")
        stdout = io.StringIO()
        stderr = io.StringIO()
        code = run_shell(
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
            main=raising_main,
            project_root=Path("."),
        )
        self.assertEqual(code, SUCCESS)
        self.assertIn("exit code: 2", stdout.getvalue())

    def test_main_unexpected_exception_is_caught(self) -> None:
        def raising_main(_argv: list[str]) -> int:
            raise RuntimeError("kaboom")

        stdin = io.StringIO("/scan\n/quit\n")
        stdout = io.StringIO()
        stderr = io.StringIO()
        code = run_shell(
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
            main=raising_main,
            project_root=Path("."),
        )
        self.assertEqual(code, SUCCESS)
        self.assertIn("Command failed", stderr.getvalue())
        self.assertIn("kaboom", stderr.getvalue())

    def test_quoted_arguments_are_parsed_via_shlex(self) -> None:
        fake = _FakeMain()
        code, _out, _err = self._drive(
            ['/packet create --task "hello world" --phase build\n', "/quit\n"],
            main=fake,
        )
        self.assertEqual(code, SUCCESS)
        self.assertEqual(
            fake.calls[0],
            ["packet", "create", "--task", "hello world", "--phase", "build"],
        )

    def test_bad_quote_emits_parse_error_loop_continues(self) -> None:
        fake = _FakeMain()
        code, _out, err = self._drive(
            ['/packet create --task "unclosed\n', "/quit\n"],
            main=fake,
        )
        self.assertEqual(code, SUCCESS)
        self.assertEqual(fake.calls, [])
        self.assertIn("Parse error", err)


if __name__ == "__main__":
    unittest.main()

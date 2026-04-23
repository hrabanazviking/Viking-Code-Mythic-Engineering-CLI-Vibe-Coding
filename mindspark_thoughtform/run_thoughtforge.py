"""
run_thoughtforge.py — MindSpark: ThoughtForge interactive CLI.

Usage:
  # Interactive REPL:
  python run_thoughtforge.py

  # Persistent chat mode:
  python run_thoughtforge.py --chat

  # Single query:
  python run_thoughtforge.py "What is Yggdrasil?"

  # With a GGUF model:
  python run_thoughtforge.py --model /models/phi-3-mini-q4.gguf

  # Chat with history file:
  python run_thoughtforge.py --chat --history sessions/my_session.json

  # With a system prompt:
  python run_thoughtforge.py --chat --system "You are a Norse mythology expert."

  # Show backend info:
  python run_thoughtforge.py --backend

  # Override hardware profile:
  python run_thoughtforge.py --profile desktop_cpu

  # Debug logging:
  python run_thoughtforge.py --debug
"""

from __future__ import annotations

import argparse
import logging
import sys

# Ensure UTF-8 output on Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="run_thoughtforge",
        description="MindSpark: ThoughtForge — Memory-Enforced Cognition Engine",
    )
    p.add_argument(
        "query",
        nargs="?",
        default=None,
        help="Single query to run (omit for interactive REPL mode)",
    )
    p.add_argument(
        "--model",
        metavar="PATH",
        default=None,
        help="Path to a GGUF model file (optional — knowledge-only mode if omitted)",
    )
    p.add_argument(
        "--profile",
        metavar="PROFILE",
        default="auto",
        help="Hardware profile: auto|phone_low|pi_zero|pi_5|desktop_cpu|desktop_gpu|server_gpu",
    )
    p.add_argument(
        "--retrieval",
        metavar="PATH",
        default=None,
        choices=["sql", "vector", "hybrid"],
        help="Retrieval path override: sql|vector|hybrid (default: auto from intent)",
    )
    p.add_argument(
        "--chat",
        action="store_true",
        default=False,
        help="Enter persistent chat mode",
    )
    p.add_argument(
        "--history",
        metavar="FILE",
        default=None,
        help="Load chat history from FILE at start; auto-save on exit",
    )
    p.add_argument(
        "--system",
        metavar="PROMPT",
        default=None,
        help="Set system prompt for this session",
    )
    p.add_argument(
        "--backend",
        action="store_true",
        default=False,
        help="Show current backend info and exit",
    )
    p.add_argument(
        "--debug",
        action="store_true",
        default=False,
        help="Enable DEBUG logging",
    )
    return p


def _setup_logging(debug: bool) -> None:
    level = logging.DEBUG if debug else logging.WARNING
    logging.basicConfig(
        format="%(levelname)s [%(name)s] %(message)s",
        level=level,
        stream=sys.stderr,
    )


def _display_result(result: object, query: str) -> None:
    sep = "═" * 72

    print(f"\n{sep}")
    print(result.text)  # type: ignore[attr-defined]
    print(sep)

    citations = getattr(result, "citations", [])
    scores = getattr(result, "scores", None)
    enforcement_passed = getattr(result, "enforcement_passed", False)
    enforcement_notes = getattr(result, "enforcement_notes", "")
    token_count = getattr(result, "token_count", 0)

    cite_str = ", ".join(citations) if citations else "none"
    confidence = scores.composite if scores else 0.0
    quality = scores.quality_tier if scores else "—"
    enf_str = "PASS" if enforcement_passed else f"REVIEW ({enforcement_notes})"

    print(f"Citations   : {cite_str}")
    print(f"Confidence  : {confidence:.3f}  [{quality}]")
    print(f"Enforcement : {enf_str}")
    print(f"Tokens      : {token_count}")
    print()


def _show_backend_info() -> None:
    from thoughtforge.inference.unified_backend import load_backend_from_config
    backend = load_backend_from_config()
    if backend is None:
        print("Backend: none configured (knowledge-only mode)")
        print("Run `python setup_thoughtforge.py` to configure a backend.")
        return
    print(f"Backend     : {backend.backend_name()}")
    healthy = backend.health_check()
    print(f"Health      : {'OK' if healthy else 'UNREACHABLE'}")


def _handle_chat_command(
    command: str,
    history: object,
    history_file: str | None,
) -> None:
    parts = command.strip().split(None, 1)
    cmd = parts[0].lower()

    if cmd == "/clear":
        history.clear()  # type: ignore[attr-defined]
        print("History cleared.")

    elif cmd == "/save":
        if history_file:
            history.save(Path(history_file))  # type: ignore[attr-defined]
            print(f"Saved to {history_file}")
        else:
            dest = parts[1].strip() if len(parts) > 1 else ""
            if dest:
                history.save(Path(dest))  # type: ignore[attr-defined]
                print(f"Saved to {dest}")
            else:
                print("Usage: /save [FILE]  (no default history file set)")

    elif cmd == "/load":
        if len(parts) < 2:
            print("Usage: /load FILE")
            return
        src = Path(parts[1].strip())
        if not src.exists():
            print(f"File not found: {src}")
            return
        from thoughtforge.cognition.chat_history import ChatHistory
        loaded = ChatHistory.load(src)
        # Replace messages in-place
        history.messages.clear()          # type: ignore[attr-defined]
        history.messages.extend(loaded.messages)  # type: ignore[attr-defined]
        print(f"Loaded {len(history)} turns from {src}")

    elif cmd == "/history":
        print(history.format_for_display())  # type: ignore[attr-defined]

    elif cmd in ("/quit", "/exit", "/q"):
        raise KeyboardInterrupt

    else:
        print(f"Unknown command: {cmd}")
        print("Commands: /clear  /save [FILE]  /load FILE  /history  /quit")


def _run_chat(
    core: object,
    retrieval_path: str | None,
    history_file: str | None,
    system_prompt: str | None,
) -> None:
    from thoughtforge.cognition.chat_history import ChatHistory
    from thoughtforge.inference.unified_backend import load_backend_from_config

    history = ChatHistory(system_prompt=system_prompt or "")
    if history_file and Path(history_file).exists():
        history = ChatHistory.load(Path(history_file))

    # Backend info for header
    backend = load_backend_from_config()
    backend_label = backend.backend_name() if backend else "knowledge-only"

    print("MindSpark: ThoughtForge — Chat Mode")
    print(f"Backend: {backend_label}")
    if history_file:
        print(f"History: {history_file}  ({len(history)} turns loaded)")
    print("Commands: /clear  /save [FILE]  /load FILE  /history  /quit")
    print()

    while True:
        try:
            user_input = input("You > ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input:
            continue

        if user_input.startswith("/"):
            try:
                _handle_chat_command(user_input, history, history_file)
            except KeyboardInterrupt:
                break
            continue

        history.add_user(user_input)
        try:
            result = core.think(  # type: ignore[attr-defined]
                user_input,
                retrieval_path=retrieval_path,
                history=history,
            )
        except Exception as e:
            print(f"[Forge Error] {e}", file=sys.stderr)
            continue

        history.add_assistant(result.text, turn_id=result.turn_id)
        print(f"\nForge > {result.text}\n")

        citations = getattr(result, "citations", [])
        retrieval_confidence = getattr(result, "retrieval_confidence", 0.0)
        enforcement_passed = getattr(result, "enforcement_passed", False)
        if citations:
            enf = "PASS" if enforcement_passed else "REVIEW"
            print(
                f"  [Citations: {', '.join(citations[:3])} | "
                f"Confidence: {retrieval_confidence:.2f} | {enf}]"
            )
        print()

    if history_file:
        history.save(Path(history_file))
        print(f"History saved to {history_file}")
    else:
        print("The forge grows quiet. Walk well.")


def _run_single(core: object, query: str, retrieval_path: str | None) -> None:
    result = core.think(query, retrieval_path=retrieval_path)  # type: ignore[attr-defined]
    _display_result(result, query)


def _run_repl(core: object, retrieval_path: str | None) -> None:
    print("MindSpark: ThoughtForge")
    print("The forge is ready. Type 'exit' or 'quit' to leave.\n")

    while True:
        try:
            query = input("Forge> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nThe forge grows quiet. Walk well.")
            break

        if not query:
            continue

        if query.lower() in ("exit", "quit", "q", ":q"):
            print("The forge grows quiet. Walk well.")
            break

        try:
            result = core.think(query, retrieval_path=retrieval_path)  # type: ignore[attr-defined]
            _display_result(result, query)
        except Exception as e:
            print(f"[Forge Error] {e}", file=sys.stderr)


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    _setup_logging(args.debug)

    # Import here so logging is set up first
    from thoughtforge.cognition.core import ThoughtForgeCore
    from thoughtforge.utils.errors import ThoughtForgeError
    from thoughtforge.utils.logging_setup import setup_logging

    if not args.debug:
        setup_logging(config={"logging": {"level": "WARNING"}})

    if args.backend:
        _show_backend_info()
        return

    try:
        # Load unified backend from user_config.yaml if present
        from thoughtforge.inference.unified_backend import load_backend_from_config
        unified_backend = load_backend_from_config()

        model_path = Path(args.model) if args.model else None
        core = ThoughtForgeCore(model_path=model_path, backend=unified_backend)

        if args.chat:
            _run_chat(core, args.retrieval, args.history, args.system)
        elif args.query:
            _run_single(core, args.query, args.retrieval)
        else:
            _run_repl(core, args.retrieval)

    except ThoughtForgeError as exc:
        print(f"\nThoughtForge Error: {exc.message}", file=sys.stderr)
        if exc.suggested_fix:
            print(f"Fix: {exc.suggested_fix}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nThe forge grows quiet. Walk well.")


if __name__ == "__main__":
    main()

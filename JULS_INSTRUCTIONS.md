# Instructions for Jules: The Norse Saga Engine

## 1. Environment & Pathing (CRITICAL)
- This project runs in **WSL2 (Ubuntu)**.
- **NEVER use absolute Windows paths** (e.g., C:\...). Always use relative paths (e.g., ./data/runes.json).
- Use `os.path.join` or the `pathlib` library to ensure cross-platform compatibility.

## 2. Coding Standards
- Language: **Python 3.10+**
- Style: Follow PEP 8, but prioritize readability for "Vibe Coding."
- Documentation: Every function must have a docstring explaining its "magical" or logical purpose.

## 3. Environment Variables
- All secrets, API keys (OpenRouter, Gemini), and local paths must be pulled from environment variables.
- Use `load_dotenv()` at the entry point of scripts.
- Never hardcode the actual keys; only reference the variable names.

## 4. GitHub Workflow
- Always perform work on a new feature branch.
- Provide a detailed summary of changes in the Pull Request.
- If a task takes multiple steps, commit incremental progress so I can review it on my monitors.
from __future__ import annotations

from dataclasses import dataclass, field
import ast
import json
import os
from pathlib import Path
from typing import Any

from .runtime.atomic_write import atomic_write_text
from .runtime.paths import config_candidates, paths_for


@dataclass
class AppConfig:
    excerpt_limit: int = 1800
    packet_char_budget: int = 12000
    auto_compact: bool = True
    method_source: str = "https://github.com/hrabanazviking/Mythic-Engineering"
    ai_provider: str = "copy-paste"
    ai_model: str = "manual"
    ai_context_window_tokens: int = 127000
    ai_max_output_tokens: int = 8192
    ai_request_timeout_seconds: int = 120
    ai_temperature: float = 0.2
    ai_top_p: float = 0.95
    ai_router: dict[str, Any] = field(default_factory=dict)
    ai_services: dict[str, Any] = field(default_factory=dict)
    ai_model_routes: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    ai_routing_rules: list[dict[str, Any]] = field(default_factory=list)
    ai_prompts: dict[str, str] = field(default_factory=dict)
    knowledge_sources: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class LoadedConfig:
    config: AppConfig
    sources: list[Path]


class ConfigStore:
    def __init__(self, project_root: Path | None = None):
        self.project_root = project_root.resolve() if project_root else None

    def _candidate_paths(self) -> list[Path]:
        return list(config_candidates(self.project_root))

    def load(self) -> LoadedConfig:
        payload: dict = {}
        sources: list[Path] = []

        for path in self._candidate_paths():
            if not path.exists():
                continue
            try:
                data = _load_config_payload(path)
            except (ValueError, OSError):
                continue
            if isinstance(data, dict):
                payload = _deep_merge(payload, data)
                sources.append(path)

        codex = payload.get("codex", {}) if isinstance(payload.get("codex", {}), dict) else {}
        method = payload.get("method", {}) if isinstance(payload.get("method", {}), dict) else {}
        ai = payload.get("ai", {}) if isinstance(payload.get("ai", {}), dict) else {}
        ai_router = ai.get("router", {}) if isinstance(ai.get("router", {}), dict) else {}
        ai_services = ai.get("services", {}) if isinstance(ai.get("services", {}), dict) else {}
        ai_prompts = _parse_prompt_templates(
            payload.get("prompts", ai.get("prompts", {}))
        )
        knowledge = payload.get("knowledge", {}) if isinstance(payload.get("knowledge", {}), dict) else {}
        knowledge_sources = _parse_knowledge_sources(knowledge.get("sources", []))
        env_knowledge_path = os.environ.get("MYTHIC_KNOWLEDGE_SQLITE_PATH", "").strip()
        if env_knowledge_path:
            knowledge_sources.append(
                {
                    "name": os.environ.get("MYTHIC_KNOWLEDGE_NAME", "env-sqlite").strip() or "env-sqlite",
                    "type": "sqlite",
                    "path": env_knowledge_path,
                    "host": os.environ.get("MYTHIC_KNOWLEDGE_HOST", "").strip(),
                }
            )

        config = AppConfig(
            excerpt_limit=_parse_int_env(
                "MYTHIC_EXCERPT_LIMIT",
                codex.get("excerpt_limit", 1800),
                minimum=200,
                maximum=12000,
            ),
            packet_char_budget=_parse_int_env(
                "MYTHIC_PACKET_CHAR_BUDGET",
                codex.get("packet_char_budget", 12000),
                minimum=1000,
                maximum=100000,
            ),
            auto_compact=_parse_bool_env("MYTHIC_AUTO_COMPACT", codex.get("auto_compact", True)),
            method_source=_parse_str_env(
                "MYTHIC_METHOD_SOURCE",
                method.get("source", AppConfig.method_source),
            ),
            ai_provider=_parse_str_env(
                "MYTHIC_AI_PROVIDER",
                ai.get("provider", AppConfig.ai_provider),
            ),
            ai_model=_parse_str_env(
                "MYTHIC_AI_MODEL",
                ai.get("model", AppConfig.ai_model),
            ),
            ai_context_window_tokens=_parse_int_env(
                "MYTHIC_AI_CONTEXT_WINDOW_TOKENS",
                ai.get("context_window_tokens", AppConfig.ai_context_window_tokens),
                minimum=1000,
                maximum=2_000_000,
            ),
            ai_max_output_tokens=_parse_int_env(
                "MYTHIC_AI_MAX_OUTPUT_TOKENS",
                ai.get("max_output_tokens", AppConfig.ai_max_output_tokens),
                minimum=128,
                maximum=200_000,
            ),
            ai_request_timeout_seconds=_parse_int_env(
                "MYTHIC_AI_REQUEST_TIMEOUT_SECONDS",
                ai.get("request_timeout_seconds", AppConfig.ai_request_timeout_seconds),
                minimum=1,
                maximum=3600,
            ),
            ai_temperature=_parse_float_env(
                "MYTHIC_AI_TEMPERATURE",
                ai.get("temperature", AppConfig.ai_temperature),
                minimum=0.0,
                maximum=2.0,
            ),
            ai_top_p=_parse_float_env(
                "MYTHIC_AI_TOP_P",
                ai.get("top_p", AppConfig.ai_top_p),
                minimum=0.0,
                maximum=1.0,
            ),
            ai_router=ai_router,
            ai_services=ai_services,
            ai_model_routes=_parse_model_routes(ai_router, ai_services),
            ai_routing_rules=_parse_routing_rules(ai_router),
            ai_prompts=ai_prompts,
            knowledge_sources=knowledge_sources,
        )

        return LoadedConfig(config=config, sources=sources)

    def raw_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        for path in self._candidate_paths():
            if not path.exists():
                continue
            try:
                data = _load_config_payload(path)
            except (ValueError, OSError):
                continue
            if isinstance(data, dict):
                payload = _deep_merge(payload, data)
        return payload

    def save_project_values(self, updates: dict[str, Any]) -> Path:
        """Merge dotted-key updates into ``<project>/.mythic-vibe.json``.

        This is the JSON config path :meth:`load` already reads. The
        legacy ``config set`` command still writes ``mythic/config.toml``
        for compatibility; companion-shell model selection uses this
        method so the saved values actually participate in runtime
        resolution.
        """
        if self.project_root is None:
            raise ValueError("project_root is required to save project config")

        path = paths_for(self.project_root).project_config_file
        payload: dict[str, Any] = {}
        if path.exists():
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                raw = {}
            if isinstance(raw, dict):
                payload = raw

        for key, value in updates.items():
            _set_dotted(payload, key, value)

        atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")
        return path


def _deep_merge(base: dict, incoming: dict) -> dict:
    out = dict(base)
    for key, value in incoming.items():
        if key in out and isinstance(out[key], dict) and isinstance(value, dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def _load_config_payload(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        payload = json.loads(text)
    elif path.suffix.lower() in {".yaml", ".yml"}:
        payload = _parse_yaml_subset(text)
    else:
        raise ValueError(f"unsupported config file suffix: {path.suffix}")
    if not isinstance(payload, dict):
        raise ValueError(f"config file must contain an object: {path}")
    return payload


def _parse_yaml_subset(text: str) -> dict[str, Any]:
    """Parse the small YAML subset used by Mythic Vibe config files.

    Supported intentionally: nested mappings, lists, quoted strings,
    booleans, ints/floats, nulls, and literal/folded block scalars.
    This keeps the base package stdlib-only while still making
    ``config.yaml`` genuinely editable.
    """
    parser = _YamlSubsetParser(text)
    payload = parser.parse()
    if not isinstance(payload, dict):
        raise ValueError("YAML config root must be a mapping")
    return payload


class _YamlSubsetParser:
    def __init__(self, text: str):
        self.lines = text.splitlines()

    def parse(self) -> Any:
        index = self._next_content(0)
        if index >= len(self.lines):
            return {}
        value, index = self._parse_node(index, self._indent(index))
        return value

    def _next_content(self, index: int) -> int:
        while index < len(self.lines):
            stripped = self.lines[index].strip()
            if stripped and not stripped.startswith("#"):
                return index
            index += 1
        return index

    def _indent(self, index: int) -> int:
        line = self.lines[index]
        return len(line) - len(line.lstrip(" "))

    def _parse_node(self, index: int, indent: int) -> tuple[Any, int]:
        index = self._next_content(index)
        if index >= len(self.lines):
            return {}, index
        stripped = self.lines[index].strip()
        if self._indent(index) < indent:
            return {}, index
        if stripped.startswith("- "):
            return self._parse_list(index, indent)
        return self._parse_map(index, indent)

    def _parse_map(self, index: int, indent: int) -> tuple[dict[str, Any], int]:
        out: dict[str, Any] = {}
        while index < len(self.lines):
            index = self._next_content(index)
            if index >= len(self.lines):
                break
            current_indent = self._indent(index)
            if current_indent < indent:
                break
            if current_indent > indent:
                break
            stripped = self.lines[index].strip()
            if stripped.startswith("- "):
                break
            key, value = self._split_key_value(stripped)
            if value in {"|", ">"}:
                block, index = self._parse_block_scalar(index + 1, indent, folded=(value == ">"))
                out[key] = block
                continue
            if value == "":
                child_index = self._next_content(index + 1)
                if child_index < len(self.lines) and self._indent(child_index) > indent:
                    child, index = self._parse_node(child_index, self._indent(child_index))
                    out[key] = child
                    continue
                out[key] = {}
                index = child_index
                continue
            out[key] = self._parse_scalar(value)
            index += 1
        return out, index

    def _parse_list(self, index: int, indent: int) -> tuple[list[Any], int]:
        out: list[Any] = []
        while index < len(self.lines):
            index = self._next_content(index)
            if index >= len(self.lines):
                break
            current_indent = self._indent(index)
            if current_indent < indent:
                break
            if current_indent > indent:
                break
            stripped = self.lines[index].strip()
            if not stripped.startswith("- "):
                break
            rest = stripped[2:].strip()
            if rest == "":
                child_index = self._next_content(index + 1)
                if child_index < len(self.lines) and self._indent(child_index) > indent:
                    child, index = self._parse_node(child_index, self._indent(child_index))
                    out.append(child)
                    continue
                out.append(None)
                index = child_index
                continue
            if self._looks_like_inline_map(rest):
                key, value = self._split_key_value(rest)
                item: dict[str, Any] = {key: self._parse_scalar(value) if value else {}}
                child_index = self._next_content(index + 1)
                if child_index < len(self.lines) and self._indent(child_index) > indent:
                    child, index = self._parse_node(child_index, self._indent(child_index))
                    if isinstance(child, dict):
                        item = _deep_merge(item, child)
                    else:
                        item[key] = child
                    out.append(item)
                    continue
                out.append(item)
                index += 1
                continue
            out.append(self._parse_scalar(rest))
            index += 1
        return out, index

    def _parse_block_scalar(self, index: int, parent_indent: int, *, folded: bool) -> tuple[str, int]:
        block_lines: list[str] = []
        content_indent: int | None = None
        while index < len(self.lines):
            raw = self.lines[index]
            stripped = raw.strip()
            if not stripped:
                block_lines.append("")
                index += 1
                continue
            indent = len(raw) - len(raw.lstrip(" "))
            if indent <= parent_indent:
                break
            if content_indent is None:
                content_indent = indent
            trim = min(content_indent, len(raw))
            block_lines.append(raw[trim:])
            index += 1
        if folded:
            return " ".join(line.strip() for line in block_lines if line.strip()), index
        return "\n".join(block_lines).rstrip("\n"), index

    def _split_key_value(self, text: str) -> tuple[str, str]:
        if ":" not in text:
            raise ValueError(f"expected key: value line, got {text!r}")
        key, value = text.split(":", 1)
        key = key.strip().strip("'\"")
        if not key:
            raise ValueError("empty YAML key")
        return key, value.strip()

    def _looks_like_inline_map(self, text: str) -> bool:
        if ": " not in text and not text.endswith(":"):
            return False
        key = text.split(":", 1)[0]
        return bool(key) and all(ch.isalnum() or ch in "_.-" for ch in key)

    def _parse_scalar(self, text: str) -> Any:
        value = text.strip()
        if value == "":
            return ""
        if value[0:1] in {"'", '"'} and value[-1:] == value[0]:
            try:
                return ast.literal_eval(value)
            except (SyntaxError, ValueError):
                return value[1:-1]
        lowered = value.lower()
        if lowered in {"true", "yes", "on"}:
            return True
        if lowered in {"false", "no", "off"}:
            return False
        if lowered in {"null", "none", "~"}:
            return None
        if value.startswith("[") or value.startswith("{"):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        try:
            return int(value.replace("_", ""))
        except ValueError:
            pass
        try:
            return float(value)
        except ValueError:
            return value


def _set_dotted(payload: dict[str, Any], key: str, value: Any) -> None:
    parts = [part for part in key.split(".") if part]
    if not parts:
        return
    target = payload
    for part in parts[:-1]:
        current = target.get(part)
        if not isinstance(current, dict):
            current = {}
            target[part] = current
        target = current
    target[parts[-1]] = value


def _parse_knowledge_sources(raw: object) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    sources: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        source = {str(key): value for key, value in item.items() if isinstance(key, str)}
        if source:
            sources.append(source)
    return sources


def _parse_prompt_templates(raw: object) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    prompts: dict[str, str] = {}
    for key, value in raw.items():
        if isinstance(key, str) and isinstance(value, str):
            prompts[key] = value
    return prompts


def _parse_model_routes(
    router: dict[str, Any],
    services: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    raw_types = router.get("model_types", {})
    if not isinstance(raw_types, dict):
        return {}
    routes: dict[str, list[dict[str, Any]]] = {}
    for route_name, route_payload in raw_types.items():
        if not isinstance(route_name, str) or not isinstance(route_payload, dict):
            continue
        attempts: list[dict[str, Any]] = []
        for service_name in route_payload.get("service_order", []):
            if not isinstance(service_name, str):
                continue
            service_payload = services.get(service_name, {})
            if not isinstance(service_payload, dict):
                continue
            service_model_types = service_payload.get("model_types", {})
            if not isinstance(service_model_types, dict):
                continue
            models = service_model_types.get(route_name, [])
            if not isinstance(models, list):
                continue
            for model in models:
                if isinstance(model, dict):
                    item = {str(k): v for k, v in model.items() if isinstance(k, str)}
                    item.setdefault("provider", service_name)
                    attempts.append(item)
                elif isinstance(model, str):
                    attempts.append({"provider": service_name, "id": model})
        routes[route_name] = attempts
    return routes


def _parse_routing_rules(router: dict[str, Any]) -> list[dict[str, Any]]:
    raw = router.get("routing_rules", [])
    if not isinstance(raw, list):
        return []
    rules: list[dict[str, Any]] = []
    for item in raw:
        if isinstance(item, dict):
            rules.append({str(key): value for key, value in item.items() if isinstance(key, str)})
    return rules


def _parse_int_env(name: str, fallback: int, minimum: int, maximum: int) -> int:
    raw = os.environ.get(name)
    value = fallback
    if raw is not None:
        try:
            value = int(raw)
        except ValueError:
            value = fallback
    return max(minimum, min(maximum, int(value)))


def _parse_bool_env(name: str, fallback: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return bool(fallback)

    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return bool(fallback)


def _parse_float_env(name: str, fallback: object, minimum: float, maximum: float) -> float:
    raw = os.environ.get(name)
    value = fallback
    if raw is not None:
        value = raw
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = float(minimum)
    return max(minimum, min(maximum, parsed))


def _parse_str_env(name: str, fallback: str) -> str:
    raw = os.environ.get(name)
    if raw is not None and raw.strip():
        return raw.strip()
    return str(fallback).strip()

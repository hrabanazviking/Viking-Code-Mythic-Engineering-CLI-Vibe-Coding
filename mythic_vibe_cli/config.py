from __future__ import annotations

from dataclasses import dataclass, field
import ast
import json
import os
from pathlib import Path
import string
from typing import Any

from .runtime.atomic_write import atomic_write_text
from .runtime.paths import config_candidates, paths_for


CURRENT_CONFIG_SCHEMA_VERSION = 1
KNOWN_AI_PROVIDERS = {
    "anthropic",
    "copy-paste",
    "gemini",
    "local",
    "mindspark",
    "ollama",
    "openai",
    "openrouter",
    "yggdrasil",
}
PROVIDERS_REQUIRING_API_KEYS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "openai": "OPENAI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}


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
    ai_retry_attempts: int = 2
    ai_daily_cost_cap_usd: float = 0.0
    ai_temperature: float = 0.2
    ai_top_p: float = 0.95
    ai_router: dict[str, Any] = field(default_factory=dict)
    ai_services: dict[str, Any] = field(default_factory=dict)
    ai_model_routes: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    ai_routing_rules: list[dict[str, Any]] = field(default_factory=list)
    ai_prompts: dict[str, str] = field(default_factory=dict)
    knowledge_sources: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class ConfigDiagnostic:
    severity: str
    code: str
    path: str
    message: str
    source: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "severity": self.severity,
            "code": self.code,
            "path": self.path,
            "message": self.message,
            "source": self.source,
        }


@dataclass
class LoadedConfig:
    config: AppConfig
    sources: list[Path]
    diagnostics: list[ConfigDiagnostic] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(item.severity == "error" for item in self.diagnostics)


class ConfigStore:
    def __init__(self, project_root: Path | None = None):
        self.project_root = project_root.resolve() if project_root else None

    def _candidate_paths(self) -> list[Path]:
        return list(config_candidates(self.project_root))

    def load(self) -> LoadedConfig:
        payload: dict = {}
        sources: list[Path] = []
        diagnostics: list[ConfigDiagnostic] = []

        for path in self._candidate_paths():
            if not path.exists():
                continue
            try:
                data = _load_config_payload(path)
            except (ValueError, OSError, json.JSONDecodeError) as exc:
                diagnostics.append(
                    _diagnostic(
                        "error",
                        "config.file.parse_error",
                        "$",
                        f"Could not load config file: {exc}",
                        path,
                    )
                )
                continue
            if isinstance(data, dict):
                data = _migrate_config_payload(data, path, diagnostics)
                payload = _deep_merge(payload, data)
                sources.append(path)

        _validate_root_payload(payload, diagnostics)
        codex = payload.get("codex", {}) if isinstance(payload.get("codex", {}), dict) else {}
        method = payload.get("method", {}) if isinstance(payload.get("method", {}), dict) else {}
        ai = payload.get("ai", {}) if isinstance(payload.get("ai", {}), dict) else {}
        ai_router = ai.get("router", {}) if isinstance(ai.get("router", {}), dict) else {}
        ai_services = ai.get("services", {}) if isinstance(ai.get("services", {}), dict) else {}
        ai_prompts = _parse_prompt_templates(
            payload.get("prompts", ai.get("prompts", {})),
            diagnostics=diagnostics,
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
                diagnostics=diagnostics,
                path="ai.request_timeout_seconds",
            ),
            ai_retry_attempts=_parse_int_env(
                "MYTHIC_AI_RETRY_ATTEMPTS",
                ai.get("retry_attempts", AppConfig.ai_retry_attempts),
                minimum=0,
                maximum=10,
                diagnostics=diagnostics,
                path="ai.retry_attempts",
            ),
            ai_daily_cost_cap_usd=_parse_float_env(
                "MYTHIC_DAILY_COST_CAP_USD",
                ai.get("daily_cost_cap_usd", AppConfig.ai_daily_cost_cap_usd),
                minimum=0.0,
                maximum=1_000_000.0,
                diagnostics=diagnostics,
                path="ai.daily_cost_cap_usd",
            ),
            ai_temperature=_parse_float_env(
                "MYTHIC_AI_TEMPERATURE",
                ai.get("temperature", AppConfig.ai_temperature),
                minimum=0.0,
                maximum=2.0,
                diagnostics=diagnostics,
                path="ai.temperature",
            ),
            ai_top_p=_parse_float_env(
                "MYTHIC_AI_TOP_P",
                ai.get("top_p", AppConfig.ai_top_p),
                minimum=0.0,
                maximum=1.0,
                diagnostics=diagnostics,
                path="ai.top_p",
            ),
            ai_router=ai_router if isinstance(ai_router, dict) else {},
            ai_services=_parse_services(ai_services, diagnostics),
            ai_model_routes={},
            ai_routing_rules=[],
            ai_prompts=ai_prompts,
            knowledge_sources=knowledge_sources,
        )
        config.ai_provider = _sanitize_provider_id(
            config.ai_provider,
            path="ai.provider",
            diagnostics=diagnostics,
            fallback=AppConfig.ai_provider,
        )
        config.ai_model = _sanitize_model_id(
            config.ai_model,
            path="ai.model",
            diagnostics=diagnostics,
            fallback=AppConfig.ai_model,
        )
        config.ai_model_routes = _parse_model_routes(
            ai_router,
            config.ai_services,
            context_tokens=config.ai_context_window_tokens,
            output_tokens=config.ai_max_output_tokens,
            diagnostics=diagnostics,
        )
        config.ai_routing_rules = _parse_routing_rules(
            ai_router,
            config.ai_services,
            config.ai_model_routes,
            diagnostics,
        )

        return LoadedConfig(config=config, sources=sources, diagnostics=diagnostics)

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


def _diagnostic(
    severity: str,
    code: str,
    path: str,
    message: str,
    source: Path | str | None = None,
) -> ConfigDiagnostic:
    return ConfigDiagnostic(
        severity=severity,
        code=code,
        path=path,
        message=message,
        source=str(source or ""),
    )


def _migrate_config_payload(
    payload: dict[str, Any],
    path: Path,
    diagnostics: list[ConfigDiagnostic],
) -> dict[str, Any]:
    raw_version = payload.get("schema_version", payload.get("config_schema_version", 1))
    try:
        version = int(raw_version)
    except (TypeError, ValueError):
        diagnostics.append(
            _diagnostic(
                "warning",
                "config.schema.invalid_version",
                "schema_version",
                "Invalid config schema version; assuming version 1.",
                path,
            )
        )
        version = 1
    if version > CURRENT_CONFIG_SCHEMA_VERSION:
        diagnostics.append(
            _diagnostic(
                "error",
                "config.schema.unsupported",
                "schema_version",
                (
                    f"Config schema version {version} is newer than supported "
                    f"version {CURRENT_CONFIG_SCHEMA_VERSION}; using compatible keys only."
                ),
                path,
            )
        )
    elif version < CURRENT_CONFIG_SCHEMA_VERSION:
        diagnostics.append(
            _diagnostic(
                "warning",
                "config.schema.old",
                "schema_version",
                (
                    f"Config schema version {version} was migrated to "
                    f"{CURRENT_CONFIG_SCHEMA_VERSION} in memory."
                ),
                path,
            )
        )
    return payload


def _validate_root_payload(
    payload: dict[str, Any],
    diagnostics: list[ConfigDiagnostic],
) -> None:
    for key in ("codex", "method", "ai", "knowledge", "prompts"):
        if key in payload and not isinstance(payload[key], dict):
            diagnostics.append(
                _diagnostic(
                    "warning",
                    "config.section.not_mapping",
                    key,
                    f"Ignoring {key!r} because it is not a mapping.",
                )
            )


def _is_provider_id(value: str) -> bool:
    if value == "copy-paste":
        return True
    allowed = set(string.ascii_letters + string.digits + "_.-")
    return bool(value) and all(ch in allowed for ch in value)


def _sanitize_provider_id(
    raw: object,
    *,
    path: str,
    diagnostics: list[ConfigDiagnostic],
    fallback: str = "",
    allow_unknown: bool = False,
) -> str:
    value = str(raw or "").strip()
    if not _is_provider_id(value):
        diagnostics.append(
            _diagnostic(
                "warning",
                "config.ai.provider.invalid",
                path,
                f"Invalid provider id {value!r}; using {fallback!r}.",
            )
        )
        return fallback
    if not allow_unknown and value not in KNOWN_AI_PROVIDERS:
        diagnostics.append(
            _diagnostic(
                "warning",
                "config.ai.provider.unknown",
                path,
                f"Unknown provider {value!r}; using {fallback!r}.",
            )
        )
        return fallback
    return value


def _sanitize_model_id(
    raw: object,
    *,
    path: str,
    diagnostics: list[ConfigDiagnostic],
    fallback: str = "",
) -> str:
    value = str(raw or "").strip()
    if not value:
        return fallback
    if any(ch in value for ch in "\r\n\t") or any(ord(ch) < 32 for ch in value):
        diagnostics.append(
            _diagnostic(
                "warning",
                "config.ai.model.invalid",
                path,
                f"Invalid model id {value!r}; using {fallback!r}.",
            )
        )
        return fallback
    if len(value) > 256:
        diagnostics.append(
            _diagnostic(
                "warning",
                "config.ai.model.too_long",
                path,
                "Model id is longer than 256 characters; using fallback.",
            )
        )
        return fallback
    return value


def _parse_services(
    raw: object,
    diagnostics: list[ConfigDiagnostic],
) -> dict[str, Any]:
    if not isinstance(raw, dict):
        if raw not in ({}, None):
            diagnostics.append(
                _diagnostic(
                    "warning",
                    "config.ai.services.not_mapping",
                    "ai.services",
                    "Ignoring ai.services because it is not a mapping.",
                )
            )
        return {}
    services: dict[str, Any] = {}
    for key, value in raw.items():
        provider = _sanitize_provider_id(
            key,
            path=f"ai.services.{key}",
            diagnostics=diagnostics,
            fallback="",
        )
        if not provider or not isinstance(value, dict):
            continue
        payload = {str(k): v for k, v in value.items() if isinstance(k, str)}
        enabled = _coerce_bool(payload.get("enabled", True), True)
        payload["enabled"] = enabled
        if not enabled:
            diagnostics.append(
                _diagnostic(
                    "info",
                    "config.ai.provider.disabled",
                    f"ai.services.{provider}.enabled",
                    f"Provider {provider!r} is disabled and will not be routed.",
                )
            )
        if provider in PROVIDERS_REQUIRING_API_KEYS:
            env_name = PROVIDERS_REQUIRING_API_KEYS[provider]
            payload["api_key_env"] = str(payload.get("api_key_env", env_name) or env_name)
        services[provider] = payload
    return services


def _coerce_bool(raw: object, fallback: bool) -> bool:
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        lowered = raw.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    return fallback


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


def _parse_prompt_templates(
    raw: object,
    *,
    diagnostics: list[ConfigDiagnostic] | None = None,
) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    prompts: dict[str, str] = {}
    for key, value in raw.items():
        if isinstance(key, str) and isinstance(value, str):
            if not _prompt_placeholders_are_valid(value):
                if diagnostics is not None:
                    diagnostics.append(
                        _diagnostic(
                            "warning",
                            "config.prompts.template.invalid",
                            f"prompts.{key}",
                            (
                                f"Ignoring prompt template {key!r} because "
                                "its placeholder braces are invalid."
                            ),
                        )
                    )
                continue
            prompts[key] = value
    return prompts


def _parse_model_routes(
    router: dict[str, Any],
    services: dict[str, Any],
    *,
    context_tokens: int,
    output_tokens: int,
    diagnostics: list[ConfigDiagnostic],
) -> dict[str, list[dict[str, Any]]]:
    raw_types = router.get("model_types", {})
    if not isinstance(raw_types, dict):
        if raw_types not in ({}, None):
            diagnostics.append(
                _diagnostic(
                    "warning",
                    "config.ai.router.model_types.not_mapping",
                    "ai.router.model_types",
                    "Ignoring router model_types because it is not a mapping.",
                )
            )
        return {}
    routes: dict[str, list[dict[str, Any]]] = {}
    for route_name, route_payload in raw_types.items():
        if not isinstance(route_name, str) or not isinstance(route_payload, dict):
            continue
        attempts: list[dict[str, Any]] = []
        service_order = route_payload.get("service_order", [])
        if not isinstance(service_order, list):
            diagnostics.append(
                _diagnostic(
                    "warning",
                    "config.ai.router.service_order.not_list",
                    f"ai.router.model_types.{route_name}.service_order",
                    "Ignoring service_order because it is not a list.",
                )
            )
            service_order = []
        for service_name in service_order:
            if not isinstance(service_name, str):
                continue
            provider = _sanitize_provider_id(
                service_name,
                path=f"ai.router.model_types.{route_name}.service_order",
                diagnostics=diagnostics,
                fallback="",
            )
            if not provider:
                continue
            service_payload = services.get(provider, {})
            if not isinstance(service_payload, dict):
                diagnostics.append(
                    _diagnostic(
                        "warning",
                        "config.ai.router.provider.unknown",
                        f"ai.router.model_types.{route_name}.service_order",
                        f"Provider {provider!r} has no ai.services entry.",
                    )
                )
                continue
            if not _coerce_bool(service_payload.get("enabled", True), True):
                diagnostics.append(
                    _diagnostic(
                        "info",
                        "config.ai.router.provider.disabled",
                        f"ai.router.model_types.{route_name}.service_order",
                        f"Skipping disabled provider {provider!r}.",
                    )
                )
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
                    model_id = _sanitize_model_id(
                        item.get("id", ""),
                        path=f"ai.services.{provider}.model_types.{route_name}",
                        diagnostics=diagnostics,
                        fallback="",
                    )
                    if not model_id:
                        diagnostics.append(
                            _diagnostic(
                                "warning",
                                "config.ai.router.model.no_id",
                                f"ai.services.{provider}.model_types.{route_name}",
                                f"Skipping model without an id for provider {provider!r}.",
                            )
                        )
                        continue
                    item["id"] = model_id
                    item["provider"] = provider
                    item["context_window_tokens"] = _bounded_int(
                        item.get("context_window_tokens", context_tokens),
                        minimum=1000,
                        maximum=context_tokens,
                        fallback=context_tokens,
                        diagnostics=diagnostics,
                        path=(
                            f"ai.services.{provider}.model_types."
                            f"{route_name}.{model_id}.context_window_tokens"
                        ),
                    )
                    item["max_output_tokens"] = _bounded_int(
                        item.get("max_output_tokens", output_tokens),
                        minimum=128,
                        maximum=output_tokens,
                        fallback=output_tokens,
                        diagnostics=diagnostics,
                        path=(
                            f"ai.services.{provider}.model_types."
                            f"{route_name}.{model_id}.max_output_tokens"
                        ),
                    )
                    attempts.append(item)
                elif isinstance(model, str):
                    model_id = _sanitize_model_id(
                        model,
                        path=f"ai.services.{provider}.model_types.{route_name}",
                        diagnostics=diagnostics,
                        fallback="",
                    )
                    if model_id:
                        attempts.append(
                            {
                                "provider": provider,
                                "id": model_id,
                                "context_window_tokens": context_tokens,
                                "max_output_tokens": output_tokens,
                            }
                        )
        routes[route_name] = attempts
    return routes


def _parse_routing_rules(
    router: dict[str, Any],
    services: dict[str, Any],
    model_routes: dict[str, list[dict[str, Any]]],
    diagnostics: list[ConfigDiagnostic],
) -> list[dict[str, Any]]:
    raw = router.get("routing_rules", [])
    if not isinstance(raw, list):
        if raw not in ({}, None):
            diagnostics.append(
                _diagnostic(
                    "warning",
                    "config.ai.router.routing_rules.not_list",
                    "ai.router.routing_rules",
                    "Ignoring routing_rules because it is not a list.",
                )
            )
        return []
    rules: list[dict[str, Any]] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            diagnostics.append(
                _diagnostic(
                    "warning",
                    "config.ai.router.rule.invalid",
                    f"ai.router.routing_rules[{index}]",
                    "Skipping routing rule because it is not a mapping.",
                )
            )
            continue
        rule = {str(key): value for key, value in item.items() if isinstance(key, str)}
        provider = _sanitize_provider_id(
            rule.get("provider", "copy-paste"),
            path=f"ai.router.routing_rules[{index}].provider",
            diagnostics=diagnostics,
            fallback="copy-paste",
        )
        service_payload = services.get(provider)
        if isinstance(service_payload, dict) and not _coerce_bool(
            service_payload.get("enabled", True),
            True,
        ):
            diagnostics.append(
                _diagnostic(
                    "warning",
                    "config.ai.router.rule.provider_disabled",
                    f"ai.router.routing_rules[{index}].provider",
                    f"Provider {provider!r} is disabled; using copy-paste.",
                )
            )
            provider = "copy-paste"
        raw_model = "manual" if provider == "copy-paste" else rule.get("model", "")
        model = _sanitize_model_id(
            raw_model,
            path=f"ai.router.routing_rules[{index}].model",
            diagnostics=diagnostics,
            fallback="manual" if provider == "copy-paste" else "",
        )
        task_type = str(rule.get("task_type", "*") or "*")
        known_models = {
            str(model_payload.get("id", ""))
            for model_payload in model_routes.get(task_type, [])
            if isinstance(model_payload, dict)
        }
        if model and known_models and model not in known_models:
            diagnostics.append(
                _diagnostic(
                    "warning",
                    "config.ai.router.rule.model_unlisted",
                    f"ai.router.routing_rules[{index}].model",
                    f"Model {model!r} is not listed for task type {task_type!r}.",
                )
            )
        rule["provider"] = provider
        rule["model"] = model
        raw_fallbacks = rule.get("fallbacks", [])
        if not isinstance(raw_fallbacks, list):
            raw_fallbacks = []
        fallbacks: list[str] = []
        for fallback_index, fallback in enumerate(raw_fallbacks):
            fallback_provider, fallback_model = _split_provider_model(str(fallback))
            fallback_provider = _sanitize_provider_id(
                fallback_provider,
                path=(
                    f"ai.router.routing_rules[{index}].fallbacks"
                    f"[{fallback_index}]"
                ),
                diagnostics=diagnostics,
                fallback="",
            )
            if not fallback_provider:
                continue
            fallback_service = services.get(fallback_provider)
            if isinstance(fallback_service, dict) and not _coerce_bool(
                fallback_service.get("enabled", True),
                True,
            ):
                diagnostics.append(
                    _diagnostic(
                        "warning",
                        "config.ai.router.rule.fallback_disabled",
                        (
                            f"ai.router.routing_rules[{index}].fallbacks"
                            f"[{fallback_index}]"
                        ),
                        f"Skipping disabled fallback provider {fallback_provider!r}.",
                    )
                )
                continue
            if fallback_model:
                fallback_model = _sanitize_model_id(
                    fallback_model,
                    path=(
                        f"ai.router.routing_rules[{index}].fallbacks"
                        f"[{fallback_index}]"
                    ),
                    diagnostics=diagnostics,
                    fallback="",
                )
                if not fallback_model:
                    continue
                fallbacks.append(f"{fallback_provider}|{fallback_model}")
            else:
                fallbacks.append(fallback_provider)
        if provider != "copy-paste" and "copy-paste" not in {
            _split_provider_model(item)[0] for item in fallbacks
        }:
            fallbacks.append("copy-paste")
        rule["fallbacks"] = fallbacks
        rules.append(rule)
    return rules


def _split_provider_model(raw: str) -> tuple[str, str]:
    if "|" not in raw:
        return raw, ""
    provider, model = raw.split("|", 1)
    return provider.strip(), model.strip()


def _prompt_placeholders_are_valid(template: str) -> bool:
    formatter = string.Formatter()
    try:
        for _literal, field_name, _format_spec, _conversion in formatter.parse(template):
            if field_name is None:
                continue
            name = field_name.split(".", 1)[0].split("[", 1)[0]
            if name and not name.isidentifier():
                return False
    except ValueError:
        return False
    return True


def _bounded_int(
    raw: object,
    *,
    minimum: int,
    maximum: int,
    fallback: int,
    diagnostics: list[ConfigDiagnostic] | None = None,
    path: str = "",
) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        if diagnostics is not None:
            diagnostics.append(
                _diagnostic(
                    "warning",
                    "config.value.invalid_int",
                    path,
                    f"Invalid integer value {raw!r}; using {fallback}.",
                )
            )
        value = fallback
    bounded = max(minimum, min(maximum, int(value)))
    if bounded != value and diagnostics is not None:
        diagnostics.append(
            _diagnostic(
                "warning",
                "config.value.clamped",
                path,
                f"Value {value!r} was clamped to {bounded}.",
            )
        )
    return bounded


def _parse_int_env(
    name: str,
    fallback: int,
    minimum: int,
    maximum: int,
    *,
    diagnostics: list[ConfigDiagnostic] | None = None,
    path: str = "",
) -> int:
    raw = os.environ.get(name)
    return _bounded_int(
        fallback if raw is None else raw,
        minimum=minimum,
        maximum=maximum,
        fallback=int(fallback),
        diagnostics=diagnostics,
        path=path or name,
    )


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


def _parse_float_env(
    name: str,
    fallback: object,
    minimum: float,
    maximum: float,
    *,
    diagnostics: list[ConfigDiagnostic] | None = None,
    path: str = "",
) -> float:
    raw = os.environ.get(name)
    value = fallback
    if raw is not None:
        value = raw
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        if diagnostics is not None:
            diagnostics.append(
                _diagnostic(
                    "warning",
                    "config.value.invalid_float",
                    path or name,
                    f"Invalid float value {value!r}; using {minimum}.",
                )
            )
        parsed = float(minimum)
    bounded = max(minimum, min(maximum, parsed))
    if bounded != parsed and diagnostics is not None:
        diagnostics.append(
            _diagnostic(
                "warning",
                "config.value.clamped",
                path or name,
                f"Value {parsed!r} was clamped to {bounded}.",
            )
        )
    return bounded


def _parse_str_env(name: str, fallback: str) -> str:
    raw = os.environ.get(name)
    if raw is not None and raw.strip():
        return raw.strip()
    return str(fallback).strip()

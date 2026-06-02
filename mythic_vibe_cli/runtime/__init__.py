"""Runtime primitives for Mythic Vibe CLI workflow execution.

Currently exposes:

- ``file_mutation_queue`` — per-path serialization for mutation operations.
- ``output_guard`` — stdout cleanliness for protocol-output modes.
- ``event_bus`` — synchronous publish/subscribe coordination layer.
- ``timings`` — lightweight elapsed-time instrumentation (env-gated).
- ``slash_commands`` — typed catalog of slash commands (no dispatcher).
- ``source_info`` — provenance type for contributed artifacts.
- ``exec`` — subprocess execution primitive with timeout and cancel-event.
"""

from .command_catalog import (
    ARGPARSE_ONLY_NAMES,
    CommandCatalogEntry,
    CommandCatalogValidation,
    SLASH_LOCAL_NAMES,
    build_command_catalog,
    builtin_slash_by_name,
    iter_builtin_slash_commands,
    validate_command_catalog,
)
from .event_bus import EventBus, EventBusController, create_event_bus
from .event_log import (
    DEFAULT_EVENT_LOG_FILENAME,
    DEFAULT_MAX_ENTRIES,
    EVENT_LOG_LIMIT_ENV,
    EventLogEntry,
    append_event,
    event_log_path_for,
    read_recent,
    resolve_max_entries,
)
from .exec import ExecResult, exec_command, spawn_process
from .file_mutation_queue import file_mutation_queue, with_file_mutation_queue
from .output_guard import (
    flush_raw_stdout,
    is_stdout_taken_over,
    json_output_guard,
    restore_stdout,
    take_over_stdout,
    write_raw_stdout,
)
from .slash_commands import (
    BUILTIN_SLASH_COMMANDS,
    BuiltinSlashCommand,
    SlashCommandInfo,
    SlashCommandSource,
)
from .source_info import (
    SourceInfo,
    SourceOrigin,
    SourceScope,
    synthetic_source_info,
)
from .timings import print_timings, record, reset_timings

__all__ = [
    "file_mutation_queue",
    "with_file_mutation_queue",
    "take_over_stdout",
    "restore_stdout",
    "is_stdout_taken_over",
    "write_raw_stdout",
    "flush_raw_stdout",
    "json_output_guard",
    "create_event_bus",
    "EventBus",
    "EventBusController",
    "EventLogEntry",
    "append_event",
    "event_log_path_for",
    "read_recent",
    "DEFAULT_EVENT_LOG_FILENAME",
    "DEFAULT_MAX_ENTRIES",
    "EVENT_LOG_LIMIT_ENV",
    "resolve_max_entries",
    "reset_timings",
    "record",
    "print_timings",
    "BUILTIN_SLASH_COMMANDS",
    "BuiltinSlashCommand",
    "SlashCommandInfo",
    "SlashCommandSource",
    "SourceInfo",
    "SourceOrigin",
    "SourceScope",
    "synthetic_source_info",
    "exec_command",
    "spawn_process",
    "ExecResult",
    "ARGPARSE_ONLY_NAMES",
    "CommandCatalogEntry",
    "CommandCatalogValidation",
    "SLASH_LOCAL_NAMES",
    "build_command_catalog",
    "builtin_slash_by_name",
    "iter_builtin_slash_commands",
    "validate_command_catalog",
]

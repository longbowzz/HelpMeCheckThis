"""Provider-neutral metadata for locally discoverable review CLIs.

This module performs no discovery or subprocess calls at import time.
"""
from __future__ import annotations

import json
import shutil
from typing import Any


DEFAULT_AGENTS: list[dict[str, Any]] = [
    {
        "id": "claude",
        "enabled": False,
        "input_mode": "argv",
        "probe_input_mode": "argv",
        "argv": ["claude", "--print", "--output-format", "json", "{prompt}"],
        "version_args": ["--version"],
        "probe_argv": ["claude", "--print", "--output-format", "text", "{prompt}"],
        "configured_model": None,
        "model_source": "unknown",
        "supported": True,
    },
    {
        "id": "codex",
        "enabled": False,
        "input_mode": "argv",
        "probe_input_mode": "argv",
        "argv": ["codex", "exec", "--ephemeral", "--sandbox", "workspace-write", "--add-dir", "{task_dir}", "{prompt}"],
        "version_args": ["--version"],
        "probe_argv": ["codex", "exec", "--ephemeral", "{prompt}"],
        "configured_model": None,
        "model_source": "unknown",
        "supported": True,
    },
    {
        "id": "pi",
        "enabled": False,
        "input_mode": "argv",
        "probe_input_mode": "argv",
        "argv": ["pi", "--print", "--no-session", "--no-extensions", "--no-mcp", "--no-skills", "--no-prompt-templates", "{prompt}"],
        "version_args": ["--version"],
        "probe_argv": ["pi", "--print", "--no-session", "--no-tools", "--no-extensions", "--no-mcp", "--no-skills", "{prompt}"],
        "configured_model": None,
        "model_source": "unknown",
        "supported": True,
    },
    {
        "id": "dsh",
        "enabled": False,
        "input_mode": "argv",
        "probe_input_mode": "argv",
        "argv": ["dsh", "--profile", "headless", "{prompt}"],
        "version_args": ["--version"],
        "probe_argv": ["dsh", "--profile", "headless", "{prompt}"],
        "configured_model": None,
        "model_source": "unknown",
        "supported": True,
    },
]


def discover_defaults() -> list[dict[str, Any]]:
    """Return default entries annotated with executable presence, without invoking them."""
    entries = []
    for adapter in DEFAULT_AGENTS:
        row = dict(adapter)
        row["present"] = shutil.which(row["argv"][0]) is not None
        entries.append(row)
    return entries


def parse_output(adapter: str | dict[str, Any], text: str) -> dict[str, Any]:
    """Normalize a direct result JSON object or verified CLI JSON result envelope.

    Claude Code's --output-format json envelope exposes the final text in `result`.
    Codex JSONL is event-oriented, so it is deliberately not guessed here; callers
    should pass a final direct JSON object if they have extracted it themselves.
    """
    adapter_id = adapter if isinstance(adapter, str) else adapter.get("id", "")
    try:
        value = json.loads(text)
    except (TypeError, json.JSONDecodeError):
        return {"ok": False, "result": None, "error": "output is not valid JSON"}

    if isinstance(value, dict) and adapter_id == "claude" and isinstance(value.get("result"), str):
        try:
            value = json.loads(value["result"])
        except json.JSONDecodeError:
            return {"ok": False, "result": None, "error": "Claude result text is not valid JSON"}

    if isinstance(value, dict):
        return {"ok": True, "result": value, "error": None}
    return {"ok": False, "result": None, "error": "result must be a JSON object"}

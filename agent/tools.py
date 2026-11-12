"""Read-only tools the mentor agent can call in debugging mode.

Every tool returns plain text. Errors are returned as text starting with
"ERROR:" so the model can react to them; they never stop the agent.
"""

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

MAX_OUTPUT_CHARS = 8000
MAX_LIST_ENTRIES = 300
TEST_TIMEOUT_SECONDS = 180
SKIPPED_DIRS = {".git", "target", "node_modules", ".idea", ".venv", "__pycache__"}
TEST_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_]+$")


class ToolError(Exception):
    """A tool could not do what the model asked (bad path, unknown test, ...)."""


@dataclass
class ToolContext:
    repo_root: Path      # student repository, the only place file tools may read
    log_file: Path | None
    tests_dir: Path      # protected tests of this ticket, e.g. tests/tickets/ticket_1
    base_url: str        # where the running service is, for run_test


def truncate(text: str, limit: int = MAX_OUTPUT_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n... [truncated, {len(text) - limit} more characters]"


def is_blocked(relative: Path) -> bool:
    """Hide git internals and env files (they may contain secrets)."""
    return any(part == ".git" or part.startswith(".env") for part in relative.parts)


def resolve_in_repo(repo_root: Path, path: str) -> Path:
    """Turn a model-supplied path into a real path inside the repository."""
    root = repo_root.resolve()
    candidate = Path(path)
    if candidate.is_absolute():
        raise ToolError("use a path relative to the repository root")
    resolved = (root / candidate).resolve()
    if not resolved.is_relative_to(root):
        raise ToolError("path is outside the repository")
    if is_blocked(resolved.relative_to(root)):
        raise ToolError("this path is not available")
    return resolved


def list_files(ctx: ToolContext, path: str = ".") -> str:
    directory = resolve_in_repo(ctx.repo_root, path)
    if not directory.is_dir():
        raise ToolError(f"not a directory: {path}")
    root = ctx.repo_root.resolve()
    entries: list[str] = []
    for item in sorted(directory.rglob("*")):
        relative = item.relative_to(root)
        if any(part in SKIPPED_DIRS for part in relative.parts) or is_blocked(relative):
            continue
        if item.is_file():
            entries.append(relative.as_posix())
        if len(entries) >= MAX_LIST_ENTRIES:
            entries.append(f"... [stopped after {MAX_LIST_ENTRIES} files]")
            break
    return "\n".join(entries) if entries else "(no files)"


def read_file(ctx: ToolContext, path: str) -> str:
    file = resolve_in_repo(ctx.repo_root, path)
    if not file.is_file():
        raise ToolError(f"not a file: {path}")
    text = file.read_text(encoding="utf-8", errors="replace")
    numbered = [f"{number:4}| {line}" for number, line in enumerate(text.splitlines(), start=1)]
    return truncate("\n".join(numbered))


def get_logs(ctx: ToolContext, contains: str | None = None, max_lines: int = 100) -> str:
    if ctx.log_file is None or not ctx.log_file.is_file():
        raise ToolError("no service log is available for this run")
    max_lines = max(1, min(int(max_lines), 300))
    lines = ctx.log_file.read_text(encoding="utf-8", errors="replace").splitlines()
    if contains:
        lines = [line for line in lines if contains.lower() in line.lower()]
    if not lines:
        return "(no matching log lines)"
    return truncate("\n".join(lines[-max_lines:]))


def run_test(ctx: ToolContext, test_name: str | None = None) -> str:
    """Run the protected tests of the ticket again (all, or one by name)."""
    command = [sys.executable, "-m", "pytest", str(ctx.tests_dir), "-q", "--tb=short", "-p", "no:cacheprovider"]
    if test_name:
        if not TEST_NAME_PATTERN.match(test_name):
            raise ToolError("test_name must be a plain test function name")
        command += ["-k", test_name]
    env = {**_safe_env(), "CODEMENTOR_BASE_URL": ctx.base_url}
    try:
        completed = subprocess.run(
            command, capture_output=True, text=True, timeout=TEST_TIMEOUT_SECONDS, env=env
        )
    except subprocess.TimeoutExpired:
        raise ToolError(f"tests did not finish in {TEST_TIMEOUT_SECONDS}s")
    return truncate(completed.stdout + completed.stderr)


def _safe_env() -> dict[str, str]:
    """Environment for the test process without the API key."""
    return {name: value for name, value in os.environ.items() if name != "OPENROUTER_API_KEY"}


TOOL_FUNCTIONS = {
    "list_files": list_files,
    "read_file": read_file,
    "get_logs": get_logs,
    "run_test": run_test,
}

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files under a directory of the student repository (recursive).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory relative to the repository root, default '.'"}
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a text file of the student repository. Lines are numbered.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "File path relative to the repository root"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_logs",
            "description": "Read the service log of this run: the last lines, optionally only lines containing a text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "contains": {"type": "string", "description": "Only lines containing this text (case-insensitive)"},
                    "max_lines": {"type": "integer", "description": "How many last lines to return (1-300, default 100)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_test",
            "description": "Run the ticket tests again against the running service. Optionally only one test by function name.",
            "parameters": {
                "type": "object",
                "properties": {"test_name": {"type": "string", "description": "Test function name, e.g. test_empty_items_returns_400"}},
            },
        },
    },
]


def execute_tool(ctx: ToolContext, name: str, arguments_json: str) -> str:
    """Run one tool call from the model. Always returns text, never raises."""
    function = TOOL_FUNCTIONS.get(name)
    if function is None:
        return f"ERROR: unknown tool '{name}'"
    try:
        arguments = json.loads(arguments_json or "{}")
        if not isinstance(arguments, dict):
            raise ValueError("arguments must be a JSON object")
        return function(ctx, **arguments)
    except ToolError as error:
        return f"ERROR: {error}"
    except (ValueError, TypeError) as error:
        return f"ERROR: bad arguments for {name}: {error}"
    except OSError as error:
        return f"ERROR: {name} failed: {error.strerror or error}"

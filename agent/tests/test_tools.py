from pathlib import Path

import pytest

from agent.tools import MAX_OUTPUT_CHARS, ToolContext, execute_tool, truncate


def test_read_file_returns_numbered_lines(ctx: ToolContext) -> None:
    output = execute_tool(ctx, "read_file", '{"path": "src/OrderService.java"}')

    assert "   1| class OrderService {" in output
    assert "   2|     int total;" in output


@pytest.mark.parametrize("path", ["../outside.txt", "src/../../outside.txt"])
def test_read_file_cannot_leave_the_repository(ctx: ToolContext, path: str) -> None:
    (ctx.repo_root.parent / "outside.txt").write_text("secret", encoding="utf-8")

    output = execute_tool(ctx, "read_file", f'{{"path": "{path}"}}')

    assert output == "ERROR: path is outside the repository"


def test_read_file_rejects_absolute_paths(ctx: ToolContext) -> None:
    absolute = (ctx.repo_root / "src" / "OrderService.java").resolve().as_posix()

    output = execute_tool(ctx, "read_file", f'{{"path": "{absolute}"}}')

    assert output.startswith("ERROR: use a path relative")


@pytest.mark.parametrize("path", [".env", ".git/config"])
def test_read_file_hides_env_and_git(ctx: ToolContext, path: str) -> None:
    output = execute_tool(ctx, "read_file", f'{{"path": "{path}"}}')

    assert output == "ERROR: this path is not available"
    assert "secret" not in output


def test_list_files_skips_hidden_and_build_dirs(ctx: ToolContext) -> None:
    output = execute_tool(ctx, "list_files", "{}")

    assert output.splitlines() == ["src/OrderService.java"]


def test_get_logs_filters_lines(ctx: ToolContext) -> None:
    output = execute_tool(ctx, "get_logs", '{"contains": "exception"}')

    assert output == "ERROR java.lang.IndexOutOfBoundsException"


def test_get_logs_without_log_file(ctx: ToolContext) -> None:
    ctx.log_file = None

    assert execute_tool(ctx, "get_logs", "{}").startswith("ERROR: no service log")


def test_unknown_tool_and_bad_json_do_not_raise(ctx: ToolContext) -> None:
    assert execute_tool(ctx, "post_comment", "{}") == "ERROR: unknown tool 'post_comment'"
    assert execute_tool(ctx, "read_file", "{not json").startswith("ERROR: bad arguments")
    assert execute_tool(ctx, "read_file", '{"wrong": 1}').startswith("ERROR: bad arguments")


def test_run_test_rejects_strange_test_names(ctx: ToolContext) -> None:
    output = execute_tool(ctx, "run_test", '{"test_name": "x or y"}')

    assert output == "ERROR: test_name must be a plain test function name"


def test_run_test_passes_base_url_but_not_the_api_key(ctx: ToolContext, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "must-not-leak")
    ctx.tests_dir.mkdir()
    (ctx.tests_dir / "test_env.py").write_text(
        "import os\n"
        "def test_env():\n"
        "    assert os.environ['CODEMENTOR_BASE_URL'] == 'http://localhost:1'\n"
        "    assert 'OPENROUTER_API_KEY' not in os.environ\n",
        encoding="utf-8",
    )

    output = execute_tool(ctx, "run_test", '{"test_name": "test_env"}')

    assert "1 passed" in output


def test_truncate_long_output() -> None:
    text = "x" * (MAX_OUTPUT_CHARS + 50)

    assert truncate(text).endswith("[truncated, 50 more characters]")

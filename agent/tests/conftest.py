from pathlib import Path

import pytest

from agent.tools import ToolContext


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A small fake student repository."""
    root = tmp_path / "student"
    (root / "src").mkdir(parents=True)
    (root / "src" / "OrderService.java").write_text("class OrderService {\n    int total;\n}\n", encoding="utf-8")
    (root / ".env").write_text("OPENROUTER_API_KEY=secret\n", encoding="utf-8")
    (root / ".git").mkdir()
    (root / ".git" / "config").write_text("[core]\n", encoding="utf-8")
    (root / "target").mkdir()
    (root / "target" / "Built.class").write_text("binary", encoding="utf-8")
    return root


@pytest.fixture
def ctx(repo: Path, tmp_path: Path) -> ToolContext:
    log_file = tmp_path / "service.log"
    log_file.write_text("INFO started\nERROR java.lang.IndexOutOfBoundsException\nINFO request\n", encoding="utf-8")
    return ToolContext(repo_root=repo, log_file=log_file, tests_dir=tmp_path / "tests", base_url="http://localhost:1")


@pytest.fixture
def prompts_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Stand-in prompts: tests of main.py must not depend on the prompt wording."""
    import agent.main as main_module

    directory = tmp_path / "prompts"
    directory.mkdir()
    (directory / "debugging.md").write_text("debugging prompt", encoding="utf-8")
    (directory / "regenerate_hint_1.md").write_text("regenerate prompt", encoding="utf-8")
    monkeypatch.setattr(main_module, "PROMPTS_DIR", directory)
    return directory


@pytest.fixture
def make_args(repo: Path, tmp_path: Path, prompts_dir: Path, monkeypatch: pytest.MonkeyPatch):
    """Build agent.main arguments for one run on the fake repository (not in CI unless a test says so)."""
    from agent.main import parse_args

    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    test_output = tmp_path / "test-output.txt"
    test_output.write_text("FAILED test_empty_items_returns_400 - assert 500 == 400\n", encoding="utf-8")

    def make(*extra: str):
        return parse_args([
            "--ticket", "1",
            "--repo", str(repo),
            "--test-output", str(test_output),
            "--out", str(tmp_path / "comment.md"),
            "--trace", str(tmp_path / "trace.json"),
            "--tickets-dir", str(tmp_path),
            *extra,
        ])

    return make

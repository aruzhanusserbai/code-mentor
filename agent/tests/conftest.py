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

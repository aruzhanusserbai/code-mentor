"""In CI only the hint of the selected level may leave the agent process (DECISIONS.md, D18).

Every part of the answer carries a sentinel string. After a run we collect
everything the student could read: stdout and stderr (the job log, ::error
annotations), the log records, comment.md and the trace (a workflow artifact).
Only the sentinel of the published hint may appear there.
"""

import json
from pathlib import Path

import pytest

from agent.hints import FALLBACK_HINT_1
from agent.main import run
from agent.tests.fake_llm import FakeLLM, text_reply, tool_reply

SENTINELS = {
    "diagnosis": "SENTINEL-DIAGNOSIS",
    "hint_1": "SENTINEL-HINT-1",
    "hint_2": "SENTINEL-HINT-2",
    "hint_3": "SENTINEL-HINT-3",
}
ANSWER = {
    "diagnosis": "SENTINEL-DIAGNOSIS: the request is not validated, so the service fails with 500.",
    "hint_1": "SENTINEL-HINT-1 Compare the expected and the actual status code.",
    "hint_2": "SENTINEL-HINT-2 Look at the request class of the orders endpoint.",
    "hint_3": "SENTINEL-HINT-3 Think about which inputs the validation should reject.",
}


def submit(arguments: dict) -> tuple[str, str]:
    return ("submit_answer", json.dumps(arguments))


@pytest.fixture
def in_ci(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_ACTIONS", "true")


def public_output(tmp_path: Path, capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture) -> str:
    captured = capsys.readouterr()
    parts = [captured.out, captured.err, caplog.text]
    for name in ("comment.md", "trace.json"):
        if (tmp_path / name).exists():
            parts.append((tmp_path / name).read_text(encoding="utf-8"))
    return "\n".join(parts)


@pytest.mark.parametrize("level", [1, 2, 3])
def test_only_the_hint_of_the_level_is_published(
    level: int, make_args, in_ci, tmp_path: Path, capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level("DEBUG")
    llm = FakeLLM([tool_reply(("get_logs", "{}")), tool_reply(submit(ANSWER))])

    code = run(make_args("--level", str(level)), llm)

    assert code == 0
    published = f"hint_{level}"
    assert SENTINELS[published] in (tmp_path / "comment.md").read_text(encoding="utf-8")
    output = public_output(tmp_path, capsys, caplog)
    for part, sentinel in SENTINELS.items():
        if part != published:
            assert sentinel not in output, f"{part} leaked"


def test_rejected_level_1_hints_are_not_published(
    make_args, in_ci, tmp_path: Path, capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level("DEBUG")
    leaky = {
        **ANSWER,
        "diagnosis": "SENTINEL-DIAGNOSIS: OrderService reads the first item.",
        "hint_1": "SENTINEL-HINT-1 OrderService fails.",
    }
    llm = FakeLLM([tool_reply(submit(leaky)), text_reply("SENTINEL-REGENERATED OrderService again.")])

    code = run(make_args("--level", "1"), llm)

    assert code == 0
    assert FALLBACK_HINT_1 in (tmp_path / "comment.md").read_text(encoding="utf-8")
    output = public_output(tmp_path, capsys, caplog)
    for sentinel in [*SENTINELS.values(), "SENTINEL-REGENERATED", "OrderService"]:
        assert sentinel not in output


def test_invalid_answers_are_not_published(
    make_args, in_ci, tmp_path: Path, capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level("DEBUG")
    broken = {**ANSWER, "hint_3": ""}
    llm = FakeLLM([tool_reply(submit(broken)), tool_reply(submit(broken))])

    code = run(make_args(), llm)

    assert code == 1
    output = public_output(tmp_path, capsys, caplog)
    assert "::error title=CodeMentor agent::" in output
    for sentinel in SENTINELS.values():
        assert sentinel not in output
    assert not (tmp_path / "comment.md").exists()


def test_text_answers_are_not_published(
    make_args, in_ci, tmp_path: Path, capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level("DEBUG")
    llm = FakeLLM([text_reply(ANSWER["diagnosis"]), text_reply(ANSWER["hint_3"])])

    code = run(make_args(), llm)

    assert code == 1
    output = public_output(tmp_path, capsys, caplog)
    for sentinel in SENTINELS.values():
        assert sentinel not in output


def test_full_answer_file_is_refused_in_ci(
    make_args, in_ci, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    full = tmp_path / "full-answer.json"
    llm = FakeLLM([])

    code = run(make_args("--full-answer-out", str(full)), llm)

    assert code == 2
    assert not full.exists()
    assert not (tmp_path / "comment.md").exists()
    assert llm.requests == []  # refused before any model request
    assert "--full-answer-out" in capsys.readouterr().out  # shown as an ::error annotation

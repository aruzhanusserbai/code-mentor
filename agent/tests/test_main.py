import json
from pathlib import Path

import pytest

import agent.main as main_module
from agent.llm import LLMReply
from agent.main import parse_args, run
from agent.tests.fake_llm import FakeLLM, text_reply, tool_reply

ANSWER = {
    "diagnosis": "OrderService reads the first item of an empty list.",
    "hint_1": "The tests expect 400 but get 500. Where should invalid input stop?",
    "hint_2": "Look at the request class of the orders endpoint.",
    "hint_3": "Think about which inputs the validation should reject.",
}


def submit(arguments: dict = ANSWER) -> tuple[str, str]:
    return ("submit_answer", json.dumps(arguments))


class FailingLLM:
    def chat(self, messages: list[dict], tools: list[dict] | None) -> LLMReply:
        raise RuntimeError("service unavailable")


def test_missing_model_is_reported_as_annotation_without_the_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(main_module, "PLATFORM_ROOT", tmp_path)  # no local .env
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test-must-not-appear")
    monkeypatch.delenv("CODEMENTOR_MODEL", raising=False)

    code = main_module.main(
        ["--ticket", "1", "--repo", str(tmp_path), "--test-output", "x.txt", "--out", str(tmp_path / "c.md")]
    )

    captured = capsys.readouterr()
    assert code == 2
    assert "::error title=CodeMentor agent::missing environment variables: CODEMENTOR_MODEL" in captured.out
    assert "sk-test-must-not-appear" not in captured.out + captured.err
    assert not (tmp_path / "c.md").exists()


def test_comment_has_the_selected_level(make_args, tmp_path: Path) -> None:
    llm = FakeLLM([tool_reply(submit())])

    code = run(make_args("--level", "3"), llm)

    comment = (tmp_path / "comment.md").read_text(encoding="utf-8")
    assert code == 0
    assert comment.splitlines()[0] == "<!-- codementor:ticket=1;mode=debugging;level=3 -->"
    assert ANSWER["hint_3"] in comment


def test_level_defaults_to_1(make_args) -> None:
    assert make_args().level == 1


@pytest.mark.parametrize("level", ["0", "4"])
def test_level_must_be_1_to_3(level: str) -> None:
    with pytest.raises(SystemExit):
        parse_args(["--ticket", "1", "--repo", ".", "--test-output", "x", "--out", "c.md", "--level", level])


def test_first_message_asks_for_submit_answer(make_args) -> None:
    llm = FakeLLM([tool_reply(submit())])

    run(make_args("--level", "2"), llm)

    first_message = llm.requests[0]["messages"][1]["content"]
    assert "submit_answer" in first_message
    assert "level" not in first_message.splitlines()[0]  # the model writes all levels, code picks one
    assert llm.requests[0]["messages"][0]["content"] == "debugging prompt"


def test_trace_records_the_run_without_the_answer(make_args, tmp_path: Path) -> None:
    leaky = {**ANSWER, "hint_1": "OrderService fails. Look there."}
    llm = FakeLLM([
        tool_reply(("get_logs", "{}")),
        tool_reply(submit(leaky)),
        text_reply("The tests expect 400 but get 500. Follow the request."),
    ])

    run(make_args("--level", "1"), llm)

    trace = json.loads((tmp_path / "trace.json").read_text(encoding="utf-8"))
    assert trace == {
        "level": 1,
        "requests": 3,  # two in the loop and one regeneration
        "hit_limit": False,
        "error": None,
        "hint_status": "regenerated",
        "hint_check": ["leaks_identifiers"],
        "tool_calls": [{"tool": "get_logs", "arguments": "{}", "result_chars": trace["tool_calls"][0]["result_chars"]}],
    }


def test_no_valid_answer_fails_with_the_reason(make_args, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    llm = FakeLLM([text_reply("Hint."), text_reply("Hint again.")])

    code = run(make_args(), llm)

    assert code == 1
    assert "::error title=CodeMentor agent::the model did not submit a valid answer (text_instead_of_submit)" in capsys.readouterr().out
    assert not (tmp_path / "comment.md").exists()
    trace = json.loads((tmp_path / "trace.json").read_text(encoding="utf-8"))
    assert trace["error"] == "text_instead_of_submit"
    assert trace["hint_status"] is None


def test_model_errors_fail_the_run(make_args, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_ACTIONS", "true")

    code = run(make_args(), FailingLLM())

    assert code == 1
    assert "agent failed: RuntimeError: service unavailable" in capsys.readouterr().out
    assert not (tmp_path / "comment.md").exists()


def test_full_answer_is_saved_for_local_eval_runs(make_args, tmp_path: Path) -> None:
    full = tmp_path / "full-answer.json"
    llm = FakeLLM([tool_reply(submit())])

    code = run(make_args("--level", "2", "--full-answer-out", str(full)), llm)

    assert code == 0
    saved = json.loads(full.read_text(encoding="utf-8"))
    assert saved == {"answer": ANSWER, "level": 2, "published_hint": ANSWER["hint_2"], "hint_status": "ok"}


def test_regeneration_uses_the_prompt_of_the_selected_level(make_args) -> None:
    leaky = {**ANSWER, "hint_2": "OrderService should check the list."}
    llm = FakeLLM([tool_reply(submit(leaky)), text_reply("The request fails in OrderService.")])

    code = run(make_args("--level", "2"), llm)

    assert code == 0
    assert llm.requests[1]["messages"][0]["content"] == "regenerate prompt 2"

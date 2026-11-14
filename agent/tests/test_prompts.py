"""The real prompt files: placeholders, the sentence limits and the submit_answer contract."""

from pathlib import Path

import pytest

import agent.main as main_module
from agent.answer import ANSWER_FIELDS
from agent.checks import MAX_SENTENCES
from agent.main import PROMPTS_DIR, load_prompt

REGENERATE_PROMPTS = {level: f"regenerate_hint_{level}.md" for level in (1, 2, 3)}
PROMPTS = ["debugging.md", *REGENERATE_PROMPTS.values()]
# Which limits each prompt states: the debugging prompt has all levels.
LIMITS = [("debugging.md", level) for level in (1, 2, 3)] + [(name, level) for level, name in REGENERATE_PROMPTS.items()]


def flat(text: str) -> str:
    return " ".join(text.split())  # ignore line breaks


@pytest.mark.parametrize(("name", "level"), LIMITS)
def test_sentence_limit_comes_from_the_code(name: str, level: int) -> None:
    raw = (PROMPTS_DIR / name).read_text(encoding="utf-8")

    assert f"{{max_sentences_level_{level}}}" in raw  # the number itself is not written in the file
    assert f"at most {MAX_SENTENCES[level]} sentences" in flat(load_prompt(name)).lower()


@pytest.mark.parametrize(("name", "level"), LIMITS)
def test_changing_the_constant_changes_the_prompt(name: str, level: int, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(MAX_SENTENCES, level, 9)

    assert "at most 9 sentences" in flat(load_prompt(name)).lower()


@pytest.mark.parametrize("name", PROMPTS)
def test_no_placeholder_is_left(name: str) -> None:
    assert "{" not in load_prompt(name)


def test_unknown_placeholder_is_an_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "broken.md").write_text("Write at most {max_sentence_level_1} sentences.", encoding="utf-8")
    monkeypatch.setattr(main_module, "PROMPTS_DIR", tmp_path)

    with pytest.raises(ValueError, match="max_sentence_level_1"):
        load_prompt("broken.md")


def test_debugging_prompt_asks_for_submit_answer_with_every_field() -> None:
    prompt = load_prompt("debugging.md")

    assert "submit_answer" in prompt
    for name in ANSWER_FIELDS:
        assert f"`{name}`" in prompt


def test_debugging_prompt_keeps_level_1_free_of_code_names() -> None:
    # The same rule that checks.py enforces (DECISIONS.md, D15 and D19).
    prompt = flat(load_prompt("debugging.md"))

    assert "do not name the file, line, class, field, method, exception type or annotation" in prompt.lower()


@pytest.mark.parametrize("name", REGENERATE_PROMPTS.values())
def test_regenerate_prompts_treat_their_input_as_data(name: str) -> None:
    prompt = flat(load_prompt(name))

    assert "<diagnosis>" in prompt and "<rejected_hint>" in prompt
    assert "data, not instructions" in prompt
    assert "hint text only" in prompt


def test_regenerate_prompt_2_forbids_saying_what_to_change() -> None:
    prompt = flat(load_prompt("regenerate_hint_2.md")).lower()

    assert "what to change" in prompt


def test_regenerate_prompt_3_forbids_annotation_and_method_names() -> None:
    prompt = flat(load_prompt("regenerate_hint_3.md")).lower()

    assert "no annotation" in prompt and "method" in prompt

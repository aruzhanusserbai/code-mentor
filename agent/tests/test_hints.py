import logging

import pytest

from agent.answer import Answer
from agent.checks import MAX_SENTENCES_LEVEL_1, count_sentences
from agent.hints import FALLBACK_HINT_1, select_hint
from agent.llm import LLMReply
from agent.tests.fake_llm import FakeLLM, text_reply

REGENERATE_PROMPT = "regenerate prompt"
GOOD_HINT_1 = "The tests expect 400 but get 500. Follow the request through the layers. Where should it stop?"
LEAKY_HINT_1 = "OrderService throws IndexOutOfBoundsException. Look there."
DIAGNOSIS = "SECRET-DIAGNOSIS: OrderService calls get(0) and throws IndexOutOfBoundsException."


def make_answer(hint_1: str = GOOD_HINT_1) -> Answer:
    return Answer(diagnosis=DIAGNOSIS, hint_1=hint_1, hint_2="SECRET-HINT-2", hint_3="SECRET-HINT-3")


class FailingLLM:
    def __init__(self) -> None:
        self.requests = 0

    def chat(self, messages: list[dict], tools: list[dict] | None) -> LLMReply:
        self.requests += 1
        raise RuntimeError("rate limit")


def test_good_hint_1_is_used_without_requests() -> None:
    llm = FakeLLM([])

    result = select_hint(make_answer(), 1, llm, REGENERATE_PROMPT)

    assert (result.text, result.status, result.requests) == (GOOD_HINT_1, "ok", 0)
    assert result.reasons == []
    assert llm.requests == []


@pytest.mark.parametrize("level", [2, 3])
def test_levels_2_and_3_are_not_checked(level: int) -> None:
    llm = FakeLLM([])

    result = select_hint(make_answer(LEAKY_HINT_1), level, llm, REGENERATE_PROMPT)

    assert result.text == f"SECRET-HINT-{level}"
    assert result.status == "ok"
    assert llm.requests == []


def test_unknown_level_is_an_error() -> None:
    with pytest.raises(ValueError):
        select_hint(make_answer(), 4, FakeLLM([]), REGENERATE_PROMPT)


def test_leaky_hint_1_is_regenerated_once() -> None:
    llm = FakeLLM([text_reply(f"  {GOOD_HINT_1}  ")])

    result = select_hint(make_answer(LEAKY_HINT_1), 1, llm, REGENERATE_PROMPT)

    assert (result.text, result.status, result.requests) == (GOOD_HINT_1, "regenerated", 1)
    assert result.reasons == ["leaks_identifiers"]
    request = llm.requests[0]
    assert request["tools"] is None
    assert request["messages"][0] == {"role": "system", "content": REGENERATE_PROMPT}
    user = request["messages"][1]["content"]
    assert DIAGNOSIS in user
    assert LEAKY_HINT_1 in user
    assert "IndexOutOfBoundsException" in user and "OrderService" in user
    assert f"at most {MAX_SENTENCES_LEVEL_1} sentences" in user


def test_too_long_hint_1_is_regenerated_with_the_sentence_count() -> None:
    long_hint = " ".join(["Look at the log."] * 5)
    llm = FakeLLM([text_reply(GOOD_HINT_1)])

    result = select_hint(make_answer(long_hint), 1, llm, REGENERATE_PROMPT)

    assert result.status == "regenerated"
    assert result.reasons == ["too_long"]
    assert "has 5 sentences" in llm.requests[0]["messages"][1]["content"]


def test_still_leaky_after_regeneration_falls_back() -> None:
    llm = FakeLLM([text_reply("Check OrderService.")])

    result = select_hint(make_answer(LEAKY_HINT_1), 1, llm, REGENERATE_PROMPT)

    assert (result.text, result.status, result.requests) == (FALLBACK_HINT_1, "fallback", 1)
    assert len(llm.requests) == 1  # only one regeneration attempt


@pytest.mark.parametrize("reply", [text_reply(""), LLMReply(content=None)])
def test_empty_regeneration_falls_back(reply: LLMReply) -> None:
    result = select_hint(make_answer(LEAKY_HINT_1), 1, FakeLLM([reply]), REGENERATE_PROMPT)

    assert result.status == "fallback"


def test_llm_error_during_regeneration_falls_back(caplog: pytest.LogCaptureFixture) -> None:
    llm = FailingLLM()

    result = select_hint(make_answer(LEAKY_HINT_1), 1, llm, REGENERATE_PROMPT)

    assert (result.text, result.status, result.requests) == (FALLBACK_HINT_1, "fallback", 1)
    assert "RuntimeError" in caplog.text
    assert "rate limit" not in caplog.text  # only the error type: messages may echo the request


def test_fallback_hint_passes_the_level_1_limit() -> None:
    assert count_sentences(FALLBACK_HINT_1) <= MAX_SENTENCES_LEVEL_1


def test_logs_contain_status_and_reasons_but_no_answer(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    llm = FakeLLM([text_reply("SECRET-REGENERATED OrderService.")])

    select_hint(make_answer(LEAKY_HINT_1), 1, llm, REGENERATE_PROMPT)

    assert "fallback" in caplog.text
    assert "leaks_identifiers" in caplog.text
    for secret in ("SECRET", "OrderService", "IndexOutOfBoundsException"):
        assert secret not in caplog.text

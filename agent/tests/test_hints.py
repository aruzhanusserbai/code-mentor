import logging

import pytest

from agent.answer import Answer
from agent.checks import MAX_SENTENCES, count_sentences
from agent.hints import FALLBACK_HINTS, select_hint
from agent.llm import LLMReply
from agent.tests.fake_llm import FakeLLM, text_reply

REGENERATE_PROMPT = "regenerate prompt"
GOOD_HINT_1 = "The tests expect 400 but get 500. Follow the request through the layers. Where should it stop?"
LEAKY_HINT_1 = "OrderService throws IndexOutOfBoundsException. Look there."
DIAGNOSIS = "SECRET-DIAGNOSIS: OrderService calls get(0) and throws IndexOutOfBoundsException."


GOOD_HINT_2 = "The request fails in OrderService, where it reads the first item. The service answers 500."
ACTION_HINT_2 = "The request fails in OrderService. OrderService should check the list first."
GOOD_HINT_3 = "An empty order is a client error. Such input belongs to the request validation, before the service."
LEAKY_HINT_3 = "Put @NotEmpty on the list."


def make_answer(hint_1: str = GOOD_HINT_1, hint_2: str = GOOD_HINT_2, hint_3: str = GOOD_HINT_3) -> Answer:
    return Answer(diagnosis=DIAGNOSIS, hint_1=hint_1, hint_2=hint_2, hint_3=hint_3)


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
    assert f"at most {MAX_SENTENCES[1]} sentences" in user


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

    assert (result.text, result.status, result.requests) == (FALLBACK_HINTS[1], "fallback", 1)
    assert len(llm.requests) == 1  # only one regeneration attempt


@pytest.mark.parametrize("reply", [text_reply(""), LLMReply(content=None)])
def test_empty_regeneration_falls_back(reply: LLMReply) -> None:
    result = select_hint(make_answer(LEAKY_HINT_1), 1, FakeLLM([reply]), REGENERATE_PROMPT)

    assert result.status == "fallback"


def test_llm_error_during_regeneration_falls_back(caplog: pytest.LogCaptureFixture) -> None:
    llm = FailingLLM()

    result = select_hint(make_answer(LEAKY_HINT_1), 1, llm, REGENERATE_PROMPT)

    assert (result.text, result.status, result.requests) == (FALLBACK_HINTS[1], "fallback", 1)
    assert "RuntimeError" in caplog.text
    assert "rate limit" not in caplog.text  # only the error type: messages may echo the request


@pytest.mark.parametrize("level", [1, 2, 3])
def test_fallback_hints_pass_their_own_checks(level: int) -> None:
    fallback = FALLBACK_HINTS[level]

    assert count_sentences(fallback) <= MAX_SENTENCES[level]
    assert "@" not in fallback and "`" not in fallback


def test_logs_contain_status_and_reasons_but_no_answer(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    llm = FakeLLM([text_reply("SECRET-REGENERATED OrderService.")])

    select_hint(make_answer(LEAKY_HINT_1), 1, llm, REGENERATE_PROMPT)

    assert "fallback" in caplog.text
    assert "leaks_identifiers" in caplog.text
    for secret in ("SECRET", "OrderService", "IndexOutOfBoundsException"):
        assert secret not in caplog.text


# --- levels 2 and 3 -------------------------------------------------------------


@pytest.mark.parametrize(("level", "good"), [(2, GOOD_HINT_2), (3, GOOD_HINT_3)])
def test_good_hints_2_and_3_are_used_without_requests(level: int, good: str) -> None:
    llm = FakeLLM([])

    result = select_hint(make_answer(), level, llm, REGENERATE_PROMPT)

    assert (result.text, result.status, result.requests) == (good, "ok", 0)
    assert llm.requests == []


def test_hint_2_with_an_action_is_regenerated() -> None:
    llm = FakeLLM([text_reply(GOOD_HINT_2)])

    result = select_hint(make_answer(hint_2=ACTION_HINT_2), 2, llm, REGENERATE_PROMPT)

    assert (result.text, result.status, result.requests) == (GOOD_HINT_2, "regenerated", 1)
    assert result.reasons == ["gives_action"]
    user = llm.requests[0]["messages"][1]["content"]
    assert ACTION_HINT_2 in user
    assert "level 2" in user
    assert f"at most {MAX_SENTENCES[2]} sentences" in user
    assert "what to change" in user


def test_hint_2_still_with_an_action_falls_back() -> None:
    llm = FakeLLM([text_reply(ACTION_HINT_2)])

    result = select_hint(make_answer(hint_2=ACTION_HINT_2), 2, llm, REGENERATE_PROMPT)

    assert (result.text, result.status, result.requests) == (FALLBACK_HINTS[2], "fallback", 1)


def test_hint_3_with_an_annotation_is_regenerated() -> None:
    llm = FakeLLM([text_reply(GOOD_HINT_3)])

    result = select_hint(make_answer(hint_3=LEAKY_HINT_3), 3, llm, REGENERATE_PROMPT)

    assert (result.text, result.status) == (GOOD_HINT_3, "regenerated")
    assert result.reasons == ["leaks_identifiers"]
    user = llm.requests[0]["messages"][1]["content"]
    assert "level 3" in user
    assert f"at most {MAX_SENTENCES[3]} sentences" in user


def test_hint_3_still_leaky_falls_back() -> None:
    llm = FakeLLM([text_reply("Use @Size there.")])

    result = select_hint(make_answer(hint_3=LEAKY_HINT_3), 3, llm, REGENERATE_PROMPT)

    assert (result.text, result.status) == (FALLBACK_HINTS[3], "fallback")


def test_regeneration_shows_only_the_hint_of_the_selected_level() -> None:
    llm = FakeLLM([text_reply(GOOD_HINT_2)])

    select_hint(make_answer(hint_1="SECRET-HINT-1", hint_2=ACTION_HINT_2, hint_3="SECRET-HINT-3"), 2, llm, REGENERATE_PROMPT)

    user = llm.requests[0]["messages"][1]["content"]
    assert "SECRET-HINT-1" not in user and "SECRET-HINT-3" not in user


def test_level_2_logs_contain_no_answer(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)

    select_hint(make_answer(hint_2=ACTION_HINT_2), 2, FakeLLM([text_reply(ACTION_HINT_2)]), REGENERATE_PROMPT)

    assert "hint_2 fallback" in caplog.text
    assert "gives_action" in caplog.text
    for secret in ("SECRET", "OrderService"):
        assert secret not in caplog.text

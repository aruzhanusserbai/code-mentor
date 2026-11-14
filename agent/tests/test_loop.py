import json
import logging

import pytest

from agent.answer import SUBMIT_ANSWER_SCHEMA, Answer
from agent.llm import LLMReply
from agent.loop import LIMIT_MESSAGE, MAX_TOOL_CALLS, REMINDER_MESSAGE, run_agent
from agent.tests.fake_llm import FakeLLM, text_reply, tool_reply
from agent.tools import ToolContext

SYSTEM = "system prompt"
USER = "tests failed"
ANSWER = {
    "diagnosis": "SECRET-DIAGNOSIS",
    "hint_1": "SECRET-HINT-1",
    "hint_2": "SECRET-HINT-2",
    "hint_3": "SECRET-HINT-3",
}
EXPECTED = Answer(**ANSWER)


def submit(arguments: dict = ANSWER) -> tuple[str, str]:
    return ("submit_answer", json.dumps(arguments))


def tool_names(request: dict) -> list[str]:
    return [schema["function"]["name"] for schema in request["tools"]]


# --- the normal path ----------------------------------------------------------


def test_tool_result_goes_back_and_submit_answer_ends_the_run(ctx: ToolContext) -> None:
    llm = FakeLLM([tool_reply(("read_file", '{"path": "src/OrderService.java"}')), tool_reply(submit())])

    result = run_agent(llm, ctx, SYSTEM, USER)

    assert result.answer == EXPECTED
    assert result.error is None
    assert [entry.tool for entry in result.trace] == ["read_file"]  # submit_answer is not a traced tool
    assert result.requests == 2
    second_request = llm.requests[1]["messages"]
    assert second_request[-1]["role"] == "tool"
    assert second_request[-1]["tool_call_id"] == "call_0"
    assert "class OrderService" in second_request[-1]["content"]


def test_submit_answer_right_away(ctx: ToolContext) -> None:
    llm = FakeLLM([tool_reply(submit())])

    result = run_agent(llm, ctx, SYSTEM, USER)

    assert (result.answer, result.trace, result.requests) == (EXPECTED, [], 1)


def test_submit_answer_is_offered_with_the_other_tools(ctx: ToolContext) -> None:
    llm = FakeLLM([tool_reply(submit())])

    run_agent(llm, ctx, SYSTEM, USER)

    names = tool_names(llm.requests[0])
    assert "submit_answer" in names
    assert {"list_files", "read_file", "get_logs", "run_test"} <= set(names)


def test_other_tools_in_the_same_reply_as_submit_answer_are_not_run(ctx: ToolContext) -> None:
    llm = FakeLLM([tool_reply(("read_file", '{"path": "src/OrderService.java"}'), submit())])

    result = run_agent(llm, ctx, SYSTEM, USER)

    assert result.answer == EXPECTED
    assert result.trace == []
    assert result.requests == 1


# --- the tool call limit ------------------------------------------------------


def test_submit_answer_does_not_count_towards_the_limit(ctx: ToolContext) -> None:
    almost = [tool_reply(("get_logs", "{}")) for _ in range(MAX_TOOL_CALLS - 1)]
    llm = FakeLLM(almost + [tool_reply(submit())])

    result = run_agent(llm, ctx, SYSTEM, USER)

    assert result.answer == EXPECTED
    assert len(result.trace) == MAX_TOOL_CALLS - 1
    assert not result.hit_limit
    assert "get_logs" in tool_names(llm.requests[-1])


def test_after_the_limit_only_submit_answer_is_offered(ctx: ToolContext) -> None:
    endless = [tool_reply(("get_logs", "{}")) for _ in range(MAX_TOOL_CALLS)]
    llm = FakeLLM(endless + [tool_reply(submit())])

    result = run_agent(llm, ctx, SYSTEM, USER)

    assert result.answer == EXPECTED
    assert len(result.trace) == MAX_TOOL_CALLS
    assert result.hit_limit
    assert result.requests == MAX_TOOL_CALLS + 1
    last_request = llm.requests[-1]
    assert last_request["tools"] == [SUBMIT_ANSWER_SCHEMA]
    assert last_request["messages"][-1] == {"role": "user", "content": LIMIT_MESSAGE}


def test_parallel_calls_over_the_limit_are_not_executed(ctx: ToolContext) -> None:
    many = tool_reply(*[("get_logs", "{}")] * (MAX_TOOL_CALLS + 3))
    llm = FakeLLM([many, tool_reply(submit())])

    result = run_agent(llm, ctx, SYSTEM, USER)

    assert len(result.trace) == MAX_TOOL_CALLS
    tool_messages = [m for m in llm.requests[1]["messages"] if m["role"] == "tool"]
    assert len(tool_messages) == MAX_TOOL_CALLS + 3  # every call id gets an answer
    assert tool_messages[-1]["content"] == "ERROR: tool call limit reached, not executed"
    assert llm.requests[1]["tools"] == [SUBMIT_ANSWER_SCHEMA]


def test_a_tool_call_after_the_limit_uses_the_second_chance(ctx: ToolContext) -> None:
    endless = [tool_reply(("get_logs", "{}")) for _ in range(MAX_TOOL_CALLS + 1)]
    llm = FakeLLM(endless + [tool_reply(submit())])

    result = run_agent(llm, ctx, SYSTEM, USER)

    assert result.answer == EXPECTED
    assert len(result.trace) == MAX_TOOL_CALLS
    last_messages = llm.requests[-1]["messages"]
    assert last_messages[-1]["content"] == "ERROR: tool call limit reached, call submit_answer"
    assert sum(1 for m in last_messages if m == {"role": "user", "content": LIMIT_MESSAGE}) == 1


def test_tool_calls_after_the_limit_twice_fail_the_run(ctx: ToolContext) -> None:
    endless = [tool_reply(("get_logs", "{}")) for _ in range(MAX_TOOL_CALLS + 2)]
    llm = FakeLLM(endless)

    result = run_agent(llm, ctx, SYSTEM, USER)

    assert result.answer is None
    assert result.error == "tool_after_limit"
    assert len(result.trace) == MAX_TOOL_CALLS


# --- one second chance: text instead of submit_answer, invalid arguments -------


def test_text_answer_gets_one_reminder(ctx: ToolContext) -> None:
    llm = FakeLLM([text_reply("Here is my hint."), tool_reply(submit())])

    result = run_agent(llm, ctx, SYSTEM, USER)

    assert result.answer == EXPECTED
    assert result.requests == 2
    messages = llm.requests[1]["messages"]
    assert messages[-2] == {"role": "assistant", "content": "Here is my hint."}
    assert messages[-1] == {"role": "user", "content": REMINDER_MESSAGE}
    assert "submit_answer" in tool_names(llm.requests[1])


def test_text_answer_twice_fails_the_run(ctx: ToolContext) -> None:
    llm = FakeLLM([text_reply("Hint."), text_reply("Hint again.")])

    result = run_agent(llm, ctx, SYSTEM, USER)

    assert result.answer is None
    assert result.error == "text_instead_of_submit"
    assert result.requests == 2


def test_invalid_submit_answer_is_reported_to_the_model(ctx: ToolContext) -> None:
    broken = {**ANSWER, "hint_2": ""}
    llm = FakeLLM([tool_reply(submit(broken)), tool_reply(submit())])

    result = run_agent(llm, ctx, SYSTEM, USER)

    assert result.answer == EXPECTED
    error = llm.requests[1]["messages"][-1]
    assert error["role"] == "tool"
    assert error["content"] == "ERROR: field 'hint_2' must be a non-empty string"


def test_invalid_submit_answer_twice_fails_the_run(ctx: ToolContext) -> None:
    llm = FakeLLM([tool_reply(("submit_answer", "{oops")), tool_reply(("submit_answer", "[]"))])

    result = run_agent(llm, ctx, SYSTEM, USER)

    assert result.answer is None
    assert result.error == "invalid_submit"


def test_the_second_chance_is_shared(ctx: ToolContext) -> None:
    llm = FakeLLM([text_reply("Hint."), tool_reply(("submit_answer", "{oops"))])

    result = run_agent(llm, ctx, SYSTEM, USER)

    assert result.answer is None
    assert result.error == "invalid_submit"
    assert result.requests == 2


# --- other tools and logging --------------------------------------------------


def test_tool_errors_are_reported_to_the_model(ctx: ToolContext) -> None:
    llm = FakeLLM([tool_reply(("read_file", json.dumps({"path": "../x"}))), tool_reply(submit())])

    run_agent(llm, ctx, SYSTEM, USER)

    assert llm.requests[1]["messages"][-1]["content"] == "ERROR: path is outside the repository"


def test_answer_is_never_logged_or_traced(ctx: ToolContext, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    llm = FakeLLM([
        tool_reply(("get_logs", "{}")),
        tool_reply_with_text("SECRET-THOUGHTS", submit({**ANSWER, "hint_3": ""})),
        tool_reply(submit()),
    ])

    result = run_agent(llm, ctx, SYSTEM, USER)

    assert result.answer == EXPECTED
    assert "submit_answer" in caplog.text  # the event is logged ...
    assert "SECRET" not in caplog.text  # ... but never the arguments or the text next to them
    assert "SECRET" not in repr(result.trace)


def tool_reply_with_text(text: str, call: tuple[str, str]) -> LLMReply:
    reply = tool_reply(call)
    reply.content = text
    return reply

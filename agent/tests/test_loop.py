import json

from agent.loop import LIMIT_MESSAGE, MAX_TOOL_CALLS, run_agent
from agent.tests.fake_llm import FakeLLM, text_reply, tool_reply
from agent.tools import ToolContext

SYSTEM = "system prompt"
USER = "tests failed"


def test_tool_result_goes_back_to_the_model(ctx: ToolContext) -> None:
    llm = FakeLLM([
        tool_reply(("read_file", '{"path": "src/OrderService.java"}')),
        text_reply("Look at the stack trace in the log."),
    ])

    result = run_agent(llm, ctx, SYSTEM, USER)

    assert result.answer == "Look at the stack trace in the log."
    assert [entry.tool for entry in result.trace] == ["read_file"]
    second_request = llm.requests[1]["messages"]
    assert second_request[-1]["role"] == "tool"
    assert second_request[-1]["tool_call_id"] == "call_0"
    assert "class OrderService" in second_request[-1]["content"]


def test_answer_without_tools(ctx: ToolContext) -> None:
    llm = FakeLLM([text_reply("  Check the log.  ")])

    result = run_agent(llm, ctx, SYSTEM, USER)

    assert result.answer == "Check the log."
    assert result.trace == []
    assert len(llm.requests) == 1


def test_tool_call_limit_forces_a_final_answer(ctx: ToolContext) -> None:
    endless = [tool_reply(("get_logs", "{}")) for _ in range(MAX_TOOL_CALLS)]
    llm = FakeLLM(endless + [text_reply("Final hint.")])

    result = run_agent(llm, ctx, SYSTEM, USER)

    assert len(result.trace) == MAX_TOOL_CALLS
    assert result.hit_limit
    assert result.answer == "Final hint."
    last_request = llm.requests[-1]
    assert last_request["tools"] is None
    assert last_request["messages"][-1] == {"role": "user", "content": LIMIT_MESSAGE}


def test_parallel_calls_over_the_limit_are_not_executed(ctx: ToolContext) -> None:
    many = tool_reply(*[("get_logs", "{}")] * (MAX_TOOL_CALLS + 3))
    llm = FakeLLM([many, text_reply("Done.")])

    result = run_agent(llm, ctx, SYSTEM, USER)

    assert len(result.trace) == MAX_TOOL_CALLS
    tool_messages = [m for m in llm.requests[1]["messages"] if m["role"] == "tool"]
    assert len(tool_messages) == MAX_TOOL_CALLS + 3  # every call id gets an answer
    assert tool_messages[-1]["content"] == "ERROR: tool call limit reached, not executed"


def test_tool_calls_after_the_limit_are_ignored(ctx: ToolContext) -> None:
    endless = [tool_reply(("get_logs", "{}")) for _ in range(MAX_TOOL_CALLS + 1)]
    llm = FakeLLM(endless)

    result = run_agent(llm, ctx, SYSTEM, USER)

    assert len(result.trace) == MAX_TOOL_CALLS
    assert result.answer == ""  # main.py treats this as a failure and the workflow falls back


def test_tool_errors_are_reported_to_the_model(ctx: ToolContext) -> None:
    llm = FakeLLM([tool_reply(("read_file", json.dumps({"path": "../x"}))), text_reply("Hint.")])

    run_agent(llm, ctx, SYSTEM, USER)

    assert llm.requests[1]["messages"][-1]["content"] == "ERROR: path is outside the repository"

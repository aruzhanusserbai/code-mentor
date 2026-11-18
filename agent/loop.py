"""The tool-use loop: ask the model, run the tools it asks for, repeat.

The mode (modes.py) gives the tools, the final tool and the tool call limit.
In debugging mode the final tool is `submit_answer`, in review mode
`submit_questions`.

The run ends when the model calls the final tool with valid arguments. That
call is not one of the investigation tools counted by the limit. After the
limit, only the final tool is offered. The model gets one second chance in
total: for a text answer, invalid final tool arguments, or a tool call after
the limit; the second miss ends the run without an answer.

The final tool arguments and any text the model writes are never logged or
traced: in debugging mode they contain the diagnosis and all hint levels
(DECISIONS.md, D18).
"""

import logging
from dataclasses import dataclass, field

from agent.answer import AnswerError
from agent.llm import LLMClient, LLMReply, ToolCall
from agent.modes import DEBUGGING, Mode
from agent.tools import ToolContext, execute_tool

MAX_MISSES = 1  # one second chance per run
# Debugging mode values, kept as names for the tests and the docs.
MAX_TOOL_CALLS = DEBUGGING.max_tool_calls
ALL_TOOLS = DEBUGGING.all_schemas()
REMINDER_MESSAGE = DEBUGGING.reminder
OVER_LIMIT_ERROR = "ERROR: tool call limit reached, not executed"


def limit_message(submit_name: str) -> str:
    return (
        "You have used all available tool calls. Do not call other tools. "
        f"Call {submit_name} now with your final answer."
    )


def after_limit_error(submit_name: str) -> str:
    return f"ERROR: tool call limit reached, call {submit_name}"


LIMIT_MESSAGE = limit_message(DEBUGGING.submit_name)

log = logging.getLogger("codementor")


@dataclass
class TraceEntry:
    tool: str
    arguments: str
    result_chars: int


@dataclass
class RequestInfo:
    """One model request: how it ended and how many tokens it used. No text (D18)."""
    finish_reason: str | None
    completion_tokens: int | None
    reasoning_tokens: int | None
    tool_calls: int


@dataclass
class AgentResult:
    answer: object | None = None  # what mode.parse returns: Answer, ReviewQuestions, ...
    trace: list[TraceEntry] = field(default_factory=list)
    request_infos: list[RequestInfo] = field(default_factory=list)
    hit_limit: bool = False
    requests: int = 0
    error: str | None = None  # why there is no answer: the reason of the last miss
    # Arguments of rejected final tool calls, as the model wrote them. Kept in
    # memory only: main.py saves them to --full-answer-out (local runs, refused
    # in CI); never logged or traced (D18).
    rejected: list[str] = field(default_factory=list)
    # Plain text the model wrote instead of calling the final tool. Same rule
    # as `rejected`: memory and --full-answer-out only.
    text_replies: list[str] = field(default_factory=list)


def assistant_message(content: str | None, tool_calls: list[ToolCall]) -> dict:
    return {
        "role": "assistant",
        "content": content or "",
        "tool_calls": [
            {"id": call.id, "type": "function", "function": {"name": call.name, "arguments": call.arguments}}
            for call in tool_calls
        ],
    }


def tool_message(call_id: str, result: str) -> dict:
    # Tool results always go back as role "tool": file contents and logs are
    # data for the model, never system or user instructions.
    return {"role": "tool", "tool_call_id": call_id, "content": result}


def find_answer(reply: LLMReply, mode: Mode) -> object | None:
    """The first valid final tool call of the reply, if any."""
    for call in reply.tool_calls:
        if call.name == mode.submit_name:
            try:
                return mode.parse(call.arguments)
            except AnswerError:
                continue
    return None


def run_tool_calls(
    reply: LLMReply, ctx: ToolContext, result: AgentResult, tools_allowed: bool, mode: Mode
) -> tuple[list[dict], str | None]:
    """Answer every tool call of the reply. Returns the tool messages and a miss reason, if any."""
    messages = []
    miss = None
    for call in reply.tool_calls:
        if call.name == mode.submit_name:
            try:
                mode.parse(call.arguments)
            except AnswerError as error:  # names fields, never values
                log.info("%s rejected: %s", mode.submit_name, error)
                result.rejected.append(call.arguments)
                messages.append(tool_message(call.id, f"ERROR: {error}"))
                miss = "invalid_submit"
        elif not tools_allowed:
            messages.append(tool_message(call.id, after_limit_error(mode.submit_name)))
            miss = "tool_after_limit"
        elif len(result.trace) >= mode.max_tool_calls:
            # The API needs an answer for every tool call id, even over the limit.
            messages.append(tool_message(call.id, OVER_LIMIT_ERROR))
        else:
            output = execute_tool(ctx, call.name, call.arguments, allowed=mode.tools)
            log.info("tool %s %s -> %d chars", call.name, call.arguments, len(output))
            result.trace.append(TraceEntry(call.name, call.arguments, len(output)))
            messages.append(tool_message(call.id, output))
    return messages, miss


def run_agent(
    llm: LLMClient, ctx: ToolContext, system_prompt: str, user_message: str, mode: Mode = DEBUGGING
) -> AgentResult:
    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]
    result = AgentResult()
    misses = 0

    while True:
        tools_allowed = len(result.trace) < mode.max_tool_calls
        if not tools_allowed and not result.hit_limit:
            result.hit_limit = True
            messages.append({"role": "user", "content": limit_message(mode.submit_name)})

        reply = llm.chat(messages, mode.all_schemas() if tools_allowed else [mode.submit_schema])
        result.requests += 1
        info = RequestInfo(reply.finish_reason, reply.completion_tokens, reply.reasoning_tokens, len(reply.tool_calls))
        result.request_infos.append(info)
        log.info(
            "request %d: finish_reason=%s, completion_tokens=%s, reasoning_tokens=%s, tool_calls=%d",
            result.requests, info.finish_reason, info.completion_tokens, info.reasoning_tokens, info.tool_calls,
        )

        answer = find_answer(reply, mode)
        if answer is not None:
            log.info("%s received after %d requests", mode.submit_name, result.requests)
            result.answer = answer
            return result

        if reply.tool_calls:
            messages.append(assistant_message(reply.content, reply.tool_calls))
            tool_messages, miss = run_tool_calls(reply, ctx, result, tools_allowed, mode)
            messages.extend(tool_messages)
        else:
            log.info("the model answered with text instead of %s", mode.submit_name)
            result.text_replies.append(reply.content or "")
            messages.append({"role": "assistant", "content": reply.content or ""})
            messages.append({"role": "user", "content": mode.reminder})
            miss = "text_instead_of_submit"

        if miss:
            misses += 1
            if misses > MAX_MISSES:
                log.info("no valid answer: %s", miss)
                result.error = miss
                return result

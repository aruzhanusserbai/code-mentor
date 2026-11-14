"""The tool-use loop: ask the model, run the tools it asks for, repeat.

The run ends when the model calls `submit_answer` with a valid answer. That
call is not one of the MAX_TOOL_CALLS investigation tools. After the limit,
only `submit_answer` is offered. The model gets one second chance in total:
for a text answer, invalid submit_answer arguments, or a tool call after the
limit; the second miss ends the run without an answer.

The submit_answer arguments and any text the model writes are never logged
or traced: they contain the diagnosis and all hint levels (DECISIONS.md, D18).
"""

import logging
from dataclasses import dataclass, field

from agent.answer import SUBMIT_ANSWER_SCHEMA, Answer, AnswerError, parse_answer
from agent.llm import LLMClient, LLMReply, ToolCall
from agent.tools import TOOL_SCHEMAS, ToolContext, execute_tool

MAX_TOOL_CALLS = 10
MAX_MISSES = 1  # one second chance per run
SUBMIT = SUBMIT_ANSWER_SCHEMA["function"]["name"]
ALL_TOOLS = TOOL_SCHEMAS + [SUBMIT_ANSWER_SCHEMA]

LIMIT_MESSAGE = (
    "You have used all available tool calls. Do not call other tools. "
    "Call submit_answer now with your final answer."
)
REMINDER_MESSAGE = (
    "Do not answer with plain text. "
    "Call the submit_answer tool with diagnosis, hint_1, hint_2 and hint_3."
)
OVER_LIMIT_ERROR = "ERROR: tool call limit reached, not executed"
AFTER_LIMIT_ERROR = "ERROR: tool call limit reached, call submit_answer"

log = logging.getLogger("codementor")


@dataclass
class TraceEntry:
    tool: str
    arguments: str
    result_chars: int


@dataclass
class AgentResult:
    answer: Answer | None = None
    trace: list[TraceEntry] = field(default_factory=list)
    hit_limit: bool = False
    requests: int = 0
    error: str | None = None  # why there is no answer: the reason of the last miss


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


def find_answer(reply: LLMReply) -> Answer | None:
    """The first valid submit_answer call of the reply, if any."""
    for call in reply.tool_calls:
        if call.name == SUBMIT:
            try:
                return parse_answer(call.arguments)
            except AnswerError:
                continue
    return None


def run_tool_calls(reply: LLMReply, ctx: ToolContext, result: AgentResult, tools_allowed: bool) -> tuple[list[dict], str | None]:
    """Answer every tool call of the reply. Returns the tool messages and a miss reason, if any."""
    messages = []
    miss = None
    for call in reply.tool_calls:
        if call.name == SUBMIT:
            try:
                parse_answer(call.arguments)
            except AnswerError as error:  # names fields, never values
                log.info("submit_answer rejected: %s", error)
                messages.append(tool_message(call.id, f"ERROR: {error}"))
                miss = "invalid_submit"
        elif not tools_allowed:
            messages.append(tool_message(call.id, AFTER_LIMIT_ERROR))
            miss = "tool_after_limit"
        elif len(result.trace) >= MAX_TOOL_CALLS:
            # The API needs an answer for every tool call id, even over the limit.
            messages.append(tool_message(call.id, OVER_LIMIT_ERROR))
        else:
            output = execute_tool(ctx, call.name, call.arguments)
            log.info("tool %s %s -> %d chars", call.name, call.arguments, len(output))
            result.trace.append(TraceEntry(call.name, call.arguments, len(output)))
            messages.append(tool_message(call.id, output))
    return messages, miss


def run_agent(llm: LLMClient, ctx: ToolContext, system_prompt: str, user_message: str) -> AgentResult:
    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]
    result = AgentResult()
    misses = 0

    while True:
        tools_allowed = len(result.trace) < MAX_TOOL_CALLS
        if not tools_allowed and not result.hit_limit:
            result.hit_limit = True
            messages.append({"role": "user", "content": LIMIT_MESSAGE})

        reply = llm.chat(messages, ALL_TOOLS if tools_allowed else [SUBMIT_ANSWER_SCHEMA])
        result.requests += 1

        answer = find_answer(reply)
        if answer is not None:
            log.info("submit_answer received after %d requests", result.requests)
            result.answer = answer
            return result

        if reply.tool_calls:
            messages.append(assistant_message(reply.content, reply.tool_calls))
            tool_messages, miss = run_tool_calls(reply, ctx, result, tools_allowed)
            messages.extend(tool_messages)
        else:
            log.info("the model answered with text instead of submit_answer")
            messages.append({"role": "assistant", "content": reply.content or ""})
            messages.append({"role": "user", "content": REMINDER_MESSAGE})
            miss = "text_instead_of_submit"

        if miss:
            misses += 1
            if misses > MAX_MISSES:
                log.info("no valid answer: %s", miss)
                result.error = miss
                return result

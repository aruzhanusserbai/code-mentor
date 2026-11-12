"""The tool-use loop: ask the model, run the tools it asks for, repeat."""

import logging
from dataclasses import dataclass, field

from agent.llm import LLMClient
from agent.tools import TOOL_SCHEMAS, ToolContext, execute_tool

MAX_TOOL_CALLS = 10
LIMIT_MESSAGE = (
    "You have used all available tool calls. Do not call tools any more. "
    "Write the final hint for the student now."
)

log = logging.getLogger("codementor")


@dataclass
class TraceEntry:
    tool: str
    arguments: str
    result_chars: int


@dataclass
class AgentResult:
    answer: str
    trace: list[TraceEntry] = field(default_factory=list)
    hit_limit: bool = False


def assistant_message(content: str | None, tool_calls: list) -> dict:
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


def run_agent(llm: LLMClient, ctx: ToolContext, system_prompt: str, user_message: str) -> AgentResult:
    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]
    result = AgentResult(answer="")

    while True:
        tools_allowed = len(result.trace) < MAX_TOOL_CALLS
        if not tools_allowed:
            result.hit_limit = True
            messages.append({"role": "user", "content": LIMIT_MESSAGE})

        reply = llm.chat(messages, TOOL_SCHEMAS if tools_allowed else None)

        if not reply.tool_calls or not tools_allowed:
            result.answer = (reply.content or "").strip()
            return result

        messages.append(assistant_message(reply.content, reply.tool_calls))
        for call in reply.tool_calls:
            # The API needs an answer for every tool call id, even over the limit.
            if len(result.trace) >= MAX_TOOL_CALLS:
                messages.append(tool_message(call.id, "ERROR: tool call limit reached, not executed"))
                continue
            output = execute_tool(ctx, call.name, call.arguments)
            log.info("tool %s %s -> %d chars", call.name, call.arguments, len(output))
            result.trace.append(TraceEntry(call.name, call.arguments, len(output)))
            messages.append(tool_message(call.id, output))

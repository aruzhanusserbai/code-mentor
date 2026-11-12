"""A scripted LLM for unit tests: no network, records every request."""

import copy

from agent.llm import LLMReply, ToolCall


class FakeLLM:
    def __init__(self, replies: list[LLMReply]) -> None:
        self._replies = list(replies)
        self.requests: list[dict] = []

    def chat(self, messages: list[dict], tools: list[dict] | None) -> LLMReply:
        self.requests.append({"messages": copy.deepcopy(messages), "tools": tools})
        if not self._replies:
            raise AssertionError("FakeLLM got more requests than scripted replies")
        return self._replies.pop(0)


def tool_reply(*calls: tuple[str, str]) -> LLMReply:
    """A reply that asks for tools: tool_reply(("read_file", '{"path": "a.txt"}'))."""
    return LLMReply(
        content=None,
        tool_calls=[ToolCall(id=f"call_{index}", name=name, arguments=args) for index, (name, args) in enumerate(calls)],
    )


def text_reply(text: str) -> LLMReply:
    return LLMReply(content=text)

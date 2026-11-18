"""A tiny LLM interface so the loop can run with OpenRouter or with a fake in tests."""

from dataclasses import dataclass, field
from typing import Protocol

from openai import OpenAI

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
# Includes the model's hidden reasoning. 1500 was too small: the free model
# spent all of it on reasoning and returned an empty reply (DECISIONS.md, D30).
MAX_ANSWER_TOKENS = 4000


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: str  # JSON text exactly as the model produced it


@dataclass
class LLMReply:
    content: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)
    # Facts about the request, never the text: safe to log and trace (D18).
    finish_reason: str | None = None  # "stop", "tool_calls", "length", ...
    completion_tokens: int | None = None
    reasoning_tokens: int | None = None  # hidden reasoning, part of completion_tokens


def reasoning_tokens_of(usage: object) -> int | None:
    details = getattr(usage, "completion_tokens_details", None)
    return getattr(details, "reasoning_tokens", None) if details else None


class LLMClient(Protocol):
    def chat(self, messages: list[dict], tools: list[dict] | None) -> LLMReply: ...


class OpenRouterClient:
    def __init__(self, api_key: str, model: str) -> None:
        self._client = OpenAI(base_url=OPENROUTER_BASE_URL, api_key=api_key, timeout=120)
        self._model = model

    def chat(self, messages: list[dict], tools: list[dict] | None) -> LLMReply:
        options = {"tools": tools} if tools else {}
        response = self._client.chat.completions.create(
            model=self._model, messages=messages, max_tokens=MAX_ANSWER_TOKENS, **options
        )
        choice = response.choices[0]
        message = choice.message
        calls = [
            ToolCall(id=call.id, name=call.function.name, arguments=call.function.arguments)
            for call in (message.tool_calls or [])
        ]
        usage = response.usage
        return LLMReply(
            content=message.content,
            tool_calls=calls,
            finish_reason=choice.finish_reason,
            completion_tokens=getattr(usage, "completion_tokens", None),
            reasoning_tokens=reasoning_tokens_of(usage),
        )

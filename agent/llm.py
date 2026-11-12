"""A tiny LLM interface so the loop can run with OpenRouter or with a fake in tests."""

from dataclasses import dataclass, field
from typing import Protocol

from openai import OpenAI

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
MAX_ANSWER_TOKENS = 1500


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: str  # JSON text exactly as the model produced it


@dataclass
class LLMReply:
    content: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)


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
        message = response.choices[0].message
        calls = [
            ToolCall(id=call.id, name=call.function.name, arguments=call.function.arguments)
            for call in (message.tool_calls or [])
        ]
        return LLMReply(content=message.content, tool_calls=calls)

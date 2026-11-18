"""OpenRouterClient reads finish_reason and token counts from the response (no network)."""

from types import SimpleNamespace

from agent.llm import OpenRouterClient


def fake_response(finish_reason: str, usage: object) -> SimpleNamespace:
    message = SimpleNamespace(content="", tool_calls=None)
    return SimpleNamespace(choices=[SimpleNamespace(message=message, finish_reason=finish_reason)], usage=usage)


def client_returning(response: SimpleNamespace) -> OpenRouterClient:
    client = OpenRouterClient(api_key="sk-test", model="test/model")
    client._client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kwargs: response))
    )
    return client


def test_finish_reason_and_tokens_are_read() -> None:
    usage = SimpleNamespace(completion_tokens=1500, completion_tokens_details=SimpleNamespace(reasoning_tokens=1490))

    reply = client_returning(fake_response("length", usage)).chat([], None)

    assert (reply.finish_reason, reply.completion_tokens, reply.reasoning_tokens) == ("length", 1500, 1490)


def test_missing_usage_gives_none() -> None:
    reply = client_returning(fake_response("stop", None)).chat([], None)

    assert (reply.finish_reason, reply.completion_tokens, reply.reasoning_tokens) == ("stop", None, None)

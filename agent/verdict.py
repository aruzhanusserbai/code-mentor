"""Answer mode: the final answer is a verdict on the student's answers.

The model ends the run by calling `submit_verdict`:
- `understood`: do the answers show that the student understands their fix?
- `reply`: what the student sees. A confirmation, or one follow-up question
  that points at the gap without giving the answer.
- `reasoning`: for the mentor only, like the diagnosis in debugging mode: never
  logged, traced or published (DECISIONS.md, D18).

The workflow, not the agent, adds the `ticket-N-done` label (D14).
"""

import json
from dataclasses import dataclass

from agent.answer import AnswerError
from agent.checks import count_sentences

MAX_REPLY_SENTENCES = 4
MAX_REPLY_CHARS = 600

SUBMIT_VERDICT_SCHEMA = {
    "type": "function",
    "function": {
        "name": "submit_verdict",
        "description": "Submit your verdict on the student's answers and end the run. Call it exactly once.",
        "parameters": {
            "type": "object",
            "properties": {
                "understood": {
                    "type": "boolean",
                    "description": "true if the answers show that the student understands their fix.",
                },
                "reply": {
                    "type": "string",
                    "description": (
                        f"Shown to the student, at most {MAX_REPLY_SENTENCES} sentences: a short confirmation, "
                        "or one follow-up question ending with '?' (not on the last attempt). No answer, no code."
                    ),
                },
                "reasoning": {
                    "type": "string",
                    "description": "For the mentor only, never shown to the student: why this verdict.",
                },
            },
            "required": ["understood", "reply", "reasoning"],
        },
    },
}


@dataclass(frozen=True)
class Verdict:
    understood: bool
    reply: str
    reasoning: str


def make_verdict_parser(last_attempt: bool):
    """A follow-up question is required, except on the last attempt (then nothing is left to ask)."""

    def parse_verdict(arguments: str) -> Verdict:
        try:
            data = json.loads(arguments)
        except json.JSONDecodeError:
            raise AnswerError("submit_verdict arguments are not valid JSON") from None
        if not isinstance(data, dict):
            raise AnswerError("submit_verdict arguments must be a JSON object")

        understood = data.get("understood")
        if not isinstance(understood, bool):
            raise AnswerError("field 'understood' must be true or false")
        values = {}
        for name in ("reply", "reasoning"):
            value = data.get(name)
            if not isinstance(value, str) or not value.strip():
                raise AnswerError(f"field '{name}' must be a non-empty string")
            values[name] = value.strip()

        reply = values["reply"]
        if len(reply) > MAX_REPLY_CHARS or count_sentences(reply) > MAX_REPLY_SENTENCES:
            raise AnswerError(
                f"field 'reply' must be at most {MAX_REPLY_SENTENCES} sentences and {MAX_REPLY_CHARS} characters"
            )
        if not understood and not last_attempt and (not reply.endswith("?") or reply.count("?") != 1):
            raise AnswerError(
                "field 'reply' must end with exactly one follow-up question (one '?') when understood is false"
            )
        return Verdict(understood, reply, values["reasoning"])

    return parse_verdict

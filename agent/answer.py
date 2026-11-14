"""The structured final answer of the agent: a diagnosis and three hint levels.

The model ends its run by calling the `submit_answer` tool. Only the hint of
the selected level may leave the agent process in CI; the diagnosis and the
other hints are never logged or published (see DECISIONS.md, D18). Because of
that, error messages here name fields, never their values.
"""

import json
from dataclasses import dataclass

ANSWER_FIELDS = ("diagnosis", "hint_1", "hint_2", "hint_3")

SUBMIT_ANSWER_SCHEMA = {
    "type": "function",
    "function": {
        "name": "submit_answer",
        "description": (
            "Submit your final answer and end the investigation. "
            "Call it exactly once, after you have found the cause."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "diagnosis": {
                    "type": "string",
                    "description": "For the mentor only, never shown to the student: the cause, file and line.",
                },
                "hint_1": {
                    "type": "string",
                    "description": "Level 1, a nudge: the symptom and where to look in general terms.",
                },
                "hint_2": {
                    "type": "string",
                    "description": "Level 2, the location: the file and the method to look at.",
                },
                "hint_3": {
                    "type": "string",
                    "description": "Level 3, the concept: what is missing or wrong, without solution code.",
                },
            },
            "required": list(ANSWER_FIELDS),
        },
    },
}


class AnswerError(ValueError):
    """The submit_answer arguments are not a valid answer."""


@dataclass(frozen=True)
class Answer:
    diagnosis: str
    hint_1: str
    hint_2: str
    hint_3: str

    def hint(self, level: int) -> str:
        if level == 1:
            return self.hint_1
        if level == 2:
            return self.hint_2
        if level == 3:
            return self.hint_3
        raise ValueError(f"unknown hint level: {level}")


def parse_answer(arguments: str) -> Answer:
    """Turn the JSON arguments of a submit_answer call into an Answer."""
    try:
        data = json.loads(arguments)
    except json.JSONDecodeError:
        raise AnswerError("submit_answer arguments are not valid JSON") from None
    if not isinstance(data, dict):
        raise AnswerError("submit_answer arguments must be a JSON object")

    values = {}
    for name in ANSWER_FIELDS:
        value = data.get(name)
        if not isinstance(value, str) or not value.strip():
            raise AnswerError(f"field '{name}' must be a non-empty string")
        values[name] = value.strip()
    return Answer(**values)

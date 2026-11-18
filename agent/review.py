"""Review mode: the final answer is two questions about the student's own fix.

Question 1: why the code failed before the fix. Question 2: why the fix looks
like this, compared with one concrete alternative. Exactly two: in runs 05 and
07 a third question was filler about made-up code (DECISIONS.md, D26).

The model ends the run by calling `submit_questions`. The questions are
public (they go into the PR comment), but the rules below are checked by code:
an invalid call is reported back to the model and uses the loop's one second
chance (loop.py; DECISIONS.md, D20).
"""

import json
from dataclasses import dataclass

from agent.answer import AnswerError
from agent.checks import count_sentences

QUESTION_COUNT = 2
MAX_QUESTION_CHARS = 400  # 300 was too short for a comparison with an alternative (run 06)
MAX_QUESTION_SENTENCES = 2  # e.g. one sentence of context, then the question

SUBMIT_QUESTIONS_SCHEMA = {
    "type": "function",
    "function": {
        "name": "submit_questions",
        "description": (
            "Submit your questions about the student's fix and end the review. "
            "Call it exactly once, after you have read the change."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "questions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": QUESTION_COUNT,
                    "maxItems": QUESTION_COUNT,
                    "description": (
                        "Exactly two questions about this specific change: first why the code failed "
                        "before the fix, then why the fix looks like this compared with one alternative; "
                        f"each at most {MAX_QUESTION_SENTENCES} sentences, the last one ending with '?', "
                        f"at most {MAX_QUESTION_CHARS} characters."
                    ),
                },
            },
            "required": ["questions"],
        },
    },
}


@dataclass(frozen=True)
class ReviewQuestions:
    questions: tuple[str, ...]


def parse_questions(arguments: str) -> ReviewQuestions:
    """Turn the JSON arguments of a submit_questions call into ReviewQuestions."""
    try:
        data = json.loads(arguments)
    except json.JSONDecodeError:
        raise AnswerError("submit_questions arguments are not valid JSON") from None
    if not isinstance(data, dict):
        raise AnswerError("submit_questions arguments must be a JSON object")

    questions = data.get("questions")
    if not isinstance(questions, list) or len(questions) != QUESTION_COUNT:
        raise AnswerError(f"field 'questions' must be a list of exactly {QUESTION_COUNT} strings")
    cleaned = []
    for number, question in enumerate(questions, start=1):
        if not isinstance(question, str) or not question.strip():
            raise AnswerError(f"question {number} must be a non-empty string")
        question = " ".join(question.split())  # one line each, so the numbered list stays intact
        if not question.endswith("?"):
            raise AnswerError(f"question {number} must end with '?'")
        if count_sentences(question) > MAX_QUESTION_SENTENCES:
            raise AnswerError(f"question {number} has more than {MAX_QUESTION_SENTENCES} sentences")
        if len(question) > MAX_QUESTION_CHARS:
            raise AnswerError(f"question {number} is longer than {MAX_QUESTION_CHARS} characters")
        cleaned.append(question)
    return ReviewQuestions(tuple(cleaned))

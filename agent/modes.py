"""The agent modes in one place (PLAN.md, section 3). The workflow picks the mode.

Each mode has its own prompt, its own read-only tools, its own final tool
that ends the run (it does not count towards the tool call limit) and its own
tool call limit.
"""

from collections.abc import Callable
from dataclasses import dataclass, replace

from agent.answer import SUBMIT_ANSWER_SCHEMA, parse_answer
from agent.review import SUBMIT_QUESTIONS_SCHEMA, parse_questions
from agent.threads import MAX_ATTEMPTS
from agent.tools import schemas_for
from agent.verdict import SUBMIT_VERDICT_SCHEMA, make_verdict_parser


@dataclass(frozen=True)
class Mode:
    name: str
    prompt: str                       # file in agent/prompts/
    tools: tuple[str, ...]            # investigation tools, all read-only
    submit_schema: dict               # the final tool that ends the run
    parse: Callable[[str], object]    # submit arguments -> answer; raises AnswerError
    max_tool_calls: int
    reminder: str                     # sent once if the model answers with plain text

    @property
    def submit_name(self) -> str:
        return self.submit_schema["function"]["name"]

    def all_schemas(self) -> list[dict]:
        return schemas_for(self.tools) + [self.submit_schema]


DEBUGGING = Mode(
    name="debugging",
    prompt="debugging.md",
    tools=("list_files", "read_file", "get_logs", "run_test"),
    submit_schema=SUBMIT_ANSWER_SCHEMA,
    parse=parse_answer,
    max_tool_calls=10,
    reminder=(
        "Do not answer with plain text. "
        "Call the submit_answer tool with diagnosis, hint_1, hint_2 and hint_3."
    ),
)

# The tests already passed: no logs and no test runs, only the code.
REVIEW = Mode(
    name="review",
    prompt="review.md",
    tools=("list_files", "read_file"),
    submit_schema=SUBMIT_QUESTIONS_SCHEMA,
    parse=parse_questions,
    max_tool_calls=10,
    reminder="Do not answer with plain text. Call the submit_questions tool with your questions.",
)

# The student answered the review questions. The diff is in the first message;
# read_file only to check a claim. 5 calls: answers are short (D28).
ANSWER = Mode(
    name="answer",
    prompt="answer.md",
    tools=("read_file",),
    submit_schema=SUBMIT_VERDICT_SCHEMA,
    parse=make_verdict_parser(last_attempt=False),
    max_tool_calls=5,
    reminder="Do not answer with plain text. Call the submit_verdict tool with understood, reply and reasoning.",
)


def answer_mode(attempt: int) -> Mode:
    """On the last attempt no follow-up question is required."""
    return replace(ANSWER, parse=make_verdict_parser(last_attempt=attempt >= MAX_ATTEMPTS))


MODES = {mode.name: mode for mode in (DEBUGGING, REVIEW, ANSWER)}

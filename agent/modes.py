"""The agent modes in one place (PLAN.md, section 3). The workflow picks the mode.

Each mode has its own prompt, its own read-only tools, its own final tool
that ends the run (it does not count towards the tool call limit) and its own
tool call limit.
"""

from collections.abc import Callable
from dataclasses import dataclass

from agent.answer import SUBMIT_ANSWER_SCHEMA, parse_answer
from agent.review import SUBMIT_QUESTIONS_SCHEMA, parse_questions
from agent.tools import schemas_for


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

MODES = {mode.name: mode for mode in (DEBUGGING, REVIEW)}

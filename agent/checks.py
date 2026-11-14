"""Code checks for the level 1 hint (see DECISIONS.md, D19).

Level 1 must be a nudge: no code names from the diagnosis and at most
MAX_SENTENCES_LEVEL_1 sentences. Only code-like tokens count as identifiers,
because plain English words such as "items" or "total" cannot be told apart
from normal text.
"""

import re
from dataclasses import dataclass, field

from agent.answer import Answer

# The single source of the level 1 length limit: the prompts must use this value.
MAX_SENTENCES_LEVEL_1 = 3

BACKTICKS = re.compile(r"`([^`\n]+)`")
# Code-like text inside backticks: Java-ish characters, no spaces or slashes.
CODE_CHARS = re.compile(r"[\w.@()\[\]<>,]+")
# Single words ("Order", "items"), acronyms ("HTTP") and numbers ("500") are not code names.
PLAIN_TOKEN = re.compile(r"[A-Za-z][a-z]*|[A-Z]+|\d+")

UPPER_CAMEL = re.compile(r"\b[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]*)+\b")  # CreateOrderRequest
LOWER_CAMEL = re.compile(r"\b[a-z]+[0-9]*(?:[A-Z][a-z0-9]*)+\b")  # createOrder
CALL = re.compile(r"\b[A-Za-z_]\w*\([^()\n]*\)")  # get(int), isEmpty()
EXCEPTION = re.compile(r"\b[A-Za-z]+Exception\b")  # IndexOutOfBoundsException
ANNOTATION = re.compile(r"(?<!\w)@[A-Za-z]\w*")  # @NotEmpty

ABBREVIATION = re.compile(r"\b(?:e\.g|i\.e|etc|vs|cf)\.", re.IGNORECASE)
SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def code_identifiers(text: str) -> set[str]:
    """Code-like tokens in a text (usually the diagnosis)."""
    found: set[str] = set()
    for content in BACKTICKS.findall(text):
        content = content.strip()
        if CODE_CHARS.fullmatch(content) and not PLAIN_TOKEN.fullmatch(content):
            found.add(content)
    for pattern in (UPPER_CAMEL, LOWER_CAMEL, CALL, EXCEPTION, ANNOTATION):
        found.update(pattern.findall(text))
    return found


def leak_pattern(identifier: str) -> re.Pattern[str]:
    """How an identifier is searched for in a hint (case-insensitive, whole words)."""
    call = re.search(r"(\w+)\s*\(", identifier)
    if call:
        # A call matches by method name with any arguments: get(0) also finds get(int).
        return re.compile(rf"(?<!\w){re.escape(call.group(1))}\s*\(", re.IGNORECASE)
    return re.compile(rf"(?<!\w){re.escape(identifier)}(?!\w)", re.IGNORECASE)


def find_leaks(hint: str, identifiers: set[str]) -> list[str]:
    """Identifiers that appear in the hint, sorted."""
    return sorted(name for name in identifiers if leak_pattern(name).search(hint))


def count_sentences(text: str) -> int:
    """Sentences end with . ! or ? followed by a space or the end of the text.

    Dots inside numbers (1.5) and file names (OrderService.java) are not
    followed by a space; common abbreviations (e.g., i.e., etc.) are masked.
    """
    masked = ABBREVIATION.sub("ABBR", text.strip())
    return len([part for part in SENTENCE_END.split(masked) if part.strip()])


@dataclass
class HintCheck:
    leaks: list[str] = field(default_factory=list)
    sentences: int = 0

    @property
    def ok(self) -> bool:
        return not self.reasons()

    def reasons(self) -> list[str]:
        """Why the check failed. Safe for logs: never contains identifiers (D18)."""
        reasons = []
        if self.leaks:
            reasons.append("leaks_identifiers")
        if self.sentences > MAX_SENTENCES_LEVEL_1:
            reasons.append("too_long")
        return reasons


def check_hint_1(answer: Answer) -> HintCheck:
    return HintCheck(
        leaks=find_leaks(answer.hint_1, code_identifiers(answer.diagnosis)),
        sentences=count_sentences(answer.hint_1),
    )

"""Code checks for the hints of every level (see DECISIONS.md, D19, D22, D23).

- Level 1, a nudge: no code names from the diagnosis (D19).
- Level 2, the location: code names are allowed, but no sentence may name
  code from the diagnosis together with an action word ("add", "missing",
  "no constraint", ...), because that says what to change (D22).
- Level 3, the concept: no annotation and no method call names (D23).
- Every level: at most MAX_SENTENCES[level] sentences.

Only code-like tokens count as identifiers, because plain English words such
as "items" or "total" cannot be told apart from normal text.
"""

import re
from dataclasses import dataclass, field

from agent.answer import Answer

# The single source of the length limits: the prompts must use these values.
MAX_SENTENCES = {1: 3, 2: 5, 3: 6}

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
HIDDEN_DOT = "\x00"  # never appears in model text

# Level 2: words that say what to change or what is missing (whole words, any case).
ACTION_WORDS = re.compile(
    r"\b(?:add|adding|should|must|need to|needs to|replace|use|change|put|annotate|remove"
    r"|missing|lacks?|lacking|without"
    r"|no (?:constraints?|validations?|checks?|annotations?|rules?)"
    r"|nothing (?:rejects|checks|validates))\b",
    re.IGNORECASE,
)


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


def annotations_and_calls(text: str) -> set[str]:
    """Level 3 identifiers: only annotations (@NotEmpty) and method calls (get(int))."""
    return set(ANNOTATION.findall(text)) | set(CALL.findall(text))


def split_sentences(text: str) -> list[str]:
    """Sentences end with . ! or ? followed by a space or the end of the text.

    Dots inside numbers (1.5) and file names (OrderService.java) are not
    followed by a space. The dots of common abbreviations (e.g., i.e., etc.)
    are hidden while splitting and put back afterwards.
    """
    hidden = ABBREVIATION.sub(lambda match: match.group().replace(".", HIDDEN_DOT), text.strip())
    parts = SENTENCE_END.split(hidden)
    return [part.replace(HIDDEN_DOT, ".") for part in parts if part.strip()]


def count_sentences(text: str) -> int:
    return len(split_sentences(text))


def count_action_sentences(hint: str, identifiers: set[str]) -> int:
    """Sentences that name code from the diagnosis and also say what to change (level 2)."""
    return sum(
        1 for sentence in split_sentences(hint) if find_leaks(sentence, identifiers) and ACTION_WORDS.search(sentence)
    )


@dataclass
class HintCheck:
    level: int
    leaks: list[str] = field(default_factory=list)
    action_sentences: int = 0
    sentences: int = 0

    @property
    def ok(self) -> bool:
        return not self.reasons()

    def reasons(self) -> list[str]:
        """Why the check failed. Safe for logs: never contains identifiers (D18)."""
        reasons = []
        if self.leaks:
            reasons.append("leaks_identifiers")
        if self.action_sentences:
            reasons.append("gives_action")
        if self.sentences > MAX_SENTENCES[self.level]:
            reasons.append("too_long")
        return reasons


def check_hint(answer: Answer, level: int) -> HintCheck:
    if level not in MAX_SENTENCES:
        raise ValueError(f"unknown hint level: {level}")
    hint = answer.hint(level)
    result = HintCheck(level=level, sentences=count_sentences(hint))
    if level == 1:
        result.leaks = find_leaks(hint, code_identifiers(answer.diagnosis))
    elif level == 2:
        result.action_sentences = count_action_sentences(hint, code_identifiers(answer.diagnosis))
    else:
        # Any annotation counts: the annotation of the fix is often not in the diagnosis.
        forbidden = annotations_and_calls(answer.diagnosis) | set(ANNOTATION.findall(hint))
        result.leaks = find_leaks(hint, forbidden)
    return result

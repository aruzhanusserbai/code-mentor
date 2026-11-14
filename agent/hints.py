"""Pick the hint of the selected level and check it by code.

Every level is checked (checks.py; DECISIONS.md, D19, D22, D23). If the hint
fails, it is regenerated once with one model request and no tools; if it
still fails, a general fallback hint of that level is used. Code blocks are
removed from every hint by comment.py.

Logs contain only the status and reason codes, never the answer (D18).
"""

import logging
from dataclasses import dataclass, field, replace

from agent.answer import Answer
from agent.checks import MAX_SENTENCES, HintCheck, check_hint
from agent.llm import LLMClient

# General hints, not about a specific bug: they must fit every ticket.
FALLBACK_HINTS = {
    1: (
        "Start from the failing test output: compare the expected and the actual response. "
        "Then find the first error in the service log and follow that request through the code, "
        "layer by layer. Where does the behaviour start to differ from what the ticket asks for?"
    ),
    2: (
        "Find the first error in the service log and read its stack trace from the top. "
        "The first lines that point into this project's own code show the file and the method "
        "where the failing request breaks. Open that method and follow what happens to the data "
        "from the failing test, line by line."
    ),
    3: (
        "Re-read the expected behaviour in the ticket and put into one sentence the rule that the "
        "code breaks now. Then decide which layer is responsible for that rule: the incoming request, "
        "the business logic or the error handling. Look at how the project already handles similar "
        "rules elsewhere and follow the same approach."
    ),
}

# What the regenerated hint must look like, per level (repeated from the prompts on purpose).
REWRITE_RULES = {
    1: "no class, method, field, exception or annotation names",
    2: "you may name the file, class, method and exception, but do not say what to change or what is missing",
    3: "explain the idea of the fix, but no annotation or method names and no code",
}

log = logging.getLogger("codementor")


@dataclass
class HintResult:
    text: str
    status: str  # "ok", "regenerated" or "fallback"
    requests: int = 0  # model requests made here (0 or 1)
    reasons: list[str] = field(default_factory=list)  # why the hint failed the first check


def regenerate_message(answer: Answer, level: int, check: HintCheck) -> str:
    problems = []
    if check.leaks:
        problems.append("It names code it must not name: " + ", ".join(check.leaks) + ".")
    if check.action_sentences:
        problems.append("It says what to change or what is missing, next to code names.")
    if "too_long" in check.reasons():
        problems.append(f"It has {check.sentences} sentences.")
    return "\n\n".join([
        f"<diagnosis>\n{answer.diagnosis}\n</diagnosis>",
        f"<rejected_hint>\n{answer.hint(level)}\n</rejected_hint>",
        f"The rejected level {level} hint breaks the rules. " + " ".join(problems),
        f"Write a new level {level} hint: at most {MAX_SENTENCES[level]} sentences, "
        f"{REWRITE_RULES[level]}. Reply with the hint text only.",
    ])


def regenerate_hint(answer: Answer, level: int, check: HintCheck, llm: LLMClient, prompt: str) -> str:
    """One request, no tools. Returns "" if the model fails or answers nothing."""
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": regenerate_message(answer, level, check)},
    ]
    try:
        reply = llm.chat(messages, None)
    except Exception as error:  # API errors, rate limits: use the fallback
        log.warning("hint_%d regeneration failed: %s", level, type(error).__name__)
        return ""
    return (reply.content or "").strip()


def select_hint(answer: Answer, level: int, llm: LLMClient, regenerate_prompt: str) -> HintResult:
    check = check_hint(answer, level)  # raises ValueError for an unknown level
    if check.ok:
        return HintResult(text=answer.hint(level), status="ok")

    reasons = check.reasons()
    new_hint = regenerate_hint(answer, level, check, llm, regenerate_prompt)
    if new_hint and check_hint(replace(answer, **{f"hint_{level}": new_hint}), level).ok:
        result = HintResult(text=new_hint, status="regenerated", requests=1, reasons=reasons)
    else:
        result = HintResult(text=FALLBACK_HINTS[level], status="fallback", requests=1, reasons=reasons)
    log.info("hint_%d %s (first check: %s)", level, result.status, ", ".join(reasons))
    return result

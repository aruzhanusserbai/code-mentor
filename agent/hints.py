"""Pick the hint of the selected level; make sure level 1 is really a nudge.

Level 1 is checked by code (checks.py). If it fails, it is regenerated once
with one model request and no tools; if it still fails, a general fallback
hint is used (see DECISIONS.md, D19). Levels 2 and 3 are not checked here;
code blocks are removed from every hint by comment.py.

Logs contain only the status and reason codes, never the answer (D18).
"""

import logging
from dataclasses import dataclass, field, replace

from agent.answer import Answer
from agent.checks import MAX_SENTENCES_LEVEL_1, HintCheck, check_hint_1
from agent.llm import LLMClient

FALLBACK_HINT_1 = (
    "Start from the failing test output: compare the expected and the actual response. "
    "Then find the first error in the service log and follow that request through the code, "
    "layer by layer. Where does the behaviour start to differ from what the ticket asks for?"
)

log = logging.getLogger("codementor")


@dataclass
class HintResult:
    text: str
    status: str  # "ok", "regenerated" or "fallback"
    requests: int = 0  # model requests made here (0 or 1)
    reasons: list[str] = field(default_factory=list)  # why level 1 failed the first check


def regenerate_message(answer: Answer, check: HintCheck) -> str:
    problems = []
    if check.leaks:
        problems.append("It names code from the diagnosis: " + ", ".join(check.leaks) + ".")
    if "too_long" in check.reasons():
        problems.append(f"It has {check.sentences} sentences.")
    return "\n\n".join([
        f"<diagnosis>\n{answer.diagnosis}\n</diagnosis>",
        f"<rejected_hint>\n{answer.hint_1}\n</rejected_hint>",
        "The rejected level 1 hint breaks the rules. " + " ".join(problems),
        f"Write a new level 1 hint: at most {MAX_SENTENCES_LEVEL_1} sentences, "
        "no class, method, field, exception or annotation names. Reply with the hint text only.",
    ])


def regenerate_hint_1(answer: Answer, check: HintCheck, llm: LLMClient, prompt: str) -> str:
    """One request, no tools. Returns "" if the model fails or answers nothing."""
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": regenerate_message(answer, check)},
    ]
    try:
        reply = llm.chat(messages, None)
    except Exception as error:  # API errors, rate limits: use the fallback
        log.warning("hint_1 regeneration failed: %s", type(error).__name__)
        return ""
    return (reply.content or "").strip()


def select_hint(answer: Answer, level: int, llm: LLMClient, regenerate_prompt: str) -> HintResult:
    if level != 1:
        return HintResult(text=answer.hint(level), status="ok")

    check = check_hint_1(answer)
    if check.ok:
        return HintResult(text=answer.hint_1, status="ok")

    reasons = check.reasons()
    new_hint = regenerate_hint_1(answer, check, llm, regenerate_prompt)
    if new_hint and check_hint_1(replace(answer, hint_1=new_hint)).ok:
        result = HintResult(text=new_hint, status="regenerated", requests=1, reasons=reasons)
    else:
        result = HintResult(text=FALLBACK_HINT_1, status="fallback", requests=1, reasons=reasons)
    log.info("hint_1 %s (first check: %s)", result.status, ", ".join(reasons))
    return result

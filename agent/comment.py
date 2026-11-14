"""Build the PR comment from the hint of the selected level.

The hidden marker is written here, by code, so the model cannot change the
mode or the hint level (see DECISIONS.md, D14).
"""

import re

CODE_BLOCK = re.compile(r"```.*?(```|$)", re.DOTALL)
CODE_REMOVED_NOTE = "_(A code snippet was removed: the mentor gives hints, not solutions.)_"
GENERAL_HINT_NOTE = "_(This time the hint is a general one. The next failed attempt gets a more specific hint.)_"
# Level 3 is the last one: there is no automatic full answer (DECISIONS.md, D24).
LAST_LEVEL = 3
LAST_LEVEL_GENERAL_NOTE = (
    "_(This is a general hint. If you’re still stuck, check the ‘Useful reading’ link in the ticket, "
    "or ask in the student chat — someone may have hit the same thing.)_"
)


def marker(ticket: int, mode: str, level: int) -> str:
    return f"<!-- codementor:ticket={ticket};mode={mode};level={level} -->"


def remove_code_blocks(text: str) -> tuple[str, bool]:
    """Remove fenced code blocks (also an unclosed one at the end)."""
    cleaned, count = CODE_BLOCK.subn(CODE_REMOVED_NOTE, text)
    return cleaned.strip(), count > 0


def remove_html_comments(text: str) -> str:
    """The model must not add its own hidden markers."""
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL).strip()


def build_debugging_comment(ticket: int, level: int, hint: str, run_url: str | None, general: bool = False) -> str:
    """`general` marks the fallback hint used when the hint failed the checks (hints.py)."""
    hint, _ = remove_code_blocks(remove_html_comments(hint))
    lines = [
        marker(ticket, "debugging", level),
        f"### CodeMentor: hint for ticket {ticket} (level {level})",
        "",
        "Some ticket tests failed. Here is a hint from your mentor:",
        "",
        hint,
        "",
    ]
    if general:
        lines += [LAST_LEVEL_GENERAL_NOTE if level >= LAST_LEVEL else GENERAL_HINT_NOTE, ""]
    lines += ["Push a new commit to try again."]
    if run_url:
        lines += ["", f"Full test output and service logs: [workflow run]({run_url})."]
    return "\n".join(lines) + "\n"

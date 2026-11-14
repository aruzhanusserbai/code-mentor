"""Build the PR comment from the hint of the selected level.

The hidden marker is written here, by code, so the model cannot change the
mode or the hint level (see DECISIONS.md, D14).
"""

import re

CODE_BLOCK = re.compile(r"```.*?(```|$)", re.DOTALL)
CODE_REMOVED_NOTE = "_(A code snippet was removed: the mentor gives hints, not solutions.)_"
GENERAL_HINT_NOTE = "_(This time the hint is a general one. The next failed attempt gets a more specific hint.)_"


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
    """`general` marks the fallback hint used when level 1 failed the checks (hints.py)."""
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
        lines += [GENERAL_HINT_NOTE, ""]
    lines += ["Push a new commit to try again."]
    if run_url:
        lines += ["", f"Full test output and service logs: [workflow run]({run_url})."]
    return "\n".join(lines) + "\n"

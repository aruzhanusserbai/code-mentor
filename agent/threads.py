"""Answer mode: read the PR comments and decide whether the agent should run.

The workflow downloads the PR comments with `gh api --paginate` and runs

    python -m agent.threads --comments comments.json --author <PR author login>

which prints `key=value` lines for $GITHUB_OUTPUT: `action=run` or
`action=skip`, the reason, the ticket, the reviewed commit and the attempt.

Only comments of the workflow bot count as markers (as in levels.py): a
student can quote a review or type a marker by hand, and that must never
start or finish a review. The attempt limit keeps the free model budget safe
(DECISIONS.md, D28).
"""

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from agent.levels import LevelsError, is_bot_comment, parse_pages

MAX_ATTEMPTS = 3
MARKER = re.compile(r"<!-- codementor:ticket=(\d+);mode=([a-z]+);([^>]*?) -->")
QUESTION_LINE = re.compile(r"^\d+\. (.+)$", re.MULTILINE)


@dataclass
class Message:
    author: str  # "mentor" or "student"
    body: str


@dataclass
class Decision:
    action: str                 # "run" or "skip"
    reason: str
    ticket: int | None = None
    sha: str | None = None
    attempt: int | None = None  # 1..MAX_ATTEMPTS when action is "run"
    questions: list[str] = field(default_factory=list)
    conversation: list[Message] = field(default_factory=list)  # after the review, oldest first


def read_marker(comment: dict) -> tuple[int, str, dict[str, str]] | None:
    """(ticket, mode, fields) of a bot comment that starts with a marker, else None."""
    if not is_bot_comment(comment):
        return None
    match = MARKER.match((comment.get("body") or "").lstrip())
    if not match:
        return None
    fields = dict(part.split("=", 1) for part in match.group(3).split(";") if "=" in part)
    return int(match.group(1)), match.group(2), fields


def body_without_marker(comment: dict) -> str:
    return MARKER.sub("", comment.get("body") or "", count=1).strip()


def is_from(comment: dict, login: str) -> bool:
    user = comment.get("user") or {}
    return user.get("login") == login and user.get("type") != "Bot"


def decide(comments: list[dict], author: str) -> Decision:
    """Comments in API order (oldest first). `author` is the PR author's login."""
    review_index = None
    for index, comment in enumerate(comments):
        marker = read_marker(comment)
        if marker and marker[1] == "review":
            review_index = index
    if review_index is None:
        return Decision("skip", "no_review")

    ticket, _, fields = read_marker(comments[review_index])
    sha = fields.get("sha", "")
    questions = QUESTION_LINE.findall(body_without_marker(comments[review_index]))

    attempts = 0
    conversation = []
    for comment in comments[review_index + 1:]:
        marker = read_marker(comment)
        if marker and marker[0] == ticket and marker[1] == "answer":
            attempts += 1
            if marker[2].get("result") in ("done", "closed"):
                return Decision("skip", f"review_{marker[2]['result']}", ticket, sha)
            conversation.append(Message("mentor", body_without_marker(comment)))
        elif is_from(comment, author):
            conversation.append(Message("student", comment.get("body") or ""))

    if attempts >= MAX_ATTEMPTS:
        return Decision("skip", "no_attempts_left", ticket, sha)
    if not conversation or conversation[-1].author != "student":
        return Decision("skip", "no_new_answer", ticket, sha)
    return Decision("run", "answer", ticket, sha, attempts + 1, questions, conversation)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Decide whether CodeMentor answer mode should run")
    parser.add_argument("--comments", type=Path, required=True, help="output of gh api --paginate .../comments")
    parser.add_argument("--author", required=True, help="login of the PR author")
    args = parser.parse_args(argv)

    try:
        comments = parse_pages(args.comments.read_text(encoding="utf-8"))
    except (OSError, LevelsError) as error:
        print(f"cannot read PR comments: {error}", file=sys.stderr)
        return 1
    decision = decide(comments, args.author)
    print(f"action={decision.action}")
    print(f"reason={decision.reason}")
    print(f"ticket={decision.ticket or ''}")
    print(f"sha={decision.sha or ''}")
    print(f"attempt={decision.attempt or ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

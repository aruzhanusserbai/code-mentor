"""Pick the next hint level from the earlier PR comments (see DECISIONS.md, D17).

The workflow downloads the PR comments with `gh api --paginate` and runs

    python -m agent.levels --ticket 1 --comments comments.json

which prints the level (1-3). Only comments written by the workflow bot
count: a student can quote an old hint or type a marker by hand, and that
must never raise the level.
"""

import argparse
import json
import re
import sys
from pathlib import Path

BOT_LOGIN = "github-actions[bot]"
BOT_TYPE = "Bot"
MAX_LEVEL = 3


class LevelsError(ValueError):
    """The comments file is not what the GitHub API returns."""


def parse_pages(text: str) -> list[dict]:
    """Read `gh api --paginate` output: one JSON array per page, or one array of pages (--slurp)."""
    decoder = json.JSONDecoder()
    pages = []
    position = 0
    while True:
        while position < len(text) and text[position].isspace():
            position += 1
        if position == len(text):
            break
        try:
            value, position = decoder.raw_decode(text, position)
        except json.JSONDecodeError:
            raise LevelsError("comments are not valid JSON") from None
        if not isinstance(value, list):
            raise LevelsError("comments must be JSON arrays (an API error message?)")
        pages.append(value)

    comments = []
    for page in pages:
        for item in page:
            comments.extend(item if isinstance(item, list) else [item])  # --slurp: pages inside
    if not all(isinstance(item, dict) for item in comments):
        raise LevelsError("every comment must be a JSON object")
    return comments


def is_bot_comment(comment: dict) -> bool:
    user = comment.get("user") or {}  # null for deleted accounts
    return user.get("login") == BOT_LOGIN and user.get("type") == BOT_TYPE


def is_debugging_hint(comment: dict, ticket: int) -> bool:
    """The marker must start the comment, as comment.py writes it."""
    marker = re.compile(rf"<!-- codementor:ticket={ticket};mode=debugging;level=\d+ -->")
    return bool(marker.match((comment.get("body") or "").lstrip()))


def next_level(comments: list[dict], ticket: int) -> int:
    earlier_hints = sum(1 for c in comments if is_bot_comment(c) and is_debugging_hint(c, ticket))
    return min(earlier_hints + 1, MAX_LEVEL)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Print the next CodeMentor hint level for a PR")
    parser.add_argument("--ticket", type=int, required=True)
    parser.add_argument("--comments", type=Path, required=True, help="output of gh api --paginate .../comments")
    args = parser.parse_args(argv)

    try:
        comments = parse_pages(args.comments.read_text(encoding="utf-8"))
    except (OSError, LevelsError) as error:
        print(f"cannot read PR comments: {error}", file=sys.stderr)
        return 1
    print(next_level(comments, args.ticket))
    return 0


if __name__ == "__main__":
    sys.exit(main())

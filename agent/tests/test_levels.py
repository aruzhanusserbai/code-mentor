import json
from pathlib import Path

import pytest

from agent.levels import MAX_LEVEL, LevelsError, main, next_level, parse_pages

BOT = {"login": "github-actions[bot]", "type": "Bot"}
STUDENT = {"login": "student", "type": "User"}


def marker(ticket: int = 1, mode: str = "debugging", level: int = 1) -> str:
    return f"<!-- codementor:ticket={ticket};mode={mode};level={level} -->"


def comment(user: dict | None, body: str) -> dict:
    return {"user": user, "body": body}


def bot_hint(ticket: int = 1, level: int = 1) -> dict:
    return comment(BOT, f"{marker(ticket, 'debugging', level)}\n### CodeMentor: hint for ticket {ticket}\n")


# --- next_level ---------------------------------------------------------------


def test_no_comments_gives_level_1() -> None:
    assert next_level([], ticket=1) == 1


def test_no_bot_comments_gives_level_1() -> None:
    comments = [comment(STUDENT, "I pushed a fix"), comment({"login": "reviewer", "type": "User"}, "LGTM")]

    assert next_level(comments, ticket=1) == 1


@pytest.mark.parametrize(("hints", "expected"), [(1, 2), (2, 3), (3, 3), (5, 3)])
def test_level_grows_with_bot_hints_and_stops_at_3(hints: int, expected: int) -> None:
    comments = [bot_hint(level=min(index + 1, MAX_LEVEL)) for index in range(hints)]

    assert next_level(comments, ticket=1) == expected


def test_student_quoting_a_bot_hint_is_not_counted() -> None:
    quote = comment(STUDENT, f"> {marker()}\n> ### CodeMentor: hint for ticket 1\n\nWhat does this mean?")

    assert next_level([bot_hint(), quote], ticket=1) == 2


def test_student_writing_a_fake_marker_is_not_counted() -> None:
    fakes = [comment(STUDENT, marker(level=level)) for level in (1, 2, 3)]

    assert next_level(fakes, ticket=1) == 1


def test_comment_needs_both_bot_login_and_bot_type() -> None:
    other_bot = comment({"login": "dependabot[bot]", "type": "Bot"}, marker())
    not_a_bot = comment({"login": "github-actions[bot]", "type": "User"}, marker())

    assert next_level([other_bot, not_a_bot], ticket=1) == 1


def test_deleted_user_is_skipped() -> None:
    # The API returns "user": null for comments of deleted accounts.
    assert next_level([comment(None, marker())], ticket=1) == 1


def test_only_debugging_hints_of_the_same_ticket_count() -> None:
    comments = [
        comment(BOT, "<!-- codementor:ticket=1;mode=check;result=failed -->\nTests failed."),
        bot_hint(ticket=2),
        bot_hint(ticket=11),
        bot_hint(ticket=1),
    ]

    assert next_level(comments, ticket=1) == 2


def test_marker_must_start_the_bot_comment() -> None:
    # comment.py writes the marker on the first line; anything else is not ours.
    late = comment(BOT, f"Tests failed.\n{marker()}")

    assert next_level([late], ticket=1) == 1


def test_leading_whitespace_before_the_marker_is_allowed() -> None:
    assert next_level([comment(BOT, f"\n  {marker()}\nhint")], ticket=1) == 2


# --- parse_pages: output of `gh api --paginate` -------------------------------


def test_one_page() -> None:
    assert parse_pages(json.dumps([bot_hint()])) == [bot_hint()]


def test_pages_are_concatenated_arrays() -> None:
    # Without --slurp, gh prints one JSON array per page, back to back.
    page_1 = json.dumps([bot_hint(), comment(STUDENT, "hi")])
    page_2 = json.dumps([bot_hint(level=2)])

    assert parse_pages(page_1 + page_2) == [bot_hint(), comment(STUDENT, "hi"), bot_hint(level=2)]
    assert len(parse_pages(page_1 + "\n" + page_2 + "\n")) == 3


def test_slurped_pages_are_flattened() -> None:
    # With --slurp, gh wraps the pages into one array of arrays.
    text = json.dumps([[bot_hint()], [bot_hint(level=2), comment(STUDENT, "hi")]])

    assert len(parse_pages(text)) == 3


@pytest.mark.parametrize("text", ["", "  \n", "[]", "[][]"])
def test_empty_output_has_no_comments(text: str) -> None:
    assert parse_pages(text) == []


@pytest.mark.parametrize("text", ["[{]", '{"message": "Not Found"}', '[1, "x"]'])
def test_invalid_output_is_an_error(text: str) -> None:
    with pytest.raises(LevelsError):
        parse_pages(text)


def test_bot_hints_on_different_pages_are_all_counted() -> None:
    page_1 = [bot_hint()] + [comment(STUDENT, f"comment {n}") for n in range(29)]
    page_2 = [bot_hint(level=2)]

    comments = parse_pages(json.dumps(page_1) + json.dumps(page_2))

    assert next_level(comments, ticket=1) == 3


# --- command line -------------------------------------------------------------


def test_cli_prints_the_level(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    comments_file = tmp_path / "comments.json"
    comments_file.write_text(json.dumps([bot_hint()]) + json.dumps([comment(STUDENT, marker())]), encoding="utf-8")

    code = main(["--ticket", "1", "--comments", str(comments_file)])

    assert code == 0
    assert capsys.readouterr().out == "2\n"


def test_cli_reports_invalid_input(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    comments_file = tmp_path / "comments.json"
    comments_file.write_text('{"message": "Bad credentials"}', encoding="utf-8")

    code = main(["--ticket", "1", "--comments", str(comments_file)])

    captured = capsys.readouterr()
    assert code == 1
    assert captured.out == ""
    assert "comments" in captured.err

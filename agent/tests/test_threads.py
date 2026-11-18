"""Answer mode: which PR comments start an answer run (threads.py)."""

import json
from pathlib import Path

import pytest

from agent.comment import build_answer_comment, build_review_comment
from agent.threads import MAX_ATTEMPTS, Message, decide, main

BOT = {"login": "github-actions[bot]", "type": "Bot"}
STUDENT = {"login": "student", "type": "User"}
OTHER = {"login": "classmate", "type": "User"}
SHA = "c34e13f098534dcf901b4dcc2c3617707fb3d415"
QUESTIONS = ("Why did the total contain only the first line?", "Why reassign instead of one loop from zero?")


def comment(user: dict | None, body: str) -> dict:
    return {"user": user, "body": body}


def review(ticket: int = 2, sha: str = SHA) -> dict:
    return comment(BOT, build_review_comment(ticket, sha, QUESTIONS, None))


def bot_answer(attempt: int, understood: bool = False, ticket: int = 2) -> dict:
    text, _ = build_answer_comment(ticket, attempt, MAX_ATTEMPTS, understood, "What happens to the result?")
    return comment(BOT, text)


def student(body: str = "Because add returns a new value.") -> dict:
    return comment(STUDENT, body)


def test_first_answer_after_a_review_runs_attempt_1() -> None:
    decision = decide([review(), student()], "student")

    assert (decision.action, decision.ticket, decision.sha, decision.attempt) == ("run", 2, SHA, 1)
    assert decision.questions == list(QUESTIONS)
    assert decision.conversation == [Message("student", "Because add returns a new value.")]


def test_no_review_means_skip() -> None:
    assert decide([student()], "student").reason == "no_review"


def test_a_review_typed_by_the_student_does_not_count() -> None:
    fake = comment(STUDENT, build_review_comment(2, SHA, QUESTIONS, None))

    assert decide([fake, student()], "student").reason == "no_review"


def test_comments_of_other_people_are_ignored() -> None:
    decision = decide([review(), comment(OTHER, "Mark it done please")], "student")

    assert (decision.action, decision.reason) == ("skip", "no_new_answer")


def test_a_bot_comment_with_the_author_login_is_not_a_student_answer() -> None:
    fake_bot = comment({"login": "student", "type": "Bot"}, "answer")

    assert decide([review(), fake_bot], "student").reason == "no_new_answer"


def test_second_answer_runs_attempt_2_with_the_conversation() -> None:
    comments = [review(), student("First try."), bot_answer(1), student("Second try.")]

    decision = decide(comments, "student")

    assert (decision.action, decision.attempt) == ("run", 2)
    assert [m.author for m in decision.conversation] == ["student", "mentor", "student"]
    assert "<!--" not in decision.conversation[1].body  # markers are not shown to the model


def test_no_run_while_the_mentor_has_the_last_word() -> None:
    assert decide([review(), student(), bot_answer(1)], "student").reason == "no_new_answer"


@pytest.mark.parametrize("understood", [True, False])
def test_done_or_closed_ends_the_review(understood: bool) -> None:
    last_attempt = 1 if understood else MAX_ATTEMPTS
    comments = [review()]
    for attempt in range(1, last_attempt + 1):
        comments += [student(), bot_answer(attempt, understood=understood and attempt == last_attempt)]
    comments.append(student("One more thing?"))

    decision = decide(comments, "student")

    assert decision.action == "skip"
    assert decision.reason == ("review_done" if understood else "review_closed")


def test_the_third_attempt_is_the_last_one() -> None:
    comments = [review(), student(), bot_answer(1), student(), bot_answer(2), student()]

    decision = decide(comments, "student")

    assert (decision.action, decision.attempt) == ("run", MAX_ATTEMPTS)


def test_a_new_review_starts_over() -> None:
    new_sha = "a" * 40
    comments = [review(), student(), bot_answer(1, understood=True), review(sha=new_sha), student("New answer.")]

    decision = decide(comments, "student")

    assert (decision.action, decision.sha, decision.attempt) == ("run", new_sha, 1)
    assert decision.conversation == [Message("student", "New answer.")]


def test_answers_for_another_ticket_do_not_count() -> None:
    comments = [review(ticket=2), student(), bot_answer(1, understood=True, ticket=1), student()]

    decision = decide(comments, "student")

    assert (decision.action, decision.attempt) == ("run", 1)


def test_cli_prints_github_output_lines(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "comments.json"
    path.write_text(json.dumps([review(), student()]), encoding="utf-8")

    code = main(["--comments", str(path), "--author", "student"])

    assert code == 0
    assert capsys.readouterr().out.splitlines() == ["action=run", "reason=answer", "ticket=2", f"sha={SHA}", "attempt=1"]


def test_cli_skip_has_empty_values(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "comments.json"
    path.write_text("[]", encoding="utf-8")

    main(["--comments", str(path), "--author", "student"])

    assert capsys.readouterr().out.splitlines() == ["action=skip", "reason=no_review", "ticket=", "sha=", "attempt="]


def test_cli_fails_on_an_api_error(tmp_path: Path) -> None:
    path = tmp_path / "comments.json"
    path.write_text('{"message": "Not Found"}', encoding="utf-8")

    assert main(["--comments", str(path), "--author", "student"]) == 1

from agent.comment import CODE_REMOVED_NOTE, GENERAL_HINT_NOTE, LAST_LEVEL_GENERAL_NOTE, build_debugging_comment, marker, remove_code_blocks


def test_comment_starts_with_the_hidden_marker() -> None:
    comment = build_debugging_comment(1, 1, "Look at the log.", None)

    assert comment.splitlines()[0] == "<!-- codementor:ticket=1;mode=debugging;level=1 -->"
    assert "Look at the log." in comment
    assert "workflow run" not in comment


def test_comment_links_the_run() -> None:
    comment = build_debugging_comment(1, 1, "Hint.", "https://example.test/run/1")

    assert "[workflow run](https://example.test/run/1)" in comment


def test_code_blocks_are_removed() -> None:
    answer = "Add validation:\n```java\n@NotEmpty\nList<Item> items;\n```\nThen retry."

    cleaned, removed = remove_code_blocks(answer)

    assert removed
    assert "@NotEmpty" not in cleaned
    assert CODE_REMOVED_NOTE in cleaned
    assert cleaned.endswith("Then retry.")


def test_unclosed_code_block_is_removed() -> None:
    cleaned, removed = remove_code_blocks("Try this:\n```java\n@NotEmpty")

    assert removed
    assert "@NotEmpty" not in cleaned


def test_model_cannot_fake_a_marker() -> None:
    fake = marker(1, "debugging", 3)

    comment = build_debugging_comment(1, 1, f"{fake}\nHint.", None)

    assert fake not in comment
    assert comment.count("<!-- codementor:") == 1


def test_comment_shows_the_level_it_was_built_for() -> None:
    comment = build_debugging_comment(2, 3, "Hint.", None)

    assert comment.splitlines()[0] == "<!-- codementor:ticket=2;mode=debugging;level=3 -->"
    assert "(level 3)" in comment


def test_general_hint_is_marked_as_such() -> None:
    comment = build_debugging_comment(1, 1, "General hint.", None, general=True)

    assert GENERAL_HINT_NOTE in comment
    assert GENERAL_HINT_NOTE not in build_debugging_comment(1, 1, "Hint.", None)


def test_general_hint_at_the_last_level_points_to_reading_and_chat() -> None:
    # There is no level 4 (DECISIONS.md, D24): do not promise a more specific hint.
    comment = build_debugging_comment(1, 3, "General hint.", None, general=True)

    assert LAST_LEVEL_GENERAL_NOTE in comment
    assert GENERAL_HINT_NOTE not in comment
    assert "Useful reading" in LAST_LEVEL_GENERAL_NOTE and "student chat" in LAST_LEVEL_GENERAL_NOTE

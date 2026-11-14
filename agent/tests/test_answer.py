import json

import pytest

from agent.answer import ANSWER_FIELDS, SUBMIT_ANSWER_SCHEMA, Answer, AnswerError, parse_answer

VALID = {
    "diagnosis": "SECRET-DIAGNOSIS",
    "hint_1": "Look at the status code.",
    "hint_2": "SECRET-HINT-2",
    "hint_3": "SECRET-HINT-3",
}


def test_valid_arguments_are_parsed() -> None:
    answer = parse_answer(json.dumps(VALID))

    assert answer == Answer(
        diagnosis="SECRET-DIAGNOSIS",
        hint_1="Look at the status code.",
        hint_2="SECRET-HINT-2",
        hint_3="SECRET-HINT-3",
    )


def test_values_are_stripped() -> None:
    answer = parse_answer(json.dumps({**VALID, "hint_1": "  Look at the log.\n"}))

    assert answer.hint_1 == "Look at the log."


def test_hint_returns_the_hint_of_the_level() -> None:
    answer = parse_answer(json.dumps(VALID))

    assert answer.hint(1) == "Look at the status code."
    assert answer.hint(2) == "SECRET-HINT-2"
    assert answer.hint(3) == "SECRET-HINT-3"


@pytest.mark.parametrize("level", [0, 4])
def test_hint_rejects_unknown_levels(level: int) -> None:
    with pytest.raises(ValueError):
        parse_answer(json.dumps(VALID)).hint(level)


def test_extra_fields_are_ignored() -> None:
    answer = parse_answer(json.dumps({**VALID, "confidence": "high"}))

    assert answer.diagnosis == "SECRET-DIAGNOSIS"


def test_invalid_json_is_an_error() -> None:
    with pytest.raises(AnswerError, match="not valid JSON"):
        parse_answer('{"diagnosis": "x"')


def test_arguments_must_be_an_object() -> None:
    with pytest.raises(AnswerError, match="JSON object"):
        parse_answer('["x"]')


@pytest.mark.parametrize("missing", ANSWER_FIELDS)
def test_missing_field_is_an_error(missing: str) -> None:
    arguments = {name: value for name, value in VALID.items() if name != missing}

    with pytest.raises(AnswerError, match=missing):
        parse_answer(json.dumps(arguments))


@pytest.mark.parametrize("bad_value", ["", "   ", None, 3, ["a"]])
def test_empty_or_non_string_field_is_an_error(bad_value: object) -> None:
    with pytest.raises(AnswerError, match="hint_2"):
        parse_answer(json.dumps({**VALID, "hint_2": bad_value}))


def test_error_messages_do_not_contain_the_answer() -> None:
    # Errors go back to the model and may be logged: they name fields, never values (D18).
    broken = {**VALID, "hint_1": ""}

    with pytest.raises(AnswerError) as error:
        parse_answer(json.dumps(broken))

    assert "SECRET" not in str(error.value)


def test_schema_requires_every_field() -> None:
    function = SUBMIT_ANSWER_SCHEMA["function"]

    assert SUBMIT_ANSWER_SCHEMA["type"] == "function"
    assert function["name"] == "submit_answer"
    assert function["parameters"]["required"] == list(ANSWER_FIELDS)
    assert set(function["parameters"]["properties"]) == set(ANSWER_FIELDS)

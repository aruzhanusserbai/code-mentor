import pytest

from agent.answer import Answer
from agent.checks import (
    MAX_SENTENCES,
    check_hint,
    code_identifiers,
    count_sentences,
    find_leaks,
    split_sentences,
)

# Diagnosis and level 1 hint from the first real CI run (eval/examples/real-run-01-ticket-1.md).
REAL_DIAGNOSIS = (
    "An empty or missing `items` list passes validation in CreateOrderRequest. "
    "OrderService calls items.get(0) and throws IndexOutOfBoundsException "
    "(NullPointerException when items is null), GlobalExceptionHandler maps it to 500. "
    "The list needs @NotEmpty."
)
REAL_HINT_1 = (
    "Nice work on the passing test — the valid-order path is fine. For the two failing ones, "
    "the service log shows an `IndexOutOfBoundsException` on the empty-cart request and an NPE "
    "about calling `get(int)` on the items list when `items` is absent, both ending up in the "
    "generic unexpected-error handler and therefore a 500. Does the validation on the incoming "
    "payload currently say anything at all about the items collection being present and non-empty?"
)


# --- code_identifiers ---------------------------------------------------------


def test_real_diagnosis_identifiers() -> None:
    found = code_identifiers(REAL_DIAGNOSIS)

    assert {
        "CreateOrderRequest",
        "OrderService",
        "get(0)",
        "IndexOutOfBoundsException",
        "NullPointerException",
        "GlobalExceptionHandler",
        "@NotEmpty",
    } <= found


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("look at `items.get(0)` here", "items.get(0)"),
        ("the class OrderService", "OrderService"),
        ("method createOrder is wrong", "createOrder"),
        ("it calls get(int)", "get(int)"),
        ("it calls isEmpty()", "isEmpty()"),
        ("a NullPointerException", "NullPointerException"),
        ("add @Valid there", "@Valid"),
        ("the field `total_price`", "total_price"),
    ],
)
def test_each_kind_of_identifier(text: str, expected: str) -> None:
    assert expected in code_identifiers(text)


def test_plain_words_are_not_identifiers() -> None:
    text = "The items list is empty, so the total is wrong. An exception is thrown. Valid input is fine."

    assert code_identifiers(text) == set()


def test_plain_lowercase_word_in_backticks_is_not_an_identifier() -> None:
    # Models put field names like `items` in backticks all the time; banning them
    # would send most ticket 1 hints to the fallback (DECISIONS.md, D19).
    assert code_identifiers("the `items` field and the `total`") == set()


@pytest.mark.parametrize("content", ["Order", "HTTP", "500", "/orders", "must not be empty"])
def test_backticks_with_words_numbers_or_paths_are_not_identifiers(content: str) -> None:
    # Status codes, endpoints and single words are symptoms, not code names.
    assert code_identifiers(f"see `{content}` here") == set()


def test_abbreviations_and_numbers_are_not_identifiers() -> None:
    assert code_identifiers("e.g. the 1.5 version, i.e. the old one, etc.") == set()


# --- find_leaks ---------------------------------------------------------------


def test_real_hint_1_leaks_are_found() -> None:
    leaks = find_leaks(REAL_HINT_1, code_identifiers(REAL_DIAGNOSIS))

    assert "IndexOutOfBoundsException" in leaks
    assert "get(0)" in leaks  # the hint says get(int): same method name


def test_leak_match_is_case_insensitive() -> None:
    assert find_leaks("look at the orderservice class", {"OrderService"}) == ["OrderService"]


def test_leak_match_respects_word_boundaries() -> None:
    assert find_leaks("the MyOrderServiceTest fails", {"OrderService"}) == []


def test_plain_words_in_hint_are_not_leaks() -> None:
    hint = "The items in the request and the order total look suspicious. Check the validation."
    diagnosis = "OrderService reads `items` and `total`; CreateOrderRequest has no @NotEmpty."

    assert find_leaks(hint, code_identifiers(diagnosis)) == []


def test_annotation_needs_the_at_sign() -> None:
    assert find_leaks("Is the input valid?", {"@Valid"}) == []
    assert find_leaks("Maybe @Valid is missing?", {"@Valid"}) == ["@Valid"]


def test_call_matches_by_method_name_with_any_arguments() -> None:
    assert find_leaks("what does get(int) do with an empty list?", {"get(0)"}) == ["get(0)"]
    assert find_leaks("you get a 500 (not 400)", {"get(0)"}) == []


def test_leaks_are_sorted_and_unique() -> None:
    hint = "OrderService and CreateOrderRequest, again OrderService"

    assert find_leaks(hint, {"OrderService", "CreateOrderRequest", "Other"}) == ["CreateOrderRequest", "OrderService"]


# --- count_sentences ----------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("One sentence.", 1),
        ("One. Two! Three?", 3),
        ("No final dot", 1),
        ("Wait... what happened? Look.", 3),
        ("", 0),
    ],
)
def test_count_sentences(text: str, expected: int) -> None:
    assert count_sentences(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "Look at the log, e.g. the first ERROR line.",
        "Compare it with the old one, i.e. the version before your change.",
        "Check headers, body, etc. in the test output.",
        "It is version 1.5 of the service.",
        "Open OrderService.java and read it.",
        "The status was 500 vs. the expected 400.",
    ],
)
def test_dots_inside_a_sentence_do_not_end_it(text: str) -> None:
    assert count_sentences(text) == 1


# --- check_hint, level 1 -------------------------------------------------------------


def answer_with_hint_1(hint_1: str, diagnosis: str = REAL_DIAGNOSIS) -> Answer:
    return Answer(diagnosis=diagnosis, hint_1=hint_1, hint_2="h2", hint_3="h3")


def test_good_hint_1_passes() -> None:
    hint = (
        "The tests expect 400 but the service answers 500. "
        "Follow an order request with an empty cart from the controller to the service. "
        "Where would you expect such a request to be rejected?"
    )

    result = check_hint(answer_with_hint_1(hint), 1)

    assert result.ok
    assert result.leaks == []
    assert result.reasons() == []


def test_real_hint_1_fails_both_checks() -> None:
    result = check_hint(answer_with_hint_1(REAL_HINT_1), 1)

    assert not result.ok
    assert "IndexOutOfBoundsException" in result.leaks
    assert result.reasons() == ["leaks_identifiers"]  # 3 sentences: within the limit


def test_too_long_hint_1_fails() -> None:
    hint = " ".join(["Look at the log."] * (MAX_SENTENCES[1] + 1))

    result = check_hint(answer_with_hint_1(hint), 1)

    assert not result.ok
    assert result.sentences == MAX_SENTENCES[1] + 1
    assert result.reasons() == ["too_long"]


def test_reasons_never_contain_identifiers() -> None:
    # reasons() goes to the log and the CI trace; identifiers come from the diagnosis (D18).
    long_leaky = REAL_HINT_1 + " Look at OrderService. Really."

    reasons = check_hint(answer_with_hint_1(long_leaky), 1).reasons()

    assert reasons == ["leaks_identifiers", "too_long"]


# --- split_sentences ----------------------------------------------------------


def test_split_sentences_keeps_dots_inside_names() -> None:
    text = "Open OrderService.java, e.g. the create method. Then run the test!"

    assert split_sentences(text) == ["Open OrderService.java, e.g. the create method.", "Then run the test!"]


# --- check_hint, level 2: location, not the change ----------------------------

# The published level 2 hint of the second real CI run (eval/examples/real-run-02-ticket-1.md).
# The last sentence says what is missing: almost the fix.
REAL_HINT_2_LOCATION = (
    "The failure is in OrderService.create in src/main/java/com/shopflow/orders/order/OrderService.java, "
    "around the line that picks the currency from the first item. For an empty list it throws "
    "IndexOutOfBoundsException, and when items is absent the DTO returns null and you get a "
    "NullPointerException. GlobalExceptionHandler catches neither case, so its catch-all handler turns "
    "both into 500."
)
REAL_HINT_2 = (
    REAL_HINT_2_LOCATION + " CreateOrderRequest declares the items field with only @Valid and no constraint "
    "on the list itself, so nothing rejects these payloads before the service runs."
)


def answer_with_hint(level: int, hint: str, diagnosis: str = REAL_DIAGNOSIS) -> Answer:
    hints = {"hint_1": "h1", "hint_2": "h2", "hint_3": "h3"}
    hints[f"hint_{level}"] = hint
    return Answer(diagnosis=diagnosis, **hints)


def test_real_hint_2_says_what_is_missing() -> None:
    result = check_hint(answer_with_hint(2, REAL_HINT_2), 2)

    assert not result.ok
    assert result.action_sentences == 1
    assert result.reasons() == ["gives_action"]


def test_location_only_hint_2_passes() -> None:
    # Level 2 may name the file, class, method and exception (DECISIONS.md, D22).
    result = check_hint(answer_with_hint(2, REAL_HINT_2_LOCATION), 2)

    assert result.ok
    assert result.leaks == []


@pytest.mark.parametrize(
    "sentence",
    [
        "Add a check to CreateOrderRequest.",
        "CreateOrderRequest is missing a constraint on the list.",
        "The list in CreateOrderRequest should not be empty.",
        "Replace the first item lookup in OrderService.",
        "Use the right annotation in CreateOrderRequest.",
        "CreateOrderRequest lacks a rule for the list.",
        "OrderService runs without any check of the list.",
        "There is no validation of the list in CreateOrderRequest.",
        "Nothing checks the list before OrderService runs.",
        "OrderService must not read the first item of an empty list.",
        "You need to change OrderService.",
    ],
)
def test_action_next_to_a_code_name_fails_level_2(sentence: str) -> None:
    result = check_hint(answer_with_hint(2, "The failing request ends in OrderService. " + sentence), 2)

    assert result.reasons() == ["gives_action"]
    assert result.action_sentences == 1


def test_action_word_without_a_code_name_passes_level_2() -> None:
    # The action word is in another sentence than the code names: no fix is named.
    hint = "The request reaches OrderService and fails there. What should happen to such a request instead?"

    assert check_hint(answer_with_hint(2, hint), 2).ok


@pytest.mark.parametrize("hint", ["OrderService uses the first item.", "The NullPointerException comes from OrderService."])
def test_word_parts_are_not_action_words(hint: str) -> None:
    # "uses" is not "use", "NullPointerException" is not "no ... check".
    assert check_hint(answer_with_hint(2, hint), 2).ok



def test_expected_vs_actual_with_instead_passes_level_2() -> None:
    # "500 instead of 400" states a fact against the expectation, not a change (D22, real run 03).
    hint = "GlobalExceptionHandler returns 500 instead of a 400."

    assert check_hint(answer_with_hint(2, hint), 2).ok

def test_too_long_hint_2_fails() -> None:
    hint = " ".join(["Look at OrderService."] * (MAX_SENTENCES[2] + 1))

    result = check_hint(answer_with_hint(2, hint), 2)

    assert result.reasons() == ["too_long"]
    assert result.sentences == MAX_SENTENCES[2] + 1


# --- check_hint, level 3: the concept, no annotation or method names -----------


def test_concept_hint_3_with_class_names_passes() -> None:
    # Class names are allowed at level 3: level 2 has already named them (D23).
    hint = (
        "An order without items is a client error, not a server error. "
        "Such input should be rejected in CreateOrderRequest, before OrderService runs, "
        "so that the existing error handling can answer with 400."
    )

    assert check_hint(answer_with_hint(3, hint), 3).ok


def test_annotation_from_the_diagnosis_leaks_at_level_3() -> None:
    result = check_hint(answer_with_hint(3, "The list needs @NotEmpty."), 3)

    assert result.leaks == ["@NotEmpty"]
    assert result.reasons() == ["leaks_identifiers"]


def test_any_annotation_leaks_at_level_3() -> None:
    # The annotation of the fix is often not in the diagnosis at all.
    result = check_hint(answer_with_hint(3, "Try @Size on the list."), 3)

    assert result.leaks == ["@Size"]


def test_method_call_from_the_diagnosis_leaks_at_level_3() -> None:
    result = check_hint(answer_with_hint(3, "Think about what get(int) does with an empty list."), 3)

    assert result.leaks == ["get(0)"]


def test_too_long_hint_3_fails() -> None:
    hint = " ".join(["Think about the input."] * (MAX_SENTENCES[3] + 1))

    assert check_hint(answer_with_hint(3, hint), 3).reasons() == ["too_long"]


@pytest.mark.parametrize("level", [0, 4])
def test_unknown_level_is_an_error(level: int) -> None:
    with pytest.raises(ValueError):
        check_hint(answer_with_hint(1, "hint"), level)


def test_level_2_and_3_reasons_never_contain_identifiers() -> None:
    reasons_2 = check_hint(answer_with_hint(2, REAL_HINT_2), 2).reasons()
    reasons_3 = check_hint(answer_with_hint(3, "Add @NotEmpty in CreateOrderRequest."), 3).reasons()

    for reason in reasons_2 + reasons_3:
        assert reason in {"leaks_identifiers", "gives_action", "too_long"}

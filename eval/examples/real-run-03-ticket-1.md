# Real run 03 — ticket 1, level 2 checks (D22), local run

- **Date:** 14 Nov 2026
- **Where:** local run (`python -m agent.main ... --level 2 --full-answer-out`), service
  from `template/` in Docker Compose, not CI
- **Platform commit:** `ab7dbc1` + uncommitted level 2/3 checks (D22, D23)
- **Model:** ERNIE 5.5 Flash Preview (free tier, via OpenRouter)
- **Code under test:** untouched template (ticket 1 bug present)
- **Goal:** see the new level 2 check on a real answer

## Verdict

| Check | Result |
|-------|--------|
| Diagnosis (cause and location) | **Correct.** Matches `eval/bugs/labels.yaml` (`ticket-1`). |
| Level 2 check | **Triggered, but a false positive.** The first `hint_2` only showed the location and the behaviour, which is what level 2 should do. Two sentences were flagged because of descriptive words: "**use** its currency as the order currency" (next to `OrderService`) and "returns 500 ... **instead** of a 400" (next to `GlobalExceptionHandler`). Neither says what to change. |
| Regeneration | **Worked.** One extra request; the new hint passes the check and is still a good level 2 hint (location, exceptions, no change named). |
| Level 3 (not published, seen in the full answer) | **Too direct, not caught.** It describes "a 'not null' plus 'not empty'/minimum-size rule on the items property" in plain words. The D23 check only blocks annotation and method names, so this passes. Known limit; the eval measures it. |
| Level 1 (not published) | Would fail with `too_long` (4 sentences) and be regenerated. |
| Investigation | 10 of 10 tool calls again; `InvalidOrderException.java`, `ErrorResponse.java` and `CONTRACT.md` are not needed for the cause. |

**Follow-up (D22 amendment):** "instead" was removed from the action words
after this run ("500 instead of 400" states a fact, not a fix). "use" is kept;
the eval decides whether it costs too many regenerations. With the amended
list the rejected hint below would still fail once, because of "use".

## Rejected `hint_2` (first answer)

> The failures come from OrderService.create in src/main/java/com/shopflow/orders/order/OrderService.java, at the line that takes the first entry of the request's item list to read its product and use its currency as the order currency. With an empty list that access throws IndexOutOfBoundsException ("Index 0 out of bounds for length 0"); with the field absent the list is null and you get a NullPointerException. Because neither is a known domain exception, the catch-all branch of GlobalExceptionHandler.handleUnexpected logs "Unexpected error" and returns 500 "Internal server error" instead of a 400.

## Trace (agent-trace.json)

| Field | Value |
|-------|-------|
| level | 2 |
| requests | 4 |
| hit_limit | true |
| error | null |
| hint_status | regenerated |
| hint_check | `["gives_action"]` |

10 tool calls in 2 requests, `submit_answer` in request 3, then one
regeneration request for `hint_2`.

| # | Tool | Arguments | Result size |
|---|------|-----------|-------------|
| 1 | list_files | `.` | 1368 chars |
| 2 | get_logs | `{"max_lines": 200}` | 8039 chars |
| 3 | read_file | `src/main/java/com/shopflow/orders/order/OrderService.java` | 3641 chars |
| 4 | read_file | `src/main/java/com/shopflow/orders/order/dto/CreateOrderRequest.java` | 469 chars |
| 5 | read_file | `src/main/java/com/shopflow/orders/order/OrderController.java` | 1579 chars |
| 6 | read_file | `src/main/java/com/shopflow/orders/common/GlobalExceptionHandler.java` | 3434 chars |
| 7 | read_file | `src/main/java/com/shopflow/orders/common/InvalidOrderException.java` | 230 chars |
| 8 | read_file | `src/main/java/com/shopflow/orders/common/ErrorResponse.java` | 118 chars |
| 9 | read_file | `src/main/java/com/shopflow/orders/order/dto/OrderItemRequest.java` | 754 chars |
| 10 | read_file | `CONTRACT.md` | 3019 chars |

## Comment that would be posted (verbatim)

```markdown
<!-- codementor:ticket=1;mode=debugging;level=2 -->
### CodeMentor: hint for ticket 1 (level 2)

Some ticket tests failed. Here is a hint from your mentor:

Your failing test points at `OrderService.create` in `src/main/java/com/shopflow/orders/order/OrderService.java` (around line 40), where the code reads the first entry of the request's item list to pick up a product id and the currency for the order. When the payload arrives with `"items": []`, that first-element read throws `IndexOutOfBoundsException` ("Index 0 out of bounds for length 0"); when the field isn't sent at all, the list is null and the same call throws `NullPointerException`. Neither of those is a domain exception, so the catch-all branch of `GlobalExceptionHandler` takes over and the client receives 500 `{"status":500,"error":"Internal server error"}` rather than a 400. The body travels through `CreateOrderRequest` and reaches the service in both cases. Your valid-order test keeps passing, since there the first element does exist.

Push a new commit to try again.
```

# Real run 02 — ticket 1, agent v1, hint level 2

- **Date:** 14 Nov 2026
- **Where:** PR #4 (`ticket-1-agent-debug`) in `aruzhanusserbai/codementor-student-test`,
  workflow run `43582507563`, triggered by an empty commit `b613fb7`
- **Platform commit:** `0a99965` (agent v1: `submit_answer`, hint levels, leak protection)
- **Model:** ERNIE 5.5 Flash Preview (free tier, via OpenRouter)
- **Code under test:** untouched template (ticket 1 bug present)
- **Expected level:** 2. PR #4 already had one `mode=debugging` comment by
  `github-actions[bot]` (real run 01, level 1) and two `mode=check` comments,
  which do not count (DECISIONS.md, D17).

## Job steps

| # | Step | Result |
|---|------|--------|
| 1–11 | Set up, detect ticket, checkouts, start service, tests, decide result, collect logs | success |
| 12 | Pick hint level | success, no warning: level 2 |
| 13 | Run the mentor agent (debugging mode) | success |
| 14 | Upload test output and logs | success |
| 15 | Comment on the pull request | success |
| 16 | Fail the check if tests did not pass | failure (expected: tests fail on the template) |

Annotations: `Result: failed` and `Process completed with exit code 1` from
step 16, plus GitHub notices about Node.js 20 and `ubuntu-latest`. No agent
errors and no hint level warning.

## Verdict

| Check | Result |
|-------|--------|
| Hint level | **Correct.** Level 2 was picked from the bot comments and written in the marker. |
| Diagnosis (cause and location) | **Correct.** The comment points to the currency line in `OrderService.create` and explains both failures (empty list, missing list). Matches `eval/bugs/labels.yaml` (`ticket-1`). |
| No solution code | **OK.** No code blocks, no diff. |
| Level 2 rules | **Too direct.** Level 2 should name the location, not what to change. The last sentence names `CreateOrderRequest` and says the list itself has no constraint, which is the cause and almost the fix (level 3 material). |
| Investigation | **Less focused than run 01.** All 10 of 10 tool calls were used (run 01: 7). Three reads are not related to the cause: `pom.xml`, `OrderItem.java`, `InvalidOrderException.java`. The cause was still found correctly. |
| Leak protection (D18) | **OK.** The trace has no diagnosis or hint text; only the level 2 hint was published. |

The prompt is not changed after one run (DECISIONS.md, D15). The eval
(rubric, no-spoiler rate per level) decides whether level 2 needs a stricter
rule.

## Trace (agent-trace.json)

| Field | Value |
|-------|-------|
| level | 2 |
| requests | 6 |
| hit_limit | true |
| error | null |
| hint_status | ok |
| hint_check | `[]` |

10 tool calls in 5 requests (parallel calls), then `submit_answer` after the
limit message in request 6. The level 1 checks and the regeneration run only
for level 1, so `hint_status` is `ok` and no extra request was made.

| # | Tool | Arguments | Result size |
|---|------|-----------|-------------|
| 1 | list_files | `{"path": "."}` | 1408 chars |
| 2 | get_logs | `{"max_lines": 150}` | 8039 chars |
| 3 | read_file | `src/main/java/com/shopflow/orders/order/OrderService.java` | 3641 chars |
| 4 | read_file | `src/main/java/com/shopflow/orders/common/GlobalExceptionHandler.java` | 3434 chars |
| 5 | read_file | `src/main/java/com/shopflow/orders/order/dto/CreateOrderRequest.java` | 469 chars |
| 6 | read_file | `src/main/java/com/shopflow/orders/common/InvalidOrderException.java` | 230 chars |
| 7 | read_file | `src/main/java/com/shopflow/orders/order/OrderController.java` | 1579 chars |
| 8 | read_file | `pom.xml` | 2574 chars |
| 9 | read_file | `src/main/java/com/shopflow/orders/order/OrderItem.java` | 1983 chars |
| 10 | read_file | `src/main/java/com/shopflow/orders/order/dto/OrderItemRequest.java` | 754 chars |

## Posted comment (verbatim)

```markdown
<!-- codementor:ticket=1;mode=debugging;level=2 -->
### CodeMentor: hint for ticket 1 (level 2)

Some ticket tests failed. Here is a hint from your mentor:

The failure is in OrderService.create in src/main/java/com/shopflow/orders/order/OrderService.java, around the line that picks the currency from the first item. For an empty list it throws IndexOutOfBoundsException, and when items is absent the DTO returns null and you get a NullPointerException. GlobalExceptionHandler catches neither case, so its catch-all handler turns both into 500. CreateOrderRequest declares the items field with only @Valid and no constraint on the list itself, so nothing rejects these payloads before the service runs.

Push a new commit to try again.

Full test output and service logs: [workflow run](https://github.com/aruzhanusserbai/codementor-student-test/actions/runs/43582507563).
```

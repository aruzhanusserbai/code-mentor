# Real run 04 — ticket 2, first business-logic bug, local run

- **Date:** 18 Nov 2026
- **Where:** local run (`python -m agent.main --ticket 2 ... --level 1 --full-answer-out`),
  service from `template/` in Docker Compose, not CI
- **Platform commit:** `f5635f3`
- **Model:** ERNIE 5.5 Flash Preview (free tier, via OpenRouter)
- **Code under test:** untouched template (ticket 2 bug present; 4 of 5 ticket 2 tests fail)
- **Goal:** first real example on a bug of another kind: business logic and
  `BigDecimal` immutability, not validation (ticket 1)

## Verdict

| Check | Result |
|-------|--------|
| Diagnosis (cause and location) | **Correct.** Names `OrderService.create`, the start of the total at line 44, the ignored result of `total.add(lineTotal)` at line 54 and immutability of `BigDecimal`; explains why single-item orders pass and why `GET /orders/{id}` shows the same value. Matches `eval/bugs/labels.yaml` (`ticket-2`). |
| Level 1 (published) | **Good, slightly leading.** Describes the symptom (only the first line is counted) and the area (where the total is calculated). The closing question "whether the running sum is actually updated for each extra line" points close to the cause, but names no file, method or change. Checks: ok, 2 sentences. |
| Level 2 (not published, seen in the full answer) | **Good.** File and method, the shape of the code (total from the first item, then a loop), observed behaviour; no change named. Passes the D22 check offline. |
| Level 3 (not published, seen in the full answer) | **Too direct, not caught.** "The result of each line's addition is currently thrown away ... reassigned after each addition" is the fix in plain words. Passes the D23 check offline (no annotation or method names). Same known limit as in run 03; for a one-line fix the gap between level 3 and the answer is especially small. |
| Investigation | **Efficient.** 6 tool calls of 10, 3 requests, no regeneration. Did not call `run_test`: the test output and the log were enough. `Order.java` and `OrderItem.java` were read but are not needed for the cause. |

## Trace (agent-trace.json)

| Field | Value |
|-------|-------|
| level | 1 |
| requests | 3 |
| hit_limit | false |
| error | null |
| hint_status | ok |
| hint_check | `[]` |

| # | Tool | Arguments | Result size |
|---|------|-----------|-------------|
| 1 | list_files | `{"path": ""}` | 1368 chars |
| 2 | get_logs | `{"max_lines": 100}` | 7630 chars |
| 3 | read_file | `src/main/java/com/shopflow/orders/order/OrderService.java` | 3964 chars |
| 4 | read_file | `src/main/java/com/shopflow/orders/order/Order.java` | 2401 chars |
| 5 | read_file | `src/main/java/com/shopflow/orders/order/OrderItem.java` | 1983 chars |
| 6 | read_file | `src/main/java/com/shopflow/orders/order/dto/OrderResponse.java` | 1232 chars |

## Full answer (local only, `--full-answer-out`)

**diagnosis**

> In OrderService.create (src/main/java/com/shopflow/orders/order/OrderService.java), the running total is built from the first item at line 44, then the loop over the remaining items at lines 48-56 calls total.add(lineTotal) on line 54 but ignores the returned value. BigDecimal is immutable, so the accumulated sum is never updated; the order is saved with only the first item's amount (e.g. 64000.00 for two keyboards, 32000.00 for orders whose first line is one keyboard). The tests see the wrong total both in the POST /orders response and in GET /orders/{id}, because the same stored Order.total is returned by OrderResponse.from. Single-item orders pass because the first line is the whole total. The fix is to reassign the result of the accumulation (total = total.add(lineTotal)) so every line contributes; no annotation or signature change is needed.

**hint_2**

> The problem is in OrderService.java, in the create method that builds an order from the request. The total is initialised from the first item, and then a loop adds the other items' line amounts to that total; with the failing requests the stored total stays at the first item's amount while all items are still saved. Both the creation response and the later lookup return this same wrong value.

**hint_3**

> The loop uses BigDecimal arithmetic, and BigDecimal values are immutable: the addition call returns a new value instead of changing the existing one. The result of each line's addition is currently thrown away, so the variable holding the total keeps its initial value from the first line. The total must be the accumulation of every line's unit price times quantity, reassigned after each addition, so multi-item orders and repeated products in two lines all contribute. Since the same stored total is returned by both create and get-by-id, fixing the accumulation fixes both endpoints.

## Comment that would be posted (verbatim)

```markdown
<!-- codementor:ticket=2;mode=debugging;level=1 -->
### CodeMentor: hint for ticket 2 (level 1)

Some ticket tests failed. Here is a hint from your mentor:

The service answers successfully and the items in the response look right, but the order total is only the amount of the first line, as if the remaining lines were ignored. Look at the order creation flow where the total is calculated before the order is stored, and ask whether the running sum is actually updated for each extra line.

Push a new commit to try again.
```

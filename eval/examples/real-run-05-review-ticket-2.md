# Real run 05 — ticket 2, review mode, first run, local

- **Date:** 18 Nov 2026
- **Where:** local run (`python -m agent.main --mode review --ticket 2 ...`), not CI
- **Platform commit:** `eb4dfa8` + uncommitted review mode (step 1)
- **Model:** ERNIE 5.5 Flash Preview (free tier, via OpenRouter)
- **Code under test:** template + `eval/reference/ticket-2.patch` as the student's commit
  (one-line fix `total = total.add(lineTotal);`), diff against the template commit.
  The service was not started: review mode does not need it, and the patch was verified
  in Docker the same day (11 passed).
- **Goal:** first real review questions

## Verdict

| Check | Result |
|-------|--------|
| Format | **Ok.** 3 questions, each ends with "?", marker with the commit hash written by code. |
| Q1: why it failed before | **Good.** About the exact line the student changed, and why single-item orders still worked. Two questions in one sentence, but both are about the cause. |
| Q2 | **Weak.** Misreads the ticket request ("`productId` 1 twice", the ticket has quantity 2) and asks about a made-up line `total.add(BigDecimal.ZERO)` that nobody wrote. Confusing, not about the student's decision. |
| Q3 | **Weak.** Asks what to change "if quantity came from the request", but it already does. Not grounded in the code; does not ask why the fix looks like this. |
| "Why this fix" question | **Missing.** No question about the chosen approach (for example reassigning vs. starting from zero and summing all lines in one loop). |
| Investigation | **Efficient.** 1 tool call (`OrderService.java`), 2 requests. |

So 1 of 3 questions is useful. Possible prompt changes, not tried yet (no extra
runs spent): ask questions only about code that exists in the repository or the
diff, no hypothetical code; make the "why this fix" question compare the
student's change with one concrete alternative.

## Trace (agent-trace.json)

| Field | Value |
|-------|-------|
| mode | review |
| requests | 2 |
| hit_limit | false |
| error | null |

| # | Tool | Arguments | Result size |
|---|------|-----------|-------------|
| 1 | read_file | `src/main/java/com/shopflow/orders/order/OrderService.java` | 3972 chars |

## Comment that would be posted (verbatim)

```markdown
<!-- codementor:ticket=2;mode=review;sha=c34e13f098534dcf901b4dcc2c3617707fb3d415 -->
### CodeMentor: ticket 2 tests passed

All ticket 2 tests passed. Before the ticket is closed, please answer a few questions about your fix:

1. Why did the line `total.add(lineTotal);` leave the order total unchanged, and why did a single-item order return the correct amount anyway?
2. Walk through the loop with the ticket's request (`productId` 1 twice then `productId` 3): what would `total` have been if the loop had read `total.add(BigDecimal.ZERO)` instead?
3. If the loop later had to handle `quantity` values coming from the request, what change would you need around `BigDecimal.valueOf(itemRequest.getQuantity())` to keep the total accurate?

Reply in a comment on this pull request, in your own words. When the answers show that you understand the fix, the PR gets the label `ticket-2-done`.
```

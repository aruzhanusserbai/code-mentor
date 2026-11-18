# Real run 07 — ticket 2, review mode, 400 characters and two sentences, local

- **Date:** 19 Nov 2026
- **Where:** local run with `--full-answer-out`, same command and student repository as runs 05 and 06
- **Platform commit:** `eb4dfa8` + uncommitted review mode (step 1) + changes below
- **Model:** ERNIE 5.5 Flash Preview (free tier, via OpenRouter)
- **Code under test:** the same as runs 05 and 06 (template + `ticket-2.patch` as the student's commit)

## Changes after run 06

1. A question may be up to 400 characters (was 300) and up to two sentences
   (for example one sentence of context, then the question); the last one ends with "?".
2. Rejected `submit_questions` calls are saved in `--full-answer-out` (local runs
   only, refused in CI), so a failed run can be analysed. Still never logged or traced.

## Verdict

| Check | Result |
|-------|--------|
| Format | **Ok on the first submit.** No rejected calls (`"rejected": []`). |
| Q1: why it failed before | **Good.** The exact line, the start of the total at line 44, and the real numbers from the ticket (64000.00 vs 76990.00). |
| Q2: why this fix, against an alternative | **Good.** Compares the fix with summing every item in one loop. One small inaccuracy: "why did you keep the first item outside" — the student did not write that part, it was already there. |
| Q3 | **Weak.** "Avoid reassigning total by calling `total = total.add(lineTotal)` only after the loop" is itself a reassignment, and `lineTotal` does not exist after the loop. Made-up code again, despite the rule. |
| Investigation | 1 tool call, 2 requests. |

## Comparison of runs 05–07

| | Run 05 | Run 06 | Run 07 |
|---|--------|--------|--------|
| Prompt | first version | + only existing code, + one concrete alternative | + 400 chars, two sentences |
| Requests / tool calls | 2 / 1 | 3 / 1 | 2 / 1 |
| Valid questions | 3 | 0 (both submits rejected) | 3 |
| Useful questions | 1 | — | 2 |
| "Why this fix" question | missing | — | present (Q2) |
| Made-up code | 2 questions | unknown | 1 question (Q3) |

## Comment that would be posted (verbatim)

```markdown
<!-- codementor:ticket=2;mode=review;sha=c34e13f098534dcf901b4dcc2c3617707fb3d415 -->
### CodeMentor: ticket 2 tests passed

All ticket 2 tests passed. Before the ticket is closed, please answer a few questions about your fix:

1. In create() the original code called total.add(lineTotal) without assigning the result, and the total was first computed on line 44. Why did that produce 64000.00 KZT instead of 76990.00 KZT for the request with 2 keyboards and 1 hub?
2. You now reassign total inside the loop over otherItems, while the total of the first item is still calculated separately at line 44 before the loop. Would summing every item inside a single loop produce the same result here, and why did you keep the first item outside?
3. Could you have avoided reassigning total by calling total = total.add(lineTotal) only after the loop, or would that behave differently for an order with a single item?

Reply in a comment on this pull request, in your own words. When the answers show that you understand the fix, the PR gets the label `ticket-2-done`.
```

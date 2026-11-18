# Real run 08 — ticket 2, review mode, exactly two questions, local

- **Date:** 19 Nov 2026
- **Where:** local run with `--full-answer-out`, same command and student repository as runs 05–07
- **Platform commit:** `eb4dfa8` + uncommitted review mode (step 1) + changes below
- **Model:** ERNIE 5.5 Flash Preview (free tier, via OpenRouter)
- **Code under test:** the same as runs 05–07 (template + `ticket-2.patch` as the student's commit)

## Changes after run 07

1. Exactly two questions with fixed roles, in this order: (1) why the code
   failed before the fix, (2) why the fix looks like this, compared with one
   concrete alternative. In runs 05 and 07 the third question was filler about
   made-up code.
2. Only the lines added or removed in the diff are the student's decisions; the
   code around them was already there (run 07, Q2 gave the student credit for
   template code).

## Verdict

| Check | Result |
|-------|--------|
| Format | **Ok on the first submit.** 2 questions, `"rejected": []`. |
| Q1: why it failed before | **Good.** The exact line, the real numbers from the ticket (64000.00 vs 76990.00), and why a one-item order is not affected. |
| Q2: why this fix, against an alternative | **Good.** A real alternative that makes sense in this code: drop the seed from the first item and sum all items from zero in one loop. Asks why the student kept the first item outside the loop: a decision they made by keeping the structure, not code they are wrongly credited with. |
| Made-up code | **None.** |
| Investigation | 1 tool call (`OrderService.java`), 2 requests. |

Both questions are on point: step 1 (review mode) is accepted.

## Comparison of runs 05–08

| | Run 05 | Run 06 | Run 07 | Run 08 |
|---|--------|--------|--------|--------|
| Prompt | first version | + only existing code, + one concrete alternative | + 400 chars, two sentences | exactly 2 questions with fixed roles |
| Requests / tool calls | 2 / 1 | 3 / 1 | 2 / 1 | 2 / 1 |
| Valid questions | 3 | 0 (both rejected) | 3 | 2 |
| Useful questions | 1 | — | 2 | 2 |
| "Why this fix" question | missing | — | present | present |
| Made-up code | 2 | unknown | 1 | 0 |

One run per prompt version on one bug: this shows the direction, not a
measured rate. The eval will measure it.

## Comment that would be posted (verbatim)

```markdown
<!-- codementor:ticket=2;mode=review;sha=c34e13f098534dcf901b4dcc2c3617707fb3d415 -->
### CodeMentor: ticket 2 tests passed

All ticket 2 tests passed. Before the ticket is closed, please answer two questions about your fix:

1. In create() the original line called total.add(lineTotal) without assigning the result, and the loop's total stayed equal to the first line's amount. Why does that make the two keyboards plus the USB-C hub order report 64000.00 instead of 76990.00, and why is a one-item order unaffected?
2. Your fix keeps the running total seeded on line 44 with the first item's unitPrice times quantity and adds each remaining line inside the loop over otherItems. An alternative would be to drop that seed and loop over all of request.getItems(), summing every line into a total starting at zero; what made you keep the first item handled outside the loop?

Reply in a comment on this pull request, in your own words. When the answers show that you understand the fix, the PR gets the label `ticket-2-done`.
```

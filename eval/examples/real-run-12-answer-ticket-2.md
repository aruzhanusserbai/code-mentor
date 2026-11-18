# Real run 12 — ticket 2, full PR path in CI: debugging, review, answer, label

- **Date:** 18–19 Nov 2026 (CI times below are UTC, 18 Nov)
- **Where:** PR #5 (`ticket-2-order-total`) in `aruzhanusserbai/codementor-student-test`, real CI
- **Model:** ERNIE 5.5 Flash Preview (free tier, via OpenRouter)
- **Result:** the PR has the label `ticket-2-done`
- **Platform commits:** `801375f` (review and answer jobs) for runs 1–4, `713bb61` (D30, D31) for runs 5–6
- **Source:** PR comments, workflow runs, jobs and check annotations from the public GitHub API.
  Job logs and the `agent-trace.json` artifacts need authentication and were not read here.

This is the first end-to-end run of all three modes, and the record of one
real failure: how it was found and fixed. Good material for REFLECTION.md.

## Timeline

| # | Run | Event | Commit | Result |
|---|-----|-------|--------|--------|
| 1 | [44395425904](https://github.com/aruzhanusserbai/codementor-student-test/actions/runs/44395425904) | pull_request | `a88e2d8` (ticket 2 bug) | red, debugging hint level 1 |
| 2 | [44396502352](https://github.com/aruzhanusserbai/codementor-student-test/actions/runs/44396502352) | pull_request | `e39f6c3` (one-line fix) | green, review on the **wrong base** |
| 3 | [44397300538](https://github.com/aruzhanusserbai/codementor-student-test/actions/runs/44397300538) | issue_comment | weak answer | `followup`, attempt 1 |
| 4 | [44397603005](https://github.com/aruzhanusserbai/codementor-student-test/actions/runs/44397603005) | issue_comment | good answer | **`answer_failed`** fallback |
| — | — | local | same input as run 4 | diagnosis, D30, D31 (platform `956417d`, `ea6757b`, `713bb61`) |
| 5 | [44403038941](https://github.com/aruzhanusserbai/codementor-student-test/actions/runs/44403038941) | pull_request | `237b529` (empty commit, correct base) | green, new review |
| 6 | [44403868375](https://github.com/aruzhanusserbai/codementor-student-test/actions/runs/44403868375) | issue_comment | good answer | **`done`**, label `ticket-2-done` |

## 1. Debugging (run 1): correct

```markdown
<!-- codementor:ticket=2;mode=debugging;level=1 -->
### CodeMentor: hint for ticket 2 (level 1)

Some ticket tests failed. Here is a hint from your mentor:

The items in the response are right, but the order total matches only one line, usually the first one, and it never grows as more lines are processed. Look at how the total is built up while the order is being created, and ask yourself what happens to the running sum on each loop turn. Are you keeping the new value anywhere?

Push a new commit to try again.

Full test output and service logs: [workflow run](https://github.com/aruzhanusserbai/codementor-student-test/actions/runs/44395425904).
```

Level 1, no file or method names, points at "keeping the new value".

## 2. Review on the wrong base (run 2): a setup mistake, not an agent mistake

The `main` branch of the test repository was the old template, where the total
was still correct. So the PR diff (`main...HEAD`) contained both the bug
(seeding the total from the first item, `subList`) and the fix, and the agent
read the whole refactoring as the student's change:

```markdown
<!-- codementor:ticket=2;mode=review;sha=e39f6c3acb64bb0bd346f598a51c42de44c29674 -->
### CodeMentor: ticket 2 tests passed

All ticket 2 tests passed. Before the ticket is closed, please answer two questions about your fix:

1. Before your change, create in OrderService started total at BigDecimal.ZERO and only added line totals inside the loop over request.getItems(). For the ticket request (productId 1 quantity 2, then productId 3 quantity 1) the stored total was 64000.00 instead of 76990.00 — which of those two numbers would the original loop have produced, and where did the missing part go?
2. Your version seeds total with the first item's line total, adds a first OrderItem and loops over subList(1, size); the alternative would be keeping the single loop over request.getItems() and just starting the total from the first item. What does the subList approach buy you here (note the currency check now only sees the other items), and which would you pick?

Reply in a comment on this pull request, in your own words. When the answers show that you understand the fix, the PR gets the label `ticket-2-done`.

Full test output: [workflow run](https://github.com/aruzhanusserbai/codementor-student-test/actions/runs/44396502352).
```

Question 1 asks about an original loop that had no bug; question 2 asks about
code the student did not write (though it notices a real side effect: the
currency check no longer sees the first item). A real student repository has
the bug in `main` (it comes from the template), so its diff is one line. Fix:
`main` of the test repository was fast-forwarded to `a88e2d8`, and an empty
commit on the branch started a new review (step 5).

## 3. Weak answer → follow-up (run 3): correct

Student (in Russian: "The loop calculated the sum wrong, but after the fix the
tests pass."):

> Цикл неправильно считал сумму, но после исправления тесты проходят.

```markdown
<!-- codementor:ticket=2;mode=answer;attempt=1;result=followup -->
### CodeMentor: follow-up question (1 of 3)

Your change does make the tests pass, and you spotted that the sum was the broken part — but I can't yet tell what you think the original loop was missing. Let's narrow it to one line: in the original code the total started at BigDecimal.ZERO and then a line total was added once per item in the loop over request.getItems(). In that original loop, was the line total for productId 1 with quantity 2 (32000.00) added to the total, or not?

Reply in a new comment on this pull request.
```

One question, a smaller step, no answer given.

## 4. Good answer → `answer_failed` (run 4): the failure

Student (in Russian: BigDecimal is immutable, the result of `add` was thrown
away, only the first line stayed, so 64000 instead of 76990; `subList` avoids
loading the first product twice; downside: the currency check skips the first
item):

> BigDecimal неизменяемый, поэтому total.add(lineTotal) без присваивания ничего не меняло — строка для productId 1 (32000.00) в исходном коде не попадала в total, терялась каждая строка, кроме первой, которую взяли отдельно под валюту. Поэтому было 64000 (только первая строка), а должно быть 76990 (сумма всех трёх). Я выбрал(а) subList(1, size), чтобы не загружать первый товар из БД дважды — он уже был загружен раньше ради валюты. Минус в том, что проверка одинаковой валюты теперь смотрит только на остальные товары, а не на все.

```markdown
<!-- codementor:ticket=2;mode=check;result=answer_failed -->
### CodeMentor

The mentor could not process your answer this time. Please post it again in a new comment a bit later.
```

### Diagnosis

| Step | What we saw |
|------|-------------|
| Public check annotation | `the model did not submit a valid verdict (text_instead_of_submit)` |
| `agent-trace.json` (downloaded by the user from the run) | 3 requests, 1 `read_file`, then twice no `submit_verdict` |
| First guess (mine) | "the model answered like in a chat" — **wrong** |
| Local run, plain-text replies saved (`956417d`) | `"text_replies": [""]`: the "text" was an **empty** reply |
| Local run, `finish_reason` and tokens logged (`956417d`) | requests 3 and 4: `finish_reason=length`, `reasoning_tokens=1500` of `MAX_ANSWER_TOKENS=1500` |

The free model spent the whole token limit on hidden reasoning and never got
to the tool call; the loop counted the empty reply as text instead of the final
tool, and the second empty reply ended the run (D20).

### Two fixes

1. **`empty_reply` and a higher limit** (`ea6757b`, D30): an empty reply has
   its own miss reason; `MAX_ANSWER_TOKENS` 1500 → 4000. A local check on the
   same input showed this alone is not enough: request 2 again ended with
   `finish_reason=length` and 4001 reasoning tokens of 4000; the reminder
   request then answered at once with 0 reasoning tokens.
2. **One extra request after an empty reply cut by the limit** (`713bb61`,
   D31): it does not use the second chance of D20, once per run. Limiting
   reasoning through OpenRouter's `reasoning` parameter is postponed to the
   eval (model-specific, unknown if this free model respects it).

## 5. Review on the correct base (run 5): good

```markdown
<!-- codementor:ticket=2;mode=review;sha=237b529d1c12f00d6b74aab595a6c76ea84e814c -->
### CodeMentor: ticket 2 tests passed

All ticket 2 tests passed. Before the ticket is closed, please answer two questions about your fix:

1. In create() the line you changed called total.add(lineTotal) and threw the result away. For the ticket request with productId 1 quantity 2 followed by productId 3 quantity 1, what value did total hold when the loop ended, and why did that produce 64000.00 KZT in the response?
2. Line 44 seeds total with the first product's price times quantity and the loop iterates over subList(1, ...), so only the later items pass through total = total.add(lineTotal). Why keep the first item outside the loop instead of starting from BigDecimal.ZERO and looping over all items?

Reply in a comment on this pull request, in your own words. When the answers show that you understand the fix, the PR gets the label `ticket-2-done`.

Full test output: [workflow run](https://github.com/aruzhanusserbai/codementor-student-test/actions/runs/44403038941).
```

Both questions are about the changed line and a real alternative, as in local
run 08.

## 6. Good answer → `done` + label (run 6): good

Student (in Russian: the same explanation as in step 4, plus why the first
item stays outside the loop):

> BigDecimal неизменяемый, поэтому total.add(lineTotal) без присваивания ничего не меняло — в цикле по subList(1, size) результат каждой строки терялся, и в total оставалась только сумма первого товара, взятого отдельно под валюту. Поэтому было 64000.00 вместо 76990.00. Я выбрал(а) начать с первого товара отдельно, а не с BigDecimal.ZERO в цикле по всем товарам, чтобы не загружать первый товар из БД дважды — он уже был загружен раньше ради валюты. Минус в том, что при такой структуре легко забыть переприсвоить результат add, как и произошло.

```markdown
<!-- codementor:ticket=2;mode=answer;attempt=1;result=done -->
### CodeMentor: ticket 2 done

Exactly right on both counts. You nailed the real cause: BigDecimal is immutable, so without reassigning the add result the loop's line totals were thrown away and total stayed at the first item's amount, which is why the response showed 64000.00 instead of 76990.00. And your reason for seeding with the first product — it was already loaded for the currency check, so starting from ZERO would mean fetching it twice — is a sensible tradeoff, and it is good that you noticed the downside of forgetting the reassignment. Nice work, no further changes needed.

Your answers show that you understand the fix. The PR gets the label `ticket-2-done`.
```

The job `answer` finished without an error annotation, the comment has
`result=done`, and the workflow added the label `ticket-2-done` through the
issues API with the existing `pull-requests: write` permission (no
`issues: write` needed).

The answer in this cycle was good at once, so the new cycle had no
`followup`; the weak-answer path was shown in step 3. Whether this run hit an
empty reply and used the D31 retry is in its `agent-trace.json` artifact
(`llm_requests`), which was not read for this file.

## What this run shows

| Check | Result |
|-------|--------|
| Mode chosen by the workflow (debugging / review / answer) | correct in all 6 runs |
| Only the PR author's comments start answer mode | yes (no other commenters in this PR) |
| Review marker sha = PR head, old review ignored after a new push | yes (`e39f6c3` → `237b529`) |
| A new review starts the answer attempts again | yes: run 6 is attempt 1 after the new review |
| Label added by the workflow, the agent has no token | yes |
| Failure found by logging facts (finish reason, tokens), not by guessing | yes, the first guess was wrong |

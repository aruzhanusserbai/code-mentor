# Real run 06 — ticket 2, review mode, stricter prompt, local

- **Date:** 18 Nov 2026
- **Where:** local run, same command and the same student repository as run 05
- **Platform commit:** `eb4dfa8` + uncommitted review mode (step 1) + prompt change below
- **Model:** ERNIE 5.5 Flash Preview (free tier, via OpenRouter)
- **Code under test:** the same as run 05 (template + `ticket-2.patch` as the student's commit)
- **Goal:** check two prompt changes made after run 05

## Prompt change after run 05

1. Ask only about code that exists (the diff or files read with the tools);
   never invent code; take request examples from the ticket exactly.
2. The "why the fix looks like this" question compares the student's change
   with one concrete alternative fix, named in words.

## Result: no questions

The model called `submit_questions` twice and both calls failed the code
checks, so the run ended without an answer (`invalid_submit`); the workflow
would post the plain "tests passed" comment.

| Request | What happened |
|---------|---------------|
| 1 | `read_file` `OrderService.java` (3972 chars) |
| 2 | `submit_questions` rejected: question 1 must end with '?' |
| 3 | `submit_questions` rejected: question 1 is longer than 300 characters |

The rejected questions are not logged (D18 applies to every final tool), so
their text is unknown. Likely reason: rule 2 asks for a comparison with an
alternative inside one sentence, which pushes the question past 300 characters
or into two sentences.

## Comparison with run 05

| | Run 05 | Run 06 |
|---|--------|--------|
| Prompt | first version | + only existing code, + one concrete alternative |
| Requests | 2 | 3 |
| Tool calls | 1 | 1 |
| Valid questions | 3 (1 useful, 2 about made-up code) | 0 (both submits rejected) |
| Comment | review comment | none, plain result |

Neither run gives a good review yet. Run 05 shows the content problem, run 06
shows that the format limits and the stricter content rules pull against each
other.

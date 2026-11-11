# Decisions

A log of non-obvious decisions: what, why, alternatives, and where the AI
assistant (Claude Code) or I were wrong.

## D1 — Ticket 0 is a small feature, not an empty PR (11 Nov 2026)

**What.** Ticket 0 asks the student to add `GET /products/{id}` (404 if the
product does not exist), following the existing `GET /orders/{id}`. The
endpoint is absent from the template, so the ticket 0 tests fail until the
student implements it. Tests: health is `UP`, `GET /products/{id}` returns the
same object as in `GET /products`, missing id returns 404 in the standard
error format.

**Why.** The first PR should go through the full pipeline (tests → agent
comment) with real code in it. "Copy an existing pattern" also trains reading
the codebase, which is one of the two target skills.

**Alternatives.** (a) Tests only check that the service starts, and ticket 0 is
"run the project and open a PR". Rejected: the PR would be empty and the tests
would pass on the untouched template, so the pipeline would not be exercised.
(b) A trivial change such as a new seed product. Rejected: no code reading.

**Who decided.** Claude proposed option (a) as the default; I chose the
feature version.

## D2 — Ticket 1 fix must be small: validation infrastructure already exists (11 Nov 2026)

**What.** Both `"items": []` and a missing `items` must return 400. The
template already has `@Valid` on the request body, constraints on item fields
(`@NotNull`, `@Min(1)`), and a `@RestControllerAdvice` that maps
`MethodArgumentNotValidException` to the standard error format. Only the
constraint on the `items` list itself is missing. The 500 comes from
`OrderService` taking the order currency from the first item
(`items.get(0)`), which is a natural reason for that code to exist (one
order = one currency).

**Why.** The ticket trains reading code and understanding HTTP status codes,
not writing an error-handling framework. The expected fix is one annotation,
but finding *where* to put it requires following the request from controller
to service. Checking `null` too prevents "fixing" only the `isEmpty()` case
with an `if` in the service.

**Alternatives.** (a) No exception handler in the template, so the student
also builds the error format. Rejected: too large for the first real ticket
and mixes two skills. (b) An artificial `items.get(0)` with no purpose.
Rejected: looks fake; a realistic codebase has a reason for every line.

**Note.** The bug is described only in `eval/bugs/labels.yaml`, never in
template comments (CLAUDE.md, hard rule 1). The reference fixes for tickets
0 and 1 are stored as patches in `eval/reference/`.

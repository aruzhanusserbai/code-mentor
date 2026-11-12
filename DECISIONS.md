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

## D3 — Tests get the service address from an env variable and wait for health (11 Nov 2026)

**What.** Ticket tests read the base URL from `CODEMENTOR_BASE_URL`
(default `http://localhost:8080`). A session fixture polls
`/actuator/health` for up to 90 s before the first test runs.

**Why.** The same tests must run locally and in GitHub Actions, where the
service starts in the background and needs time (database, Flyway, Spring).
Without waiting, the first tests would fail with "connection refused", which
is noise for the student and for the agent.

**Alternatives.** A fixed `sleep` in the workflow (slow and flaky) or a
hard-coded URL (cannot run against another host).

## D4 — Template packages by feature, layers inside each feature (11 Nov 2026)

**What.** `product/`, `order/` (with `dto/`), `common/` (exceptions, global
error handler). Inside each feature: controller → service → repository.

**Why.** A student new to the codebase finds everything about orders in one
place, and ticket 0 ("do it like orders") is a natural copy-the-pattern task.
The layering rule from CLAUDE.md is kept.

**Alternatives.** Package by layer (`controller/`, `service/`, ...). Also
common in real projects, but related code ends up spread over many folders.

## D5 — English locale is fixed explicitly (11 Nov 2026)

**What.** `spring.web.locale: en` with `spring.web.locale-resolver: fixed` in
`application.yml`, plus `-Duser.language=en -Duser.country=US` in the
Dockerfile `ENTRYPOINT`.

**Why.** Bean Validation messages depend on the locale. On my machine (Russian
JVM locale) the ticket 1 error was `"items: не должно быть пустым"`, while
Docker and CI would answer in English. Error messages must be the same
everywhere: in the ticket text, in the tests output the agent reads, and in
the eval. The application setting covers runs from an IDE; the JVM options
cover everything else that uses the default locale (for example log output).

**Verified.** Running locally with a Russian JVM locale and
`Accept-Language: ru`, the error is
`"items[0].quantity: must be greater than or equal to 1"`.

**Alternatives.** Only JVM options (an IDE run would still be localized), or
custom `message=` on every constraint (verbose, easy to forget).

## D6 — Spring Boot 3.5.5 (11 Nov 2026)

**What.** The template uses `spring-boot-starter-parent` 3.5.5.

**Why.** Claude first wrote 3.5.7. Because of a very slow network, the code
was compiled and run against the dependencies already in the local Maven
cache, which had 3.5.5. The committed version is the one that was actually
verified. The difference between patch versions does not matter for this
project.

## D7 — Mistake: `git add --renormalize` staged the reference fix (11 Nov 2026)

**What happened.** To produce the reference patches, the plan was: stage the
buggy template, apply the fixes in the working tree, save `git diff` (working
tree vs index) as a patch, then restore the template from the index. While the
ticket 0 fix was already in the working tree, Claude added `.gitattributes`
(LF line endings) and ran `git add --renormalize template`. That command
re-stages all tracked files from the working tree, so the ticket 0 fix went
into the index. The diff against the index became empty and the "baseline"
in the index was no longer buggy.

**How it was noticed.** The command meant to print the ticket 0 patch printed
nothing; `wc -l` showed `eval/reference/ticket-0.patch` had 0 lines.

**How it was fixed.** A copy of the buggy sources, made before any fix for a
compile check, was still in the scratch directory. Claude created a temporary
git repository from that copy, committed it as the baseline, copied the fixed
sources on top and generated both patches from that diff. Then the template
was restored from the same copy and the index re-synced. Checks: the template
has no `@NotEmpty` and no `ProductNotFoundException`, both patches apply with
`git apply --check`, and the ticket tests fail on the template and pass with
the patches.

**Lesson.** Do not run commands that touch the whole index while there are
temporary changes in the working tree. Better: make the baseline commit first
and produce patches with `git diff` against a commit, or work in a separate
copy.

## D8 — Neutral error message in ticket 1 (12 Nov 2026)

**What.** The example in `tickets/ticket-1.md` is now
`"<what is wrong with the request>"`, and the ticket says the wording is up to
the student.

**Why.** The first version showed `"items: must not be empty"`. That is exactly
the default message of `@NotEmpty` formatted by our error handler, so the
ticket gave away the solution. Spotted by me in review, not by Claude.

## D9 — Branch naming rule `ticket-<N>-<description>` (12 Nov 2026)

**What.** Student branches must match `^ticket-([0-9]+)-[a-z0-9-]+$`.
The workflow takes N from the branch name and runs only
`tests/tickets/ticket_<N>`. The agent gets the ticket number from the same
place. A branch that does not match, or an N without tests, fails the check
with a message; tests and agent do not run.

**Why.** Running all ticket tests on every PR would show failures of tickets
the student has not started, and the agent would not know which ticket to
help with. The branch name is something the student already sets, so no
extra configuration is needed.

**Alternatives.** (a) Ticket number in the PR title or a PR label: easy to
forget or edit later, and labels need extra permissions. (b) Detect the ticket
from changed files: unreliable, a fix can touch any file. (c) Run all tests
and report per ticket: noisy and slower.

## D10 — Placeholder PR comment: one per run, marker `mode=check` (12 Nov 2026)

**What.** Until the agent is connected, the workflow posts a new PR comment on
every run with the test result and a hidden marker
`<!-- codementor:ticket=N;mode=check;result=passed|failed|build_failed -->`.

**Why.** A new comment per push keeps a visible history of attempts, which is
the same model the agent will use (PLAN.md: each failed attempt gets a more
specific hint). The agent will pick the next hint level by counting earlier
comments with `mode=debugging`; the placeholder uses `mode=check` and has no
`level`, so it can never shift the hint level.

**Alternatives.** Edit one comment in place: less noise, but loses the history
the hint levels depend on.

**Note for answer mode (17–23 Nov).** Reply only to comments by the PR author;
ignore comments by bots (including our own) and by anyone else.

## D11 — Keep the "currency from the first product" comment in OrderService (12 Nov 2026)

**What.** `OrderService.java` line 39 keeps the comment
`// one order = one currency, we take it from the first product`, directly
above the `items.get(0)` line that causes the ticket 1 bug. The line number in
`eval/bugs/labels.yaml` (40) stays the same.

**Why.** The comment explains the *intent* of the code (why the first item is
read), not the bug: it says nothing about empty or missing lists. Real code
has comments like this, and the template should look realistic. The student
still has to connect the stack trace (`IndexOutOfBoundsException` /
`NullPointerException` at line 40) with the missing validation on the request.

**Alternatives.** Remove the comment so the line draws less attention.
Rejected: the code would look less natural, and hiding intent is not the skill
we train; the skill is reading code and finding where invalid input gets in.

**Note.** Claude flagged the comment as a possible hint before publishing the
template; I decided to keep it.

## D12 — Mistake: `if: always()` on a step that needs earlier steps (12 Nov 2026)

**What happened.** In `check.yml` the step "Collect service logs" had
`if: always()` and `working-directory: student`. For a PR from a branch with a
wrong name (`fix-stuff`), the job stops at "Detect ticket from branch name",
so the student repository is never checked out. The logs step still ran and
failed with "No such file or directory". In the PR checks its annotation was
shown above the real message ("Branch 'fix-stuff' does not follow the
rule ..."), which would confuse a student.

**How it was noticed.** Running the planned scenario 4 (`fix-stuff`) in the
test student repository and reading the job steps and annotations through the
GitHub API.

**How it was fixed.** The step now runs only if the service step actually ran:
`if: always() && (steps.service.outcome == 'success' || steps.service.outcome == 'failure')`.
Commit `21196c1`; verified by a new run on `fix-stuff`.

**Lesson.** `always()` means "even if the job already failed". A step with
`always()` must check that everything it depends on (checkout, a started
service) really happened. Claude wrote the original condition; the planned
negative scenario caught it.

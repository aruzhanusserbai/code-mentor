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

# CodeMentor

A training platform for junior backend developers. The student joins an
existing Java/Spring project, fixes realistic tickets in their own GitHub
repository, and an AI mentor agent reviews every pull request with hints,
never with solution code.

Full plan: [PLAN.md](PLAN.md). Decisions log: [DECISIONS.md](DECISIONS.md).

> Status: early development (skeleton, template service, tests for tickets 0–1).

## Repository layout

| Path | What |
|------|------|
| `template/` | Java/Spring orders service the student receives (with ticket bugs) |
| `tickets/` | Student-facing ticket descriptions |
| `tests/tickets/` | Protected black-box tests per ticket (pytest + requests, HTTP only) |
| `agent/` | AI mentor agent (Python) — *in progress* |
| `eval/` | Seeded bugs, labels, reference fixes, eval runner, results |
| `.github/workflows/` | Reusable workflow for student repositories — *in progress* |
| `agent-logs/` | Key Claude Code sessions |

## Quick start

Requirements: Docker with Compose, Python 3.11+.

```bash
# 1. Run the template service (http://localhost:8080)
cd template
docker compose up --build -d
cd ..

# 2. Install test dependencies
python -m venv .venv
.venv/Scripts/activate        # Windows (Git Bash); on Linux/macOS: source .venv/bin/activate
pip install -r tests/requirements.txt

# 3. Run ticket tests
pytest tests/tickets/ticket_0 -v
pytest tests/tickets/ticket_1 -v
```

On Windows, use `py` instead of `python` if `python` is not on the PATH.

On the untouched template, the ticket tests are **expected to fail**: the
student's job is to make them pass. Health checks pass.

Tests read the service address from `CODEMENTOR_BASE_URL`
(default `http://localhost:8080`).

## Branch naming rule

Students work in branches named `ticket-<N>-<description>`
(regex `^ticket-([0-9]+)-[a-z0-9-]+$`), for example `ticket-1-empty-cart`.

- The workflow runs only the tests of that ticket: `tests/tickets/ticket_<N>`.
- The agent gets the ticket number from the branch name.
- A branch that does not match the rule, or a ticket number without tests,
  fails the check with a clear message; the tests and the agent do not run.

## Configuration

Copy `.env.example` to `.env` and fill in the values. `.env` is git-ignored.

| Variable | Used by |
|----------|---------|
| `OPENROUTER_API_KEY` | agent |
| `CODEMENTOR_MODEL` | agent (model id on OpenRouter) |
| `CODEMENTOR_BASE_URL` | ticket tests |

## TODO

- [ ] Add the Maven Wrapper (`mvnw`) to `template/` (needs network; blocked on 11 Nov).
- [ ] Verify the full Docker path: `docker compose up --build` in `template/` and the
      ticket 0–1 tests against it, including Flyway migrations. On 11 Nov only an offline
      run was possible (local Maven cache, schema applied with `psql`). If the local network
      is still too slow, verify in GitHub Actions on 13–14 Nov.

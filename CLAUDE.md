# CLAUDE.md — instructions for the coding agent

## Project

CodeMentor: a training platform where a junior developer joins an existing
Java/Spring backend project, fixes realistic bugs (tickets) in their own GitHub
repository, and gets hints from an AI mentor agent on every pull request.
Full plan: `PLAN.md`. Read it before starting a task.

This is a university final project (AI course). It is graded on: a working
end-to-end product, a substantive AI feature with an evaluation, engineering
quality (README, tests, no secrets), and an honest record of how I worked with
you. I must be able to explain every line, so keep code simple and readable.

## Communication

- Talk to me in **Russian**. Write code, comments, commit messages and repo
  docs in **English**.
- Before a larger change, show a short plan and wait for my OK.
- When you make a non-obvious decision, or I correct you, propose an entry for
  `DECISIONS.md` (what, why, alternatives, where you were wrong).
- Explain what you did in a few sentences after each task, so I can defend it.

## Repository layout

- `template/` — Java/Spring orders service that the student receives.
- `tickets/` — student-facing ticket descriptions.
- `tests/tickets/` — protected black-box tests per ticket (pytest + requests).
- `agent/` — the AI mentor agent (Python).
- `eval/` — seeded bugs, labels, eval runner, rubric, results.
- `.github/workflows/check.yml` — reusable workflow (`on: workflow_call`).

## Stack

- Template: Java 21, Spring Boot 3, Maven, Spring Data JPA, Flyway, PostgreSQL,
  Docker Compose.
- Agent, tests, eval: Python 3.11+, `openai` SDK with OpenRouter `base_url`,
  pytest, requests.

## Hard rules

1. **Never "fix" the intentional ticket bugs in `template/`.** They are the
   tickets. Describe them only in `eval/bugs/labels.yaml`, never in comments
   in the template code (the student must not see hints there).
2. **Tests are black-box.** They talk to the service only over HTTP as
   described in `template/CONTRACT.md`. Never import or inspect the Java code
   from tests.
3. **The agent never gives solution code.** Hints only. It is read-only on the
   student repository: no writes, no commits.
4. **Agent limits:** max 10 tool calls per run; file tools restricted to the
   repository root; tools per mode as in PLAN.md section 3.
5. **No secrets in git.** Keys only from environment variables
   (`OPENROUTER_API_KEY`, `CODEMENTOR_MODEL`). Keep `.env` in `.gitignore`,
   commit `.env.example`. Never print keys in logs.
6. The LLM model must be configurable through `CODEMENTOR_MODEL`, never
   hard-coded.
7. Agent unit tests use a fake LLM client: no network calls in tests.
8. Keep the scope of `PLAN.md`. Stretch goals only when I ask.

## Commands

(Update this section as the project grows.)

- Run template: `cd template && docker compose up --build`
- Test deps (Windows: `py` instead of `python`): `python -m venv .venv && .venv/Scripts/python -m pip install -r tests/requirements.txt`
- Ticket tests: `pytest tests/tickets/ticket_1 -v` (needs the service running on localhost:8080,
  or set `CODEMENTOR_BASE_URL`). On the untouched template, ticket tests are expected to fail.
- Check reference patches: `git apply --check --directory=template eval/reference/ticket-0.patch`
- Agent tests: `pytest agent/tests -v`
- Eval: `python eval/run_eval.py --model <model>`

## Style

- Small functions, clear names, no clever tricks.
- Java: standard Spring layering (controller → service → repository).
  The template should look like a realistic, slightly messy project, but still
  readable.
- Python: type hints, `pathlib`, no heavy frameworks for the agent loop.

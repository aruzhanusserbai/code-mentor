# PLAN — CodeMentor: AI-Reviewed Project-Based Backend Training

Author: Aruzhan Usserbai
Written: 11 Nov 2026, before any code.

## 1. Problem and user

Junior developers often pass technical interviews but struggle with real work.
Senior developers I interviewed named two skills juniors lack most:
**debugging** and **reading other people's code**. Most learning platforms teach
writing code from scratch, which trains neither.

**User:** students and junior backend developers (Java) who want hands-on,
job-like experience.

**Idea:** the student joins an *existing* backend project, like a new developer
on a team, and solves realistic tickets (bugs) in their own GitHub repository.
Fixing bugs in an unfamiliar codebase trains both skills. An AI mentor agent
reviews every pull request and guides the student with hints, never solutions.

## 2. User flow (MVP)

1. The student creates their own repository from the **template repository**
   ("Use this template"), clones it and runs it with `docker compose up`.
2. The student reads the ticket (Markdown in `tickets/`), creates a branch,
   fixes the bug and opens a pull request.
3. GitHub Actions starts the project and runs the **protected black-box tests**
   for that ticket. The tests live in the platform repository, not in the
   student's repository, so the student cannot change them.
4. **Tests fail** → the agent runs in *debugging mode*: it investigates the code,
   logs and test output and posts a hint in the PR. Each new failed attempt gets
   a more specific hint (level 1 nudge → level 2 location → level 3 concept).
   Never solution code.
5. **Tests pass** → the agent runs in *review mode*: it asks 2–3 questions about
   the fix ("why did it fail with 500?", "why 400 and not 404?").
6. The student answers in a PR comment → the agent evaluates the answers
   (*answer mode*). If they are good, it adds the label `ticket-N-done`.

## 3. Architecture

Two parts, developed in one repository (`codementor`, this repo):

```
codementor/
├── template/            Java/Spring orders service = what the student gets.
│                        Working, slightly "legacy", with the ticket bugs inside.
│                        Published later as a separate GitHub template repository.
├── tickets/             ticket-0.md, ticket-1.md, ticket-2.md (student-facing text)
├── tests/tickets/       protected black-box tests per ticket (pytest + requests, HTTP only)
├── agent/               AI mentor agent (Python)
│   ├── tools.py         list_files, read_file, get_logs, run_test, post_comment
│   ├── loop.py          tool-use loop, max steps, mode selection
│   ├── prompts/         system prompt per mode
│   └── tests/           unit tests for the agent (fake LLM, no network)
├── eval/
│   ├── reference/       how to build the bug-free reference solution
│   ├── bugs/            15 seeded bugs as patch files + labels.yaml (file, line, cause)
│   ├── run_eval.py      runs the agent (and the ChatGPT baseline) on every bug
│   ├── rubric.md        hint usefulness rubric (1–5)
│   └── results/         result tables per model
├── .github/workflows/   reusable workflow `check.yml` (on: workflow_call)
├── PLAN.md  CLAUDE.md  DECISIONS.md  REFLECTION.md  README.md
└── agent-logs/          3–5 key Claude Code sessions
```

The template repository contains only a short caller workflow:

```yaml
on: [pull_request, issue_comment]
jobs:
  check:
    uses: <github-user>/codementor/.github/workflows/check.yml@main
    secrets: inherit
```

### The training project (template)

- Orders service for a small online shop: Java 21, Spring Boot 3, Maven,
  Spring Data JPA, Flyway, PostgreSQL, Docker Compose.
- Endpoints: `GET /actuator/health`, `POST /orders`, `GET /orders/{id}`,
  `GET /orders`, `GET /products`.
- Contract (ports, endpoints, request/response format) in `template/CONTRACT.md`.
  Tests talk to the service only over HTTP, so they do not depend on how the
  student structures the code.

### Tickets (MVP)

| # | Ticket | Skill |
|---|--------|-------|
| 0 | Set up the workplace: run the project, open the first PR | git, PR flow |
| 1 | "Checkout with an empty cart returns 500" → must be 400 with an error message | reading code, validation, HTTP status codes |
| 2 | "Order total is wrong for orders with several items" | debugging business logic |

Ticket bugs are **intentional** and stay in the template.

### The agent

- Python, `openai` SDK pointed at the OpenRouter API (`base_url`).
- Model from env `CODEMENTOR_MODEL`; key from env `OPENROUTER_API_KEY`.
- One agent, three modes. **The workflow chooses the mode**, not the agent:

| Mode | Trigger | Tools |
|------|---------|-------|
| debugging | PR, tests failed | list_files, read_file, get_logs, run_test, post_comment |
| review | PR, tests passed | list_files, read_file, post_comment |
| answer | PR comment by the PR author | read_file, post_comment (+ add label) |

- Limits: max 10 tool calls per run; file tools are read-only and restricted
  to the student repository; the agent never writes code to the repository.
- **Stateless hint levels:** each agent comment carries a hidden marker such as
  `<!-- codementor:ticket=1;mode=debugging;level=2 -->`. The next run reads
  earlier comments to pick the next level. No database.
- Ignore comments written by bots or by anyone other than the PR author.

## 4. Evaluation of the AI feature

- **Dataset:** a bug-free reference solution + 15 seeded bugs, each stored as a
  patch with a label (file, line, cause). The 2 ticket bugs are part of the 15.
  Mix: validation, wrong status code, business logic, null handling, SQL/JPA
  query, transaction, config.
- For each bug: apply the patch → start the service → run the tests → run the
  agent in debugging mode (level 1 and level 3) → save the output.
- **Metrics:**
  - Detection rate: cause and location identified correctly (vs labels).
  - No-spoiler rate: hint contains no solution code (automatic check + manual review).
  - Hint usefulness: 1–5 by `rubric.md`.
- **Baseline:** the same failing test output + code given to plain ChatGPT with
  a simple prompt ("find the bug").
- Compare 2–3 models via OpenRouter (one free, one cheap paid, one strong).
- Results in `eval/results/` and summarized in README.

## 5. Tools and budget

- Development: Claude Code (paid).
- Product LLM: OpenRouter. Free tool-use models while developing; paid model
  (Claude Haiku/Sonnet) for the final eval and demo. Spending limit set on the key.
- No secrets in git: `.env` is git-ignored, `.env.example` is committed,
  CI uses GitHub Secrets.

## 6. Timeline

| Dates | Goal |
|-------|------|
| 11–12 Nov | Repo skeleton, PLAN.md, CLAUDE.md. Template Spring project with ticket 0 and the ticket 1 bug. Tests for tickets 0–1. |
| 13–14 Nov | Reusable workflow: start the project in Actions, run ticket tests. Agent v0: debugging mode, posts one PR comment. |
| 15–16 Nov | **Checkpoint:** end-to-end on a test student repository (PR → tests → agent comment). First agent logs. |
| 17–23 Nov | Ticket 2. Hint levels. Review mode and answer mode. Agent unit tests. |
| 24–30 Nov | Eval: reference solution, 15 bug patches with labels, `run_eval.py`, rubric, ChatGPT baseline. |
| 1–6 Dec | Eval runs on 2–3 models, README from a clean machine, DECISIONS.md, REFLECTION.md. Tag `v1.0`. **Code freeze 6 Dec.** |
| 7–19 Dec | Defense: live demo + 2–3 min backup video. |

## 7. Stretch goals (only after v1.0 scope works)

1. A simple static site: project introduction, architecture, ticket pages.
2. "AI colleague" ticket: the agent opens a PR with a hidden issue and the
   student finds it in code review.

## 8. Known limitations (accepted for MVP)

- The student's repository needs its own `OPENROUTER_API_KEY` secret. A real
  product would use a GitHub App or a backend that holds the key.
- Tests cannot be changed by the student but are readable, because the
  platform repository is public. Truly hidden tests need a private repo + GitHub App.
- One training project, three tickets.

## 9. Required course files

README.md · PLAN.md · CLAUDE.md · agent-logs/ (3–5 sessions) · DECISIONS.md ·
REFLECTION.md · tests · evaluation. No secrets in git history.

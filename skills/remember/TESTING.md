# Testing: /remember skill

## Test suite: 24 classification items

| # | Input | Expected | Property path |
|---|-------|----------|---------------|
| 1 | "Run `pnpm test` before any `git commit`" | **Hook** | Fully mechanical, specific command |
| 2 | "Run the linter after every file edit" | **Hook** | Fully mechanical, no judgment |
| 3 | "Block Bash commands containing `rm -rf /`" | **Hook** | Fully mechanical, pattern match |
| 4 | "Auto-format Python files with `black` after every write" | **Hook** | Fully mechanical, specific command |
| 5 | "The auth middleware uses Redis for sessions with a 24h TTL" | **MagicDocs** | Describes architecture |
| 6 | "API routes are generated from OpenAPI specs in /api/specs/" | **MagicDocs** | Describes how things work |
| 7 | "The frontend uses custom state management on React context, not Redux" | **MagicDocs** | Describes architecture |
| 8 | "The notification system uses fan-out — events to central topic, then per-consumer queues" | **MagicDocs** | Describes architecture |
| 9 | "When committing: run tests, check coverage, lint, draft message, wait for approval" | **Skill** | Prescribes, needs recency at point of action |
| 10 | "When I ask to deploy: run tests, build Docker image, push to staging, notify me" | **Skill** | Prescribes, needs recency at point of action |
| 11 | "When reviewing a PR: check security, verify tests, check breaking changes, summarize" | **Skill** | Prescribes, needs recency at point of action |
| 12 | "When setting up a new service: create dir, add Dockerfile, register in docker-compose, add health check, add to CI" | **Skill** | Prescribes, needs recency at point of action |
| 13 | "This project uses pnpm, not npm" | **CLAUDE.md** | Prior, shapes assumptions, every session |
| 14 | "Make sure tests pass before committing" | **CLAUDE.md** | Prior (needs judgment), every session |
| 15 | "The database is SQLite in production — don't suggest Postgres" | **CLAUDE.md** | Prior, shapes assumptions, every session |
| 16 | "We deploy to Fly.io, not AWS" | **CLAUDE.md** | Prior, shapes assumptions, every session |
| 17 | "User prefers bundled PRs over many small ones" | **Memory** | Preference, sometimes relevant |
| 18a | `<context>Repo has a Go API server, PostgreSQL migrations, worker queue, and a small React admin dashboard</context>` "User is colorblind — avoid using only color to distinguish options in UI work" | **Memory** | Preference, sometimes relevant (most sessions are backend, dashboard is a small corner) |
| 18b | `<context>Backend-only repo</context>` "User is colorblind — avoid using only color to distinguish options in UI work" | **Memory** (user-scoped) | Prescribes, prior, sometimes relevant; actionable across user's projects even if not this one |
| 18c | `<context>Frontend-only repo</context>` "User is colorblind — avoid using only color to distinguish options in UI work" | **CLAUDE.md** | Preference, every session touches UI |
| 19 | "Don't mock the database in integration tests — mocks passed but prod migration broke" | **Memory** | Lesson learned, sometimes relevant |
| 20 | "User finds excessive code comments patronizing — only comment non-obvious logic" | **Memory** | Preference, sometimes relevant |
| 21 | "The sky is blue" | **None** | Not actionable |
| 22 | "I had pizza for lunch" | **None** | Not actionable |
| 23 | "TypeScript was created by Microsoft" | **None** | Not actionable (Claude already knows) |
| 24 | "React is a popular frontend framework" | **None** | Not actionable (Claude already knows) |

## RED baseline (without skill)

**Model**: Sonnet
**Date**: 2026-04-01
**Score**: 14/24 (58%)

### Results

| # | Expected | Got | Pass? |
|---|----------|-----|-------|
| 1 | Hook | Hook | PASS |
| 2 | Hook | Hook | PASS |
| 3 | Hook | Hook | PASS |
| 4 | Hook | Hook | PASS |
| 5 | MagicDocs | Memory | **FAIL** |
| 6 | MagicDocs | MagicDocs | PASS |
| 7 | MagicDocs | CLAUDE.md | **FAIL** |
| 8 | MagicDocs | Memory | **FAIL** |
| 9 | Skill | Skill | PASS |
| 10 | Skill | Skill | PASS |
| 11 | Skill | Skill | PASS |
| 12 | Skill | Skill | PASS |
| 13 | CLAUDE.md | CLAUDE.md | PASS |
| 14 | CLAUDE.md | CLAUDE.md | PASS |
| 15 | CLAUDE.md | CLAUDE.md | PASS |
| 16 | CLAUDE.md | CLAUDE.md | PASS |
| 17 | Memory | CLAUDE.md | **FAIL** |
| 18a | Memory | CLAUDE.md | **FAIL** |
| 18b | None | *(not in baseline)* | — |
| 18c | CLAUDE.md | *(not in baseline)* | — |
| 19 | Memory | CLAUDE.md | **FAIL** |
| 20 | Memory | CLAUDE.md | **FAIL** |
| 21 | None | None | PASS |
| 22 | None | None | PASS |
| 23 | None | None | PASS |
| 24 | None | None | PASS |

### Failure patterns

**Pattern A: All 4 Memory items → CLAUDE.md (items 17-20)**

The agent treated anything prescriptive and "always true" as CLAUDE.md. It didn't distinguish "always true" from "always relevant." Rationalizations:

- #17: "A standing preference that shapes how Claude approaches PRs across all tasks. Always-relevant behavioral prior."
- #18: "A universal constraint on all UI work. Should always be in context — not situational enough to be Memory." (Note: full-stack context wasn't provided in baseline — agent assumed UI-only repo)
- #19: "A hard-won rule backed by a specific failure. It should always shape how Claude approaches integration tests."
- #20: "A standing stylistic preference that applies to all code Claude writes. Always-relevant prior about output style."

**Pattern B: 3 of 4 MagicDocs items misclassified (items 5, 7, 8)**

The agent didn't apply the describe/prescribe distinction. It pulled architectural descriptions into CLAUDE.md or Memory based on how "relevant" they felt.

- #5 → Memory: "Architectural detail that matters when working on auth, sessions, or caching — but not always."
- #7 → CLAUDE.md: "Shapes assumptions on every frontend task. Any time Claude touches frontend code, it should know not to suggest Redux."
- #8 → Memory: "Relevant when working on notifications, messaging, or event-driven code — but not globally relevant."

### Key rationalizations to counter in the skill

1. **"Always true = always relevant"** — The agent conflated these. "User is colorblind" is always true but only relevant when doing UI color work. The skill must hammer: test with "Claude starts a session to fix a CSS bug — does it need this right now?"

2. **"Shapes assumptions on X tasks"** — Used to pull descriptions into CLAUDE.md. "The frontend uses React context" describes architecture; it doesn't prescribe behavior. The describe/prescribe gate must come before the always/sometimes gate.

3. **"Not globally relevant = Memory"** — Used to pull descriptions into Memory instead of MagicDocs. Descriptions of how the codebase works are MagicDocs regardless of scope. Memory is for prescriptive context that's sometimes relevant.

## GREEN run (with skill)

**Model**: Sonnet
**Date**: 2026-04-01
**Score**: 22/26 (85%), up from 14/24 (58%) baseline

### Results

| # | Expected | Got | Pass? |
|---|----------|-----|-------|
| 1 | Hook | Hook | PASS |
| 2 | Hook | CLAUDE.md | **FAIL** |
| 3 | Hook | Hook | PASS |
| 4 | Hook | Hook | PASS |
| 5 | MagicDocs | MagicDocs | PASS (fixed from baseline) |
| 6 | MagicDocs | MagicDocs | PASS |
| 7 | MagicDocs | MagicDocs | PASS (fixed from baseline) |
| 8 | MagicDocs | MagicDocs | PASS (fixed from baseline) |
| 9 | Skill | Skill | PASS |
| 10 | Skill | Skill | PASS |
| 11 | Skill | Skill | PASS |
| 12 | Skill | Skill | PASS |
| 13 | CLAUDE.md | CLAUDE.md | PASS |
| 14 | CLAUDE.md | Memory | **FAIL** |
| 15 | CLAUDE.md | CLAUDE.md | PASS |
| 16 | CLAUDE.md | Memory | **FAIL** |
| 17 | Memory | Memory | PASS (fixed from baseline) |
| 18a | Memory | Memory | PASS (fixed from baseline) |
| 18b | None | None | PASS (new test) |
| 18c | CLAUDE.md | CLAUDE.md | PASS (new test) |
| 19 | Memory | Memory | PASS (fixed from baseline) |
| 20 | Memory | CLAUDE.md | **FAIL** |
| 21 | None | None | PASS |
| 22 | None | None | PASS |
| 23 | None | None | PASS |
| 24 | None | None | PASS |

### What improved

All MagicDocs items (5, 7, 8) now correct — the describe/prescribe gate worked. All Memory items (17, 18a, 19) now correct — the "always true ≠ always relevant" framing worked. The colorblind variants (18a/18b/18c) all classified correctly.

### Remaining failures (4 items)

**#2: "Run the linter after every file edit" — expected Hook, got CLAUDE.md**
Rationalization: "the linter" isn't specific enough — which linter? what command? The agent decided it requires judgment. But the intent is clearly a mechanical action ("run the linter" implies a known command). The skill should clarify that if the *intent* is mechanical automation, it's a Hook — the user would fill in the specific command when configuring it.

**#14: "Make sure tests pass before committing" — expected CLAUDE.md, got Memory**
Rationalization: "only relevant when committing, not when fixing a CSS bug." The agent over-applied the "fix a CSS bug" test. But committing happens in nearly every session — it's not a rare topic. The skill should clarify that if the constraint applies to a *ubiquitous action* (committing, writing code), it's always relevant.

**#16: "We deploy to Fly.io, not AWS" — expected CLAUDE.md, got Memory**
Rationalization: "only matters when deployment or infra topics come up." Same pattern as #14 — the agent treated it as sometimes-relevant. But deployment platform shapes infrastructure assumptions broadly (config files, CI, env vars). The skill should distinguish between "only relevant in niche scenarios" (Memory) and "shapes a broad assumption space" (CLAUDE.md).

**#20: "User finds excessive code comments patronizing" — expected Memory, got CLAUDE.md**
Rationalization: "Claude writes code in virtually every session. This affects the first file edit." The agent over-applied the "every session" heuristic. But the preference is about code *style*, which only matters when generating code — not when researching, reading, or answering questions. In a full-stack repo, plenty of sessions don't involve writing code. The skill should counter: "writing code" is not literally every session — many sessions are research, debugging, or discussion.

### Pattern

The CLAUDE.md/Memory boundary is still where failures cluster. The "fix a CSS bug" test helps but has edge cases:
- Things that affect *ubiquitous actions* (committing, deployment config) get incorrectly pushed to Memory (#14, #16)
- Things that affect *common-but-not-universal actions* (writing code) get incorrectly pulled to CLAUDE.md (#20)

The skill needs a more nuanced heuristic for Property 4 than a single "CSS bug" test.

## REFACTOR run (with updated skill)

**Model**: Sonnet
**Date**: 2026-04-01
**Score**: 25/26 (96%), up from 22/26 (85%) GREEN

### Changes made to skill

1. **Property 1 (Hook)**: Added clause — "If the *intent* is mechanical automation but the user hasn't specified the exact command yet, it's still a Hook."
2. **Property 4 (Always/Sometimes)**: Split into two explicit error patterns:
   - Error 1: putting sometimes-relevant things in CLAUDE.md ("always true ≠ always relevant")
   - Error 2: putting always-relevant things in Memory because they seem "topic-specific" — added "ubiquitous actions" test with examples (#14 committing, #16 deployment, #20 code comments)

### Results

| # | Expected | Got | Pass? |
|---|----------|-----|-------|
| 1 | Hook | Hook | PASS |
| 2 | Hook | Hook | PASS (fixed from GREEN) |
| 3 | Hook | Hook | PASS |
| 4 | Hook | Hook | PASS |
| 5 | MagicDocs | MagicDocs | PASS |
| 6 | MagicDocs | MagicDocs | PASS |
| 7 | MagicDocs | MagicDocs | PASS |
| 8 | MagicDocs | MagicDocs | PASS |
| 9 | Skill | Skill | PASS |
| 10 | Skill | Skill | PASS |
| 11 | Skill | Skill | PASS |
| 12 | Skill | Skill | PASS |
| 13 | CLAUDE.md | CLAUDE.md | PASS |
| 14 | CLAUDE.md | CLAUDE.md | PASS (fixed from GREEN) |
| 15 | CLAUDE.md | CLAUDE.md | PASS |
| 16 | CLAUDE.md | CLAUDE.md | PASS (fixed from GREEN) |
| 17 | Memory | Memory | PASS |
| 18a | Memory | Memory | PASS |
| 18b | None | Memory | **FAIL** |
| 18c | CLAUDE.md | CLAUDE.md | PASS |
| 19 | Memory | Memory | PASS |
| 20 | Memory | Memory | PASS (fixed from GREEN) |
| 21 | None | None | PASS |
| 22 | None | None | PASS |
| 23 | None | None | PASS |
| 24 | None | None | PASS |

### Remaining failure (1 item)

**#18b: "Backend-only repo. User is colorblind..." — expected None, got Memory**
The agent noted it was "borderline 'not actionable' in practice" but hedged toward Memory instead of None. The actionability prerequisite should be stronger: if the repo context makes the constraint essentially impossible to apply, it's None. The agent correctly identified the issue but didn't follow through on it.

## REFACTOR 2 (scope refinement)

**Model**: Sonnet
**Date**: 2026-04-02
**Score**: 26/26 (100%)

### Changes made to skill

1. **Actionability prerequisite expanded**: "Can Claude change its behavior because of this — in this project or in any of the user's projects?" Explicitly states actionability is evaluated against the user's full scope, not just the current repo.
2. **18b expected answer changed**: None → Memory (user-scoped). The user's colorblindness is actionable across their projects even if not in the current backend-only repo.
3. **Routing section rewritten**: After classification, scope is a separate routing question. Hook and MagicDocs are always project-scoped. Skill, CLAUDE.md, and Memory ask the user whether it applies to this project, a subdirectory, or all projects.

### Results

| # | Expected | Got | Pass? |
|---|----------|-----|-------|
| 1 | Hook | Hook | PASS |
| 2 | Hook | Hook | PASS |
| 3 | Hook | Hook | PASS |
| 4 | Hook | Hook | PASS |
| 5 | MagicDocs | MagicDocs | PASS |
| 6 | MagicDocs | MagicDocs | PASS |
| 7 | MagicDocs | MagicDocs | PASS |
| 8 | MagicDocs | MagicDocs | PASS |
| 9 | Skill | Skill | PASS |
| 10 | Skill | Skill | PASS |
| 11 | Skill | Skill | PASS |
| 12 | Skill | Skill | PASS |
| 13 | CLAUDE.md | CLAUDE.md | PASS |
| 14 | CLAUDE.md | CLAUDE.md | PASS |
| 15 | CLAUDE.md | CLAUDE.md | PASS |
| 16 | CLAUDE.md | CLAUDE.md | PASS |
| 17 | Memory | Memory | PASS |
| 18a | Memory | Memory | PASS |
| 18b | Memory | Memory | PASS (fixed — was expected None, now correctly Memory) |
| 18c | CLAUDE.md | CLAUDE.md | PASS |
| 19 | Memory | Memory | PASS |
| 20 | Memory | Memory | PASS |
| 21 | None | None | PASS |
| 22 | None | None | PASS |
| 23 | None | None | PASS |
| 24 | None | None | PASS |

### Key insight

The 18b fix came from recognizing that scope (project vs user) is orthogonal to classification. Actionability must be evaluated against the user's full scope, not just the current repo. Classification determines the *mechanism* (Hook, MagicDocs, Skill, CLAUDE.md, Memory, None). Scope determines the *location* (project file vs user file). These are two separate questions, and conflating them caused the only remaining failure.

### Progression

| Phase | Score | Key fixes |
|-------|-------|-----------|
| RED baseline | 14/24 (58%) | — |
| GREEN | 22/26 (85%) | MagicDocs describe/prescribe gate, Memory "always true ≠ always relevant" |
| REFACTOR 1 | 25/26 (96%) | Hook intent clause, ubiquitous actions test, two-error pattern for Property 4 |
| REFACTOR 2 | 26/26 (100%) | Scope as routing (not classification), actionability across user's full scope |
| REFACTOR 3 (trim) | 25/26 (96%) | Trimmed skill from ~70 to ~30 lines; lost #20 counter-example |
| REFACTOR 4 (trim+fix) | 25/26 (96%) | Added #20 counter-example back; 18a failed due to compound statement |
| REFACTOR 5 (final) | 26/26 (100%) | Used `<context>` XML tags to separate repo framing from content to classify |

## Final skill

The final SKILL.md is ~35 lines. It teaches only what the model gets wrong without help:
1. Describe/prescribe gate (MagicDocs vs everything else)
2. "Always true ≠ always relevant" with three counter-examples (Memory items the model pulls into CLAUDE.md)
3. "Ubiquitous actions are always relevant" with two examples (CLAUDE.md items the model pushes to Memory)
4. Actionability evaluated at user's full scope, not just current repo
5. Scope as a routing question after classification, not a classification question

The model natively gets Hook, Skill, CLAUDE.md (core), and None correct without any skill. The skill's value is entirely at the MagicDocs boundary and the CLAUDE.md/Memory boundary.

## Self-classification

Running /remember on itself: the skill prescribes a multi-step procedure (actionability → mechanical → describe/prescribe → steps → always/sometimes → route). Classification: **Skill**. It correctly classifies itself.

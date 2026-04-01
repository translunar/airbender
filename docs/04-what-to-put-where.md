# What to Put Where

Claude Code has five mechanisms for customizing its behavior: CLAUDE.md, skills, memory, hooks, and MagicDocs. They all feel like "tell Claude what to do," but they have fundamentally different injection points, survival characteristics, and effectiveness profiles. Putting an instruction in the wrong place doesn't just waste tokens — it often means the instruction doesn't work.

## The five mechanisms at a glance

| Mechanism | When injected | Where in context | Survives compaction? | Relevance-filtered? | You control content? |
|---|---|---|---|---|---|
| CLAUDE.md | Session start | System prompt, late section (8 or 9) | Yes (always present) | No (all or nothing) | Yes (verbatim) |
| Skills | On demand, mid-conversation | Tool result | No (but doesn't need to) | Yes (`when_to_use`) | Yes (you write them) |
| Memory | Session start, selective | System-reminder tags | Varies | Yes (LLM picks top 5) | Yes (but system-managed) |
| Hooks | Pre/post tool use | Outside LLM context | N/A (mechanical) | N/A | Yes (shell commands) |
| MagicDocs | Post-conversation | Updated files on disk | N/A (persisted to files) | N/A (auto-generated) | No (internal feature) |

[source: `prompt.rs` for CLAUDE.md placement](https://github.com/instructkr/claw-code/blob/main/rust/crates/runtime/src/prompt.rs), [`compact.rs` for compaction behavior](https://github.com/instructkr/claw-code/blob/main/rust/crates/runtime/src/compact.rs)

## CLAUDE.md: environmental context

CLAUDE.md files are concatenated into one of the later sections of the system prompt (section 8 or 9, depending on whether an output style is configured). The content is preserved with minimal processing — whitespace is trimmed and a path-based header is added, but the substantive content is unchanged. No summarization, no relevance filtering. Every token is present on every API call for the entire session.

[source: `prompt.rs` — `render_instruction_files()` showing concatenation with trim and path headers](https://github.com/instructkr/claw-code/blob/main/rust/crates/runtime/src/prompt.rs)

**Good at**: Environmental facts that prevent wrong assumptions before any reasoning starts — the package manager, the deploy target, the database choice, the shape of the codebase. Terminology grounding. Invariants that should never be violated. Pointers to where other information lives ("architectural docs are in docs/magic/", "review skill enforces coding standards").

**Bad at**: Multi-step workflows. Conditional logic ("if X, then do Y"). Long examples. Behavioral rules you want reliably enforced. Instructions that conflict with Anthropic's built-in behavioral rules in sections 1-5.

**Why**: CLAUDE.md is static, always present, and unfiltered. It's positioned after five sections of Anthropic's own instructions. It sets priors — the baseline assumptions the model carries into every action. But it doesn't trigger specific behaviors at specific moments. By the time Claude is performing a task, the CLAUDE.md content may be thousands of tokens away from where the model is currently attending. And critically, CLAUDE.md has no verification loop — there is no mechanism that checks whether a CLAUDE.md instruction actually changed behavior (see [Chapter 2: the verification gap](02-context-engineering.md#whats-missing-verification)).

### Bad example: workflow in CLAUDE.md

```markdown
# CLAUDE.md
When fixing a bug, always reproduce it first, then write a failing test,
then fix the code, then verify the test passes.
```

*Why it's bad: By the time Claude is fixing a bug, this instruction is thousands of tokens away. It reads it at session start but doesn't reliably follow multi-step procedures from the system prompt. In a long conversation, it may be further diluted by compaction of surrounding context.*

### Good example: invariant in CLAUDE.md

```markdown
# CLAUDE.md
This project uses pnpm, not npm or yarn. All package commands use pnpm.
```

*Why it works: Claude would otherwise guess `npm` — it's the most common package manager. This instruction prevents a wrong assumption before any reasoning happens. It's short, always relevant, and impossible to follow "at the wrong time."*

## Skills: direct orders at the right moment

Skills are loaded via the `SkillTool` mid-conversation. Their content arrives as a tool result — the most authoritative position in a conversation, right at the point of action.

[source: `system-prompt-skillify-current-session.md` for skill structure and `when_to_use` criticality](https://github.com/Piebald-AI/claude-code-system-prompts/blob/main/system-prompts/system-prompt-skillify-current-session.md)

**Why they outperform CLAUDE.md:**
- **Recency**: Injected at the point of action, not thousands of tokens ago at session start
- **Specificity**: Targeted to the current task, not a blob covering everything
- **Authority**: Tool results carry strong instruction-following weight — the model treats them as direct, authoritative instructions

**What belongs in skills**: Workflows, checklists, verification procedures, structured output formats, anything with "when X happens, do Y" logic.

### Bad example: static fact in a skill

```markdown
---
when_to_use: When working in this project
---
This project uses PostgreSQL 16 and runs on Node 22.
```

*Why it's bad: This consumes a skill invocation for information that should be a CLAUDE.md one-liner. Skills are for procedures, not facts. And `when_to_use: "When working in this project"` is too vague to trigger reliably — it matches everything and nothing.*

### Good example: procedure in a skill

```markdown
---
when_to_use: When committing code or the user asks to commit
---
Before committing:
1. Run `pnpm test` and confirm all tests pass
2. Run `pnpm lint` and fix any issues
3. Draft a commit message following conventional commits
4. Show the user the message and wait for approval
```

*Why it works: The `when_to_use` field is specific — it triggers when committing, not all the time. The content arrives at the exact moment Claude is about to commit, with step-by-step instructions it follows reliably. After the commit is done, the skill content can be compacted away without loss.*

## Memory: persistent cross-conversation context

Memory files persist across conversations, but only a subset is loaded into any given session. A Sonnet subagent reads memory file descriptions and picks up to 5 relevant ones per conversation.

[source: `agent-prompt-determine-which-memory-files-to-attach.md` for selection logic](https://github.com/Piebald-AI/claude-code-system-prompts/blob/main/system-prompts/agent-prompt-determine-which-memory-files-to-attach.md)

**Key characteristics:**
- Selection is LLM-based, not vector search — the subagent reads descriptions and judges relevance
- Memory types (user, feedback, project, reference) each serve a different purpose
- The dream consolidation agent periodically cleans up: merging, deduplicating, removing contradictions
- Memory descriptions are the selection index — vague descriptions mean the memory is never selected

### Bad example: vague description

```markdown
---
name: project-notes
description: Some notes about the project
type: project
---
The API uses rate limiting with a sliding window. Limits are per-endpoint,
backed by Redis. The default is 100 req/min for authenticated users,
10 req/min for anonymous.
```

*Why it's bad: The content is valuable, but the description "some notes about the project" won't match any specific query. When the user asks about rate limits or Redis configuration, the memory selection agent has no keywords to match on. This memory will sit unused.*

### Good example: specific description

```markdown
---
name: api-rate-limiting
description: API rate limiting configuration — sliding window, Redis-backed, per-endpoint limits, 100/min authenticated, 10/min anonymous
type: project
---
The API uses rate limiting with a sliding window. Limits are per-endpoint,
backed by Redis. The default is 100 req/min for authenticated users,
10 req/min for anonymous.
```

*Why it works: The description contains the keywords that matter — "rate limiting", "Redis", "per-endpoint", "authenticated", "anonymous". When the user asks about any of these topics, the memory selection agent can match on the description and load the full content.*

## Hooks: automated guardrails

Hooks are shell commands that run at specific lifecycle events — before or after tool use, when a session starts or stops, around compaction. They execute mechanically, outside the LLM context. Claude doesn't decide whether to run them; they just run.

[source: `system-prompt-hooks-configuration.md` for hook schema](https://github.com/Piebald-AI/claude-code-system-prompts/blob/main/system-prompts/system-prompt-hooks-configuration.md), [`config.rs` for config loading](https://github.com/instructkr/claw-code/blob/main/rust/crates/runtime/src/config.rs)

**Good for**: Mechanical enforcement that should happen regardless of what Claude is doing — auto-formatting, type checking, linting, blocking dangerous operations.

**Not for**: Behavioral instructions (use skills), project context (use CLAUDE.md), persistent knowledge (use memory).

### Bad example: trying to change Claude's behavior via hook

This hook tries to remind Claude to write tests before any Bash command. The intent is to enforce a "tests first" workflow:

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Bash",
      "hooks": [{
        "type": "command",
        "command": "echo '{\"systemMessage\": \"Remember to write tests first\"}'"
      }]
    }]
  }
}
```

*Why it's bad: This fires before every single Bash command — `ls`, `git status`, `npm install` — not just commands that write code. And the `systemMessage` from a hook arrives as system feedback in the tool context, not as a structured behavioral instruction. Claude sees the reminder but doesn't reliably change its approach. If you want Claude to follow a testing workflow, write a skill with `when_to_use: "When implementing a feature or fixing a bug"` — that way the instruction arrives at the right moment with step-by-step structure.*

### Good example: mechanical enforcement as hook

```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Write|Edit",
      "hooks": [{
        "type": "command",
        "command": "cd $PROJECT_DIR && pnpm lint --fix $FILEPATH 2>&1 | tail -5"
      }]
    }]
  }
}
```

*Why it works: After every file write or edit, the linter runs automatically. There's no reliance on Claude remembering to lint — it happens mechanically every time. If the linter finds issues, the output flows back as tool feedback and Claude sees what needs fixing.*

## MagicDocs: auto-maintained architectural documentation

MagicDocs is an **internal Anthropic feature** — a post-conversation Sonnet subagent that automatically updates architectural documentation files. It is not currently available as a public Claude Code feature. We discuss it here because its philosophy illustrates the right division of labor between mechanisms, and because you can replicate its behavior yourself using skills and hooks (see [Chapter 5: Building MagicDocs](05-building-magicdocs.md)).

The key principle from MagicDocs is that **architectural knowledge should live in auto-maintained files, not in CLAUDE.md.** CLAUDE.md is for constraints and preferences that affect Claude's behavior. Architecture descriptions go stale; constraints don't.

[source: `agent-prompt-update-magic-docs.md` for the philosophy](https://github.com/Piebald-AI/claude-code-system-prompts/blob/main/system-prompts/agent-prompt-update-magic-docs.md)

### Bad example: architectural description in CLAUDE.md

```markdown
# CLAUDE.md
The auth middleware is in src/middleware/auth.ts. It talks to Redis
for session storage. The session TTL is 24h. The middleware chain
runs in order: cors → rateLimit → auth → validate → handler.
Sessions are stored with prefix "sess:" in Redis key space 2.
```

*Why it's bad: This is architectural documentation that will go stale the moment someone changes the middleware chain or the Redis key prefix. It belongs in a separate architectural doc (a "Magic Doc") that gets updated regularly — either automatically or via a skill. In CLAUDE.md, it's a maintenance burden you'll forget to update.*

### Good example: CLAUDE.md states a constraint

```markdown
# CLAUDE.md
The auth middleware session TTL is a compliance-sensitive value.
Always flag TTL changes in PR descriptions for security review.
```

*Why it works: This is a behavioral constraint — it tells Claude what to do (flag TTL changes) rather than describing architecture. Claude can follow this instruction directly by including a note in PR descriptions. Compare this to "check with the security team," which Claude can't actually do. Constraints in CLAUDE.md should be actions Claude itself can take.*

## Descriptions are selection indices

There's a cross-cutting pattern that applies to every mechanism with a selection step: **the description field is a search index, not documentation.** The entire architecture uses a two-stage pattern — cheap filter on a description field, then expensive load of full content. If the description doesn't match, the content is never loaded.

This applies to:

| Mechanism | Selection field | Who reads it | Bad description | Good description |
|---|---|---|---|---|
| Skill | `when_to_use` | Skill matching system | "Use when helpful" | "Use when committing code or the user asks to commit" |
| Memory | `description` in frontmatter | Memory selection agent (Sonnet) | "Some project notes" | "API rate limiting — sliding window, Redis, per-endpoint" |
| Deferred tool | Tool name + description | `ToolSearchTool` | "A tool" | "Browser automation for Chrome tabs" |
| MagicDoc | Document title | MagicDocs update agent | "Notes" | "Authentication Middleware Architecture" |

If your skill isn't auto-triggering, your memory isn't getting attached, or your deferred tool isn't loading — **the first thing to check is the description, not the content.** Write descriptions like trigger conditions or search keywords, not prose documentation.

## Decision tree

When you have an instruction, a preference, or a piece of knowledge you want Claude Code to use, classify it by its **properties** — not its topic. The same subject (e.g., "testing before commits") can belong in different places depending on the *form* of the information.

### Prerequisite: Is it actionable?

Before classifying, ask: **can Claude change its behavior because of this — in this project or in any of the user's projects?** If Claude can't do anything differently anywhere, it's **None** — regardless of how true or interesting the information is.

The test: can you describe what Claude would do *differently* with this information? "This project uses pnpm" → Claude runs `pnpm install` instead of `npm install`. "The sky is blue" → Claude does nothing differently. "Check with the security team" → Claude can't contact humans. "Be careful with X" → vague, no concrete behavior change.

Actionability is evaluated against the user's full scope, not just the current repo. "User is colorblind" is actionable even in a backend-only repo — it matters in their other projects. Classification determines the *mechanism* (Hook, Skill, CLAUDE.md, Memory, etc.); a separate routing step determines the *location* (which file, at what scope).

If the information isn't actionable anywhere, stop here. Otherwise, continue to the decision tree.

### The decision tree

The classification is grounded in how each mechanism works in the context window:

| Mechanism | Position in context | When active | What it's good for |
|-----------|-------------------|-------------|-------------------|
| CLAUDE.md | Early in system prompt | Before any reasoning starts | Priors that shape assumptions |
| Skill | Tool result, mid-conversation | At the moment of a specific action | Step-by-step guidance needing recency |
| Memory | System-reminder, selectively loaded | When the topic comes up | Context that matters sometimes |
| Hook | Outside LLM context entirely | Mechanically, every time | Enforcement without judgment |
| MagicDocs | Files on disk, loaded on demand | When exploring a subsystem | Architectural knowledge |

```
                     Can it be fully enforced
                     without Claude's judgment?
                    /                          \
                  yes                           no
                   |                             |
                 HOOK                  Describes how things work,
                                      or prescribes behavior?
                                     /                       \
                                describes                 prescribes
                                    |                         |
                               MAGIC DOCS           Does it need to be
                              (if available;      a prior (shape assumptions)
                              CLAUDE.md with      or fresh at point of action?
                              advisory if not)   /                        \
                                              prior                   at point
                                                |                     of action
                                         Always relevant                  |
                                         or sometimes?                  SKILL
                                        /            \
                                     always        sometimes
                                       |               |
                                  CLAUDE.md          MEMORY
```

### Property 1: Can it be fully enforced without Claude's judgment?

If the action is purely mechanical — a specific command, no interpretation needed, same behavior every time — it's a **hook**. Hooks are shell commands that run regardless of what Claude is doing.

The key word is **fully**. "Run `pnpm test` before any `git commit`" is fully mechanical — a hook can do this. "Make sure tests pass before committing" requires judgment (which tests? what about flaky ones? fix failures or just report?) — that's not a hook.

If the *intent* is mechanical automation but the user hasn't specified the exact command yet (e.g., "run the linter after every file edit"), it's still a hook — the user just needs to fill in the specific command for their hook config.

Examples: run `pnpm lint --fix` after every file edit, auto-format Python with `black` after every write, block Bash commands containing `rm -rf /`.

### Property 2: Does it describe or prescribe?

**Descriptions** of how the codebase works (architecture, entry points, how components connect) belong in **MagicDocs** — auto-maintained documentation that stays current. MagicDocs is an internal Anthropic feature, but you can build your own equivalent (see [next chapter](05-building-magicdocs.md)).

If the project doesn't have MagicDocs set up, architectural descriptions can go in CLAUDE.md as a pragmatic fallback — but they'll go stale without manual maintenance. The right response is to note that this is architectural documentation that would benefit from a MagicDocs setup.

**Prescriptions** for how Claude should behave (constraints, workflows, preferences) continue down the tree.

Examples of descriptions: "the auth middleware talks to Redis for session storage", "the frontend uses a custom state management layer built on React context, not Redux."

### Property 3: Prior or point-of-action?

This is the core context engineering question. The reason a commit workflow belongs in a skill isn't just that it "has steps" — it's that **procedures need recency to be followed reliably**. A procedure in CLAUDE.md is thousands of tokens away by the time Claude is acting. A skill arrives at the exact moment of action.

Conversely, "use pnpm not npm" works in CLAUDE.md because it's a **prior** — it needs to shape Claude's assumptions *before* any reasoning starts. It doesn't need recency; it needs priority.

The shortcut: **does it have steps?** Procedures almost always need recency (→ Skill). Single constraints almost always need priority (→ prior, continue to Property 4). But the underlying reason is about context position.

Same topic, different forms:
- **"Always run tests before committing"** — a prior that shapes assumptions → CLAUDE.md (or Hook if fully mechanical)
- **"When committing: 1. Run `pnpm test` 2. Ensure coverage >80% 3. Run `pnpm lint --fix` 4. Draft conventional commit message 5. Show user for approval"** — needs recency at point of action → **Skill**

### Property 4: Always relevant or sometimes?

For priors (single constraints and facts), ask: **would Claude make a wrong assumption without this on its very first action in any session?**

- **Yes → CLAUDE.md.** These are always-relevant priors: "this project uses pnpm not npm", "the database is SQLite in production — this is intentional", "we deploy to Fly.io not AWS."

- **No → Memory.** These matter in some conversations but not all, and are selected by relevance. Memory isn't just for user preferences — it covers anything actionable that's only sometimes relevant:
  - **Preferences**: "user prefers bundled PRs over small ones", "user is colorblind — avoid using only color to distinguish options in UI work"
  - **Lessons learned**: "don't mock the database in integration tests — mocks passed but the prod migration broke"
  - **Project state**: "the payments module is being rewritten this sprint — avoid changes there"
  - **External references**: "API docs for the shipping provider are at docs.shipco.com/api/v3"

This boundary is where most mistakes happen. Two common errors:

**Error 1: Putting sometimes-relevant things in CLAUDE.md because they feel "always true."** "Always true" ≠ "always relevant." Test: Claude starts a new session to fix a CSS bug. Does it need this right now? "User prefers bundled PRs" → no, not relevant to a CSS fix → Memory. "User is colorblind" (full-stack repo) → no, only relevant when doing UI work → Memory. "Don't mock the DB in integration tests" → no, only relevant when writing integration tests → Memory.

**Error 2: Putting always-relevant things in Memory because they seem "topic-specific."** Some constraints sound topic-specific but affect *ubiquitous actions* — things Claude does in nearly every session. "Make sure tests pass before committing" → committing happens most sessions → CLAUDE.md. "We deploy to Fly.io, not AWS" → shapes infrastructure assumptions (config files, CI, env vars, CLI tools) → CLAUDE.md. "User finds excessive code comments patronizing" → code style preference, but many sessions are research/debugging/discussion without writing code → Memory.

### Few-shot examples

*Note: The canonical test suite and expected answers are maintained in `skills/remember/TESTING.md`. If the examples below diverge from that file, TESTING.md is authoritative.*

| Input | Property path | Classification |
|-------|--------------|----------------|
| "Run `pnpm test` before any `git commit`" | Fully mechanical, specific command | **Hook** |
| "Run the linter after every file edit" | Fully mechanical, no judgment | **Hook** |
| "Block Bash commands containing `rm -rf /`" | Fully mechanical, pattern match | **Hook** |
| "Auto-format Python files with `black` after every write" | Fully mechanical, specific command | **Hook** |
| "The auth middleware uses Redis for sessions with a 24h TTL" | Describes architecture | **MagicDocs** |
| "API routes are generated from OpenAPI specs in /api/specs/" | Describes how things work | **MagicDocs** |
| "The frontend uses custom state management on React context, not Redux" | Describes architecture | **MagicDocs** |
| "The notification system uses fan-out — events to central topic, then per-consumer queues" | Describes architecture | **MagicDocs** |
| "When committing: run tests, check coverage, lint, draft message, wait for approval" | Prescribes, needs recency at point of action | **Skill** |
| "When I ask to deploy: run tests, build Docker image, push to staging, notify me" | Prescribes, needs recency at point of action | **Skill** |
| "When reviewing a PR: check security, verify tests, check breaking changes, summarize" | Prescribes, needs recency at point of action | **Skill** |
| "When setting up a new service: create dir, add Dockerfile, register in docker-compose, add health check, add to CI" | Prescribes, needs recency at point of action | **Skill** |
| "This project uses pnpm, not npm" | Prior, shapes assumptions, every session | **CLAUDE.md** |
| "Make sure tests pass before committing" | Prior (needs judgment), every session | **CLAUDE.md** |
| "The database is SQLite in production — don't suggest Postgres" | Prior, shapes assumptions, every session | **CLAUDE.md** |
| "We deploy to Fly.io, not AWS" | Prior, shapes assumptions, every session | **CLAUDE.md** |
| "User prefers bundled PRs over many small ones" | Preference, sometimes relevant | **Memory** |
| `<context>Repo: Go API, PostgreSQL, worker queue, small React admin dashboard</context>` "User is colorblind — avoid using only color to distinguish options in UI work" | Preference, sometimes relevant (most sessions are backend) | **Memory** |
| `<context>Backend-only repo</context>` "User is colorblind — avoid using only color to distinguish options in UI work" | Preference, actionable across user's projects even if not here | **Memory** (user-scoped) |
| `<context>Frontend-only repo</context>` "User is colorblind — avoid using only color to distinguish options in UI work" | Preference, every session touches UI | **CLAUDE.md** |
| "Don't mock the database in integration tests — mocks passed but prod migration broke" | Lesson learned, sometimes relevant | **Memory** |
| "User finds excessive code comments patronizing — only comment non-obvious logic" | Preference, sometimes relevant | **Memory** |
| "The sky is blue" | Not actionable | **None** |
| "I had pizza for lunch" | Not actionable | **None** |
| "TypeScript was created by Microsoft" | Not actionable (Claude already knows) | **None** |
| "React is a popular frontend framework" | Not actionable (Claude already knows) | **None** |

### A note on behavioral rules in CLAUDE.md

The tree above correctly classifies "make sure tests pass before committing" as CLAUDE.md — it's an always-relevant prior. But in practice, behavioral rules that land in CLAUDE.md often don't get followed reliably. The instruction is read at session start and may be thousands of tokens away by the time Claude is acting. There's no feedback loop to verify compliance, and no mechanism to catch violations (see [Chapter 2: the verification gap](02-context-engineering.md#whats-missing-verification)).

Environmental facts don't have this problem. "This project uses pnpm" shapes assumptions immediately and wrong assumptions surface as errors — Claude runs `pnpm install` or it doesn't. But behavioral rules like "always run tests before committing" or "don't mock the database in integration tests" require Claude to *remember to do something* at the right moment, which is exactly what CLAUDE.md is bad at.

In our experience, behavioral rules that land in CLAUDE.md often need a second enforcement layer: a code-review skill with coding standards attached, where a subagent checks compliance at point of action. The review skill arrives with recency (as a tool result, not a system prompt from thousands of tokens ago), and the subagent provides independent verification. This doesn't mean behavioral rules *shouldn't* go in CLAUDE.md — they still set a useful prior. But if you find that Claude keeps ignoring a CLAUDE.md instruction, the fix is usually not to reword the instruction. It's to add a skill that enforces it.

## Scope: where to put it

The decision tree tells you *what kind* of persistence to use. A separate question determines *where* it lives. Claude Code's persistence mechanisms span multiple scopes:

- **CLAUDE.md** walks up the directory tree: `src/frontend/CLAUDE.md` → project root `CLAUDE.md` → `~/.claude/CLAUDE.md`. Each level is accumulated in order.
- **Memory** can be project-scoped (`.claude/projects/<project>/memory/`) or user-wide (`~/.claude/memory/`).
- **Skills** can live in the project (`.claude/skills/`) or in the user's home (`~/.claude/skills/`).
- **Hooks** and **MagicDocs** are always project-scoped.

For Hook and MagicDocs, scope is implicit — they're about this project's tooling and architecture. For Skill, CLAUDE.md, and Memory, ask: **does this follow the code, or follow the person?**

- "This project uses pnpm" → follows the code → project `CLAUDE.md`
- "User is colorblind" → follows the person → `~/.claude/memory/` or `~/.claude/CLAUDE.md`
- "I'm not familiar with Rust" (in a Rust project) → follows the person *in this codebase* → project-scoped memory

The same information can have different scopes in different contexts. "User is colorblind" in a frontend-only repo is CLAUDE.md (always relevant here), while in a backend-only repo it's user-scoped Memory (not relevant here, but matters in the user's other projects). Classification and scope are orthogonal — determine the mechanism first, then determine the location.

## Next

[Chapter 5: Building MagicDocs →](05-building-magicdocs.md)

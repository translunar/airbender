# Building MagicDocs

MagicDocs is an internal feature of Claude Code — a Sonnet subagent that automatically updates architectural documentation files. It is fully gated to internal builds and not available to public Claude Code users. But its design philosophy is well-documented in the extracted agent prompt, and we can replicate the behavior using skills, subagents, and hooks.

This chapter walks through the progression: understand the philosophy, create docs manually, then set up automated updates using the airbender plugin.

## What we're replicating

The real MagicDocs agent has a simple architecture:

- **Model**: Sonnet (cost-optimized, not the full Opus model)
- **Tools**: Only the Edit tool — doc contents are pre-loaded via template variables (`{{docPath}}`, `{{docContents}}`, `{{docTitle}}`, `{{customInstructions}}`)
- **Input**: The conversation transcript and current doc contents
- **Output**: Edit tool calls to update the doc, or a brief explanation of why no update is needed
- **Trigger**: `postSamplingHook` — fires after each model response that involved tool calls, **not** post-conversation. This means updates happen incrementally during the session, not as a batch at the end.
- **Scope**: Each doc gets its own fresh agent run. An orchestration layer (with full conversation context) decides which docs are relevant; the agent only edits the single doc it's given

A key design point: docs are **not** mapped to code files via path matching or a `when_to_use` field. They're navigational overlays organized by concern ("Authentication", "Build Pipeline"). The orchestration layer judges which docs are relevant to the conversation; the agent itself just updates the one it's given. The agent cannot create new docs or split existing ones — it only edits.

Our replication uses the [airbender](https://github.com/translunar/airbender) plugin, which provides: `/setup-magicdocs` (bootstrap a repo), `/create-magicdoc` (add individual docs), and `/classify-info` (route information to the right persistence mechanism, including MagicDocs). The rest of this chapter explains the underlying philosophy and manual process — understand these before using the plugin.

[source: `agent-prompt-update-magic-docs.md` — agent metadata showing model, tools, and trigger](https://github.com/Piebald-AI/claude-code-system-prompts/blob/main/system-prompts/agent-prompt-update-magic-docs.md)

## Step 1: Understand the MagicDocs philosophy

Before building the automation, you need to internalize what makes a good MagicDoc. The real agent prompt contains a detailed philosophy that separates MagicDocs from typical documentation.

### What TO document

- **High-level architecture and system design** — how major components connect and communicate
- **Non-obvious patterns, conventions, or gotchas** — things that would surprise someone reading the code for the first time
- **Key entry points and where to start reading** — "if you want to understand X, start at file Y"
- **Important design decisions and their rationale** — not just what was chosen, but why
- **Critical dependencies or integration points** — where your system touches external systems
- **References to related files, docs, or code** — cross-references that help readers navigate (like a wiki)

### What NOT to document

- **Anything obvious from reading the code itself** — if the function name explains what it does, don't repeat it
- **Exhaustive lists of files, functions, or parameters** — that's what grep is for
- **Step-by-step implementation details** — the code is the implementation detail
- **Low-level code mechanics** — how a for loop works is not documentation
- **Information already in CLAUDE.md or other project docs** — MagicDocs are designed to avoid duplicating CLAUDE.md content

### The update philosophy

The agent prompt is emphatic about this: **MagicDocs are current state, not changelog.**

- "Keep the document CURRENT with the latest state of the codebase — this is NOT a changelog or history"
- "Update information IN-PLACE to reflect the current state — do NOT append historical notes or track changes over time"
- "Remove or replace outdated information rather than adding 'Previously...' or 'Updated to...' notes"
- "Clean up or DELETE sections that are no longer relevant or don't align with the document's purpose"
- "Fix obvious errors: typos, grammar mistakes, broken formatting, incorrect information, or confusing statements"

And above all: **"BE TERSE. High signal only. No filler words or unnecessary elaboration."**

[source: `agent-prompt-update-magic-docs.md` — CRITICAL RULES and DOCUMENTATION PHILOSOPHY sections](https://github.com/Piebald-AI/claude-code-system-prompts/blob/main/system-prompts/agent-prompt-update-magic-docs.md)

## Step 2: Create your first Magic Doc manually

Start by creating a directory for your Magic Docs and writing one by hand. This forces you to practice the philosophy before automating it.

### Setup

```bash
mkdir -p docs/magic
```

### Template

Every Magic Doc uses a consistent header that the update system preserves exactly:

```markdown
# MAGIC DOC: <Title>

*<Optional one-line description — preserved by the update agent>*

## Overview

<2-3 sentences on what this subsystem/area is and why it exists>

## Architecture

<How major components connect. Diagrams if helpful.>

## Key Entry Points

<Where to start reading if you want to understand this area>

## Non-Obvious Patterns

<Gotchas, conventions, things that would surprise a newcomer>

## Dependencies

<External systems, APIs, or internal modules this area relies on>
```

### Good vs bad example

**Bad Magic Doc** (too detailed):

```markdown
# MAGIC DOC: Authentication

The auth system is in src/middleware/auth.ts (247 lines). It exports
the `authMiddleware` function on line 12 which takes `req`, `res`, and
`next` parameters. First it checks `req.headers.authorization` on line
15. If the header is missing, it returns 401 on line 18. If present,
it calls `verifyToken()` from src/utils/jwt.ts on line 23...
```

*This is a code walkthrough, not a Magic Doc. Anyone can read the source. Document the why and the how-things-connect, not the line-by-line what.*

**Good Magic Doc** (terse, architectural):

```markdown
# MAGIC DOC: Authentication

*Session-based auth using Redis for token storage*

## Overview

Auth uses signed JWTs with Redis-backed session storage. Tokens are
short-lived (15min) with refresh tokens stored server-side. This was
chosen over stateless JWTs because we need server-side session
revocation for compliance.

## Key Entry Points

- `src/middleware/auth.ts` — middleware chain entry
- `src/services/session.ts` — Redis session CRUD
- `src/routes/auth/` — login, logout, refresh endpoints

## Non-Obvious Patterns

- The `/health` and `/metrics` endpoints bypass auth entirely —
  they're mounted before the middleware chain
- Session TTL is 24h but the middleware refreshes it on every
  request, so active users never expire
- Rate limiting runs BEFORE auth — unauthenticated spam is blocked
  before it hits the token verifier
```

### Scoping guidance

Create one doc per major subsystem or concern, not one giant doc. Good boundaries:

- One doc per service in a microservices architecture
- One doc per major feature area (auth, billing, notifications)
- One doc for infrastructure/deployment
- One doc for cross-cutting concerns (logging, error handling, testing patterns)

A doc that grows beyond ~500 words is probably covering too much. Split it.

## Step 3: Set up the automated system

Once you understand the philosophy and have practiced writing docs manually, install the [airbender](https://github.com/translunar/airbender) plugin and run `/setup-magicdocs` in your repo. This bootstraps the full system:

1. Explores your repo structure
2. Proposes 2-3 segmentation strategies — you pick how to slice the docs
3. Creates `docs/magic/` with skeleton docs following the philosophy above
4. Adds a CLAUDE.md pointer so future sessions know the docs exist
5. Configures a Stop hook for automatic staleness pruning

After setup, use `/create-magicdoc <title>` to add individual docs for new subsystems as they emerge.

### How updates happen

Updates flow through three channels, from most to least context:

**Channel 1: Insight dispatch (primary).** During normal work, the main agent encounters something non-obvious about the codebase. The `/classify-info` skill classifies it as MagicDocs (architectural description, not a behavioral prescription). The main agent formulates a terse insight and specifies the target doc:

```
An agent modifying the auth middleware would assume sessions are
stateless JWTs. Actually, sessions are Redis-backed with server-side
revocation — this was chosen for compliance. The relevant code is
in src/middleware/auth.ts and src/services/session.ts.
```

A fresh Sonnet subagent receives this insight with `Read, Edit` tools only, reads the target doc from disk, integrates the insight following the MagicDocs philosophy, and exits. Edits are left unstaged for the user to commit. The subagent runs in the background — fire-and-forget, no blocking.

Why `Read, Edit` only? MVP testing showed that giving the subagent `Glob` access caused scope violations (Haiku edited unrelated files it discovered). Dropping Glob and specifying the exact target doc path eliminated this. The main agent — which has full conversation context — picks the target doc, not the subagent.

**Channel 2: Manual invocation.** The user says "remember this" or runs `/create-magicdoc`. Highest signal, lowest automation.

**Channel 3: Stop hook pruning (safety net).** When a session ends, a Stop hook checks `git diff` for meaningful code changes. If found, it spawns a headless Sonnet session that reconciles magic docs against the diff — fixing stale file paths, removing references to deleted code, updating structural descriptions. This is **reconciliation, not synthesis** — the hook can fix "what" (file paths changed) but not "why" (design rationale discovered in conversation). It catches things the main agent forgot to document.

```json
{
  "hooks": {
    "Stop": [{
      "hooks": [{
        "type": "command",
        "command": "if git diff --stat HEAD 2>/dev/null | grep -q '.'; then claude -p 'Check the git diff against existing magic docs (grep for files with # MAGIC DOC: headers). If any doc references files, paths, or structures that changed in the diff, update those references in-place. Do NOT add new architectural insights — only fix inconsistencies between docs and current code state. Be terse. If nothing is inconsistent, make no edits.' --model sonnet --allowedTools 'Glob,Read,Edit,Grep' 2>/dev/null & fi"
      }]
    }]
  }
}
```

The Stop hook gets `Glob` and `Grep` (unlike the insight subagent) because it needs to discover magic docs repo-wide, including co-located docs outside `docs/magic/`.

### Why this design differs from Chapter 5's original approach

The earlier version of this chapter described a simpler system: a Stop hook runs after every session and uses `git diff` to update docs. That approach has fundamental limitations:

- **No conversation context.** The Stop hook only sees diffs — it can't capture design rationale, gotchas, or non-obvious patterns discussed during the session.
- **Batch, not incremental.** Running once at session end means insights accumulate and may be forgotten by the time the hook fires.
- **All-or-nothing.** Every session triggers the hook, even trivial ones. Gating by diff size is a rough proxy.

The incremental insight dispatch model (Channel 1) solves these: updates happen during the session while the main agent has full context, each update is focused on a single insight, and the Stop hook serves only as a safety net for structural drift — not as the primary update mechanism.

[source: `system-prompt-hooks-configuration.md` for hook schema and events](https://github.com/Piebald-AI/claude-code-system-prompts/blob/main/system-prompts/system-prompt-hooks-configuration.md), [`config.rs` for hook configuration loading](https://github.com/instructkr/claw-code/blob/main/rust/crates/runtime/src/config.rs)

## Putting it all together

Here's what you've built — a documentation system that mirrors Anthropic's internal MagicDocs pipeline using user-accessible primitives:

```
┌─────────────────────────────────────────────────┐
│                 Your Session                     │
│                                                  │
│  You work with Claude Code on your project.      │
│  Architectural decisions are made. Patterns are   │
│  discovered. Gotchas are encountered.             │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│              Stop Hook Triggers                  │
│                                                  │
│  Session ends → hook runs headless claude -p      │
│  with --model sonnet and restricted tools         │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│           Headless Claude Updates Docs            │
│                                                  │
│  Reads docs/magic/*.md                            │
│  Reads recent git diff                            │
│  Updates relevant docs in-place                   │
│  Removes outdated info                            │
│  Skips if nothing substantial to add              │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│            Next Session Loads Docs               │
│                                                  │
│  Updated docs are available in the codebase.      │
│  Claude Code can read them via Explore/Read.      │
│  Or reference them from CLAUDE.md.                │
└─────────────────────────────────────────────────┘
```

### Making docs discoverable in future sessions

Your Magic Docs are files on disk, but Claude Code won't automatically read them unless it has a reason to. To close the loop, add a pointer in your CLAUDE.md:

```markdown
# CLAUDE.md
Architectural documentation is maintained in docs/magic/. Read the relevant
Magic Doc before making changes to a subsystem you're unfamiliar with.
```

This uses CLAUDE.md for what it's good at — a short, always-present pointer that sets a prior ("docs exist, read them first") without trying to contain the documentation itself. This is also the right division of labor: CLAUDE.md holds the environmental fact ("docs are here"), while the Magic Docs hold the architectural knowledge that would otherwise bloat CLAUDE.md and go stale without maintenance. Magic Docs self-correct through the development loop; CLAUDE.md content doesn't (see [Chapter 2: the verification gap](02-context-engineering.md#whats-missing-verification)). If you find yourself putting architectural descriptions in CLAUDE.md — how components connect, what talks to what, where entry points are — that content belongs in Magic Docs instead.

Alternatively, you can create a memory file with a specific description (e.g., "Architectural docs for auth, billing, and deployment are in docs/magic/") so the memory selection agent loads the pointer when those topics come up in conversation. This is lighter than a CLAUDE.md entry since it only appears when relevant.

### Verifying it works

How do you know your Magic Docs are actually informing Claude's context? A few ways to check:

- **Ask Claude directly**: "What do you know about the auth system?" If it cites information from your Magic Doc, the pipeline is working. If it says "I'd need to explore the codebase," the doc isn't being loaded.
- **Check after a hook-triggered update**: After a session where you made auth changes, open `docs/magic/auth.md` and see if the content changed. If not, the hook may not be firing or the headless session may be failing silently.
- **Watch for stale information**: If Claude confidently states something that's no longer true, check whether a Magic Doc is the source of the outdated claim. This is the most common failure mode — a doc that stopped getting updated.
- **Review git diffs**: Since Magic Docs are files on disk, `git diff docs/magic/` shows exactly what changed after each update cycle.

### Maintenance

- **Review periodically**: Magic Docs self-prune on updates, but they can't remove docs for subsystems that no longer exist. Delete docs for removed features manually.
- **Keep them terse**: If a doc grows beyond ~500 words, it's probably covering too much. Split it into separate docs, one per concern — the update agent can only edit one doc per run, so smaller docs get more focused updates.
- **One doc per concern**: Don't create a monolithic "architecture.md" that covers everything. Scoped docs are easier to update and more useful to load selectively. Good boundaries: one doc per service, per major feature area, or per cross-cutting concern.
- **Trust the philosophy**: The instinct to document everything in detail is strong. Resist it. The code is the detail. Magic Docs are the map.

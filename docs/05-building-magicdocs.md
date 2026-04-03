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

## Step 3: Build an update skill

Now wrap the update logic in a skill so you can invoke it with `/update-docs` after a significant session.

Create the file `.claude/skills/update-docs/SKILL.md`:

```markdown
---
name: update-docs
description: Update Magic Doc files with new learnings from the current session
when_to_use: When the user asks to update docs, update magic docs, or after completing significant implementation work
allowed-tools: Read, Edit, Glob, Grep
---

Review the current conversation for new learnings, insights, or information
that would be valuable to preserve in the project's Magic Doc files.

## Steps

1. Find all existing Magic Doc files:
   - Glob for `docs/magic/*.md` (or the project's magic docs location)
   - Read each file to understand current contents

2. Analyze the conversation and recent git diff for new information:
   - What architectural decisions were made or discussed?
   - What non-obvious patterns were discovered?
   - What gotchas or issues were encountered?
   - What entry points or key files were identified?
   - What does `git diff HEAD~1` reveal about recent changes?

3. For each relevant Magic Doc, update it following these rules:
   - Preserve the header exactly: `# MAGIC DOC: <title>`
   - If there's an italicized line after the header, preserve it exactly
   - Update information IN-PLACE — do NOT append historical notes
   - Remove or replace outdated information
   - Clean up or DELETE sections that are no longer relevant
   - BE TERSE. High signal only. No filler words.

4. If the conversation revealed a new subsystem or area that doesn't
   have a Magic Doc yet, note this to the user but don't create it
   automatically — use `/create-doc` for that.

5. Show the user what changed (summarize the edits).

## What TO update

- High-level architecture and system design
- Non-obvious patterns, conventions, or gotchas
- Key entry points and where to start reading code
- Important design decisions and their rationale
- Critical dependencies or integration points

## What NOT to update

- Anything obvious from reading the code
- Exhaustive lists of files, functions, or parameters
- Step-by-step implementation details
- Information already in CLAUDE.md
```

The key design choices in this skill:

- **`when_to_use` is specific** — it mentions "update docs", "magic docs", and "after completing significant work." This gives the selection system concrete phrases to match on.
- **`allowed-tools` includes Read and Glob** — unlike the real MagicDocs agent which only has Edit, our skill needs to discover and read the existing docs. The real agent gets doc contents passed as a template variable; we have to find them ourselves.
- **The philosophy is embedded in the skill** — the rules about terseness, in-place updates, and what to document are right there in the prompt, so they're fresh in context when the skill fires.

## Step 4: Build a creation skill

The update skill maintains existing docs. You also need a way to bootstrap new ones. Create `.claude/skills/create-doc/SKILL.md`:

```markdown
---
name: create-doc
description: Create a new Magic Doc for a subsystem or area of the codebase
when_to_use: When the user asks to create a doc, create a magic doc, or document a new subsystem
allowed-tools: Read, Write, Glob, Grep, Bash
---

Create a new Magic Doc file for a subsystem or area of the codebase.

## Arguments

$title — The title for the Magic Doc (e.g., "Authentication", "Build Pipeline"). Invoke as `/create-doc Authentication` — the argument after the command becomes `$title`.

## Steps

1. Check if a Magic Doc already exists for this topic:
   - Glob for `docs/magic/*.md`
   - If a doc with a similar title exists, tell the user and suggest
     using `/update-docs` instead

2. Analyze the relevant area of the codebase:
   - Search for key files, entry points, and patterns
   - Read the most important files (not exhaustively — focus on
     entry points and architecture)
   - Identify non-obvious patterns and gotchas

3. Write the Magic Doc to `docs/magic/<slug>.md` using this structure:

   ```
   # MAGIC DOC: $title

   *<one-line description>*

   ## Overview
   ## Architecture (if applicable)
   ## Key Entry Points
   ## Non-Obvious Patterns
   ## Dependencies (if applicable)
   ```

4. Follow the MagicDocs philosophy:
   - BE TERSE. High signal only.
   - Document WHY things exist, HOW components connect, WHERE to
     start reading, WHAT patterns are used
   - Do NOT document anything obvious from reading the code
   - Do NOT create exhaustive lists of files or functions
   - Keep the total doc under ~500 words

5. Show the user the created doc and ask if anything should be
   adjusted.
```

## Step 5: Automate with hooks

Once you're comfortable with the manual workflow, you can automate it so Magic Docs update after every session without you remembering to invoke `/update-docs`.

The approach: use a `Stop` hook event to trigger a headless `claude -p` call when a session ends.

### Hook configuration

Add this to your `.claude/settings.json` (or `.claude/settings.local.json` for personal use):

```json
{
  "hooks": {
    "Stop": [{
      "hooks": [{
        "type": "command",
        "command": "claude -p 'Review the git diff of the last session and update any relevant Magic Doc files in docs/magic/ following the MagicDocs philosophy. Be terse. Update in-place. Remove outdated info. Only update if there is substantial new information.' --allowedTools 'Read,Edit,Glob,Grep' --model sonnet 2>/dev/null &"
      }]
    }]
  }
}
```

### Design choices explained

- **`Stop` event**: Runs when the session ends, mirroring how the real MagicDocs agent runs post-conversation.
- **`--model sonnet`**: Uses Sonnet, matching the real MagicDocs agent. Cheaper than Opus, fast enough for doc updates.
- **`--allowedTools`**: Restricts the headless session to read and edit operations only. No Bash, no Write (can't create new files — only update existing ones).
- **`&` at the end**: Runs in the background so it doesn't block session exit.
- **`2>/dev/null`**: Suppresses stderr so background errors don't pollute your terminal.
- **The prompt includes the philosophy inline**: "Be terse. Update in-place. Remove outdated info." Since the headless session has no access to our skill files, the key rules need to be in the prompt itself.

*Note: The `--allowedTools` and `--model` flags shown here reflect the Claude Code CLI at time of writing. Flag names may vary across versions — check `claude --help` to confirm.*

### Trade-offs and gating

This setup runs after **every** session, which has costs:

- **Token cost**: Each update triggers a Sonnet session that reads your Magic Docs and recent changes. For a project with 5 docs, this might be 10-20K tokens per session.
- **Noise**: Not every conversation produces doc-worthy learnings. A session where you only asked "what does this function do?" doesn't need a doc update.
- **Stale diffs**: The `git diff` approach only captures committed changes, not conversational insights that didn't result in code changes.

To reduce noise, you could gate the hook:

```json
{
  "hooks": {
    "Stop": [{
      "hooks": [{
        "type": "command",
        "command": "if [ $(git diff --stat HEAD~1 | wc -l) -gt 5 ]; then claude -p '...' --model sonnet 2>/dev/null & fi"
      }]
    }]
  }
}
```

This only triggers the update if the most recent commit changed more than 5 files — a rough proxy for "significant work happened."

[source: `system-prompt-hooks-configuration.md` for hook schema and events](https://github.com/Piebald-AI/claude-code-system-prompts/blob/main/system-prompts/system-prompt-hooks-configuration.md), [`config.rs` for hook configuration loading](https://github.com/instructkr/claw-code/blob/main/rust/crates/runtime/src/config.rs)

[source: `system-prompt-insights-suggestions.md` for the pattern of post-session analysis](https://github.com/Piebald-AI/claude-code-system-prompts/blob/main/system-prompts/system-prompt-insights-suggestions.md)

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

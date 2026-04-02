# Spec: MagicDocs System

**Date**: 2026-04-02
**Status**: Draft
**Prerequisite**: MVP validation passes (see `docs/specs/2026-04-02-magicdocs-mvp.md`)

## Goal

Build a portable, installable set of skills that bootstraps a MagicDocs system in any repository. MagicDocs are terse, auto-maintained architectural documentation files that capture non-obvious patterns, gotchas, design rationale, and entry points — things that would surprise an agent reading the codebase for the first time.

MagicDocs complement CLAUDE.md (behavioral constraints) by holding architectural knowledge that would otherwise go stale. CLAUDE.md says "how you want Claude to behave." MagicDocs say "how the codebase works."

The deliverable is a **modular set of skills** — a bootstrap installer (`/setup-magicdocs`) plus a doc creation skill (`/create-magic-doc`). Skills are built serially using `/writing-skills` (not by subagents, which don't have access to the writing-skills skill). Updates happen automatically via the existing `/classify-info` classification flow.

## Reference: How Anthropic's Internal MagicDocs Works

Anthropic has an internal MagicDocs feature, fully gated to internal builds. It is not available to public Claude Code users — creating `# MAGIC DOC:` files in a public repo activates nothing. No settings key, env var, or CLI flag enables it. Matt Palmer confirms it's an employee feature. The code exists at `src/services/MagicDocs/`.

Key details from the extracted `agent-prompt-update-magic-docs.md` and source code analysis:

- **Model**: Sonnet subagent, cost-optimized
- **Tools**: Edit only. Doc contents are pre-loaded via template variables (`{{docPath}}`, `{{docContents}}`, `{{docTitle}}`, `{{customInstructions}}`) — the agent never reads files itself
- **Trigger**: `postSamplingHook` after model responses that involved tool calls. This means updates happen **incrementally during the session**, not as a batch at session end. (Chapter 5 of the airbender manual describes this incorrectly as post-conversation — that chapter needs updating.)
- **Timing**: Fires during idle lulls when the user hasn't sent a new message
- **Scope**: Each doc gets its own fresh agent run. An orchestration layer (with full conversation context) decides which docs are relevant; the agent only edits the single doc it's given
- **Discovery**: Regex `^#\s*MAGIC\s+DOC:\s*(.+)$/im` — docs can live anywhere in the repo
- **Cannot create new docs** — only edits existing ones. A separate process handles creation
- **Self-pruning**: Inline during every update. "Remove or replace outdated information." "Clean up or DELETE sections that are no longer relevant." No separate pruning step.

### MagicDocs Philosophy

From Anthropic's extracted agent prompt — replicated verbatim in our subagent prompt:

**What TO document**: High-level architecture and system design. Non-obvious patterns, conventions, or gotchas. Key entry points and where to start reading code. Important design decisions and their rationale. Critical dependencies or integration points. Cross-references to related files, docs, or code.

**What NOT to document**: Anything obvious from reading the code itself. Exhaustive lists of files, functions, or parameters. Step-by-step implementation details. Low-level code mechanics. Information already in CLAUDE.md or other project docs.

**Update rules**: Current state only — NOT a changelog. Update in-place, remove outdated info, delete irrelevant sections. **"BE TERSE. High signal only. No filler words or unnecessary elaboration."**

**Header convention**: `# MAGIC DOC: <title>` preserved exactly on every edit.

## Architecture

### Core Loop: Insight Dispatch

```
Main agent does normal work
  → encounters something non-obvious about the codebase
  → /classify-info classifies it as MagicDocs (describes architecture, not prescribes behavior)
  → /classify-info returns the classification — it does NOT dispatch
  → main agent formulates insight + specifies target doc
  → main agent spawns fresh Sonnet subagent (background, fire-and-forget)
  → subagent reads target doc from disk, integrates insight, exits
  → edits left unstaged for user to commit
```

### Why This Design

**Why terse insights, not conversation transcripts?** We don't have access to the conversation transcript from outside the session. Even if we did, passing 95%+ of a context window to a subagent would be slow and expensive with no guarantee it wouldn't hit the same context limits. The main agent already did the hard work of discovering the insight; the subagent's job is to integrate it, not re-derive it. If edit quality turns out to be low, we can upgrade to conversation summaries later. Start minimal.

**Why the main agent picks the target doc?** The main agent just encountered the insight — it knows which subsystem it relates to. A subagent with only a terse insight and a list of filenames would be making a hard relevance judgment with insufficient context. (This was identified by the design review — pushing doc-selection to a minimally-contexted subagent doesn't work.)

**Why fresh-per-insight, not a persistent daemon?** A persistent agent accumulates stale context via compaction. Earlier turns' doc reads get compacted into 160-char summaries, degrading the quality of later updates. Fresh-per-insight means every dispatch reads the current file state with a clean context window. This matches Anthropic's design (fresh agent per doc per update) and has better context hygiene. (The design review identified this — a daemon model contradicts the "always reads most recent version" principle.)

**Why `/classify-info` classifies but doesn't dispatch?** Separation of concerns. `/classify-info` is a classification skill, testable independently at 100% accuracy (26/26 test suite). Dispatch requires codebase context (formulating the insight, picking the target doc) that `/classify-info` doesn't have. Keeping them separate makes each piece testable.

**Why edits are left unstaged?** Magic doc files are "owned" by the magicdocs system — no other subagent should be editing them. Unstaged changes to `docs/magic/auth.md` don't interfere with a subagent implementing auth code. No auto-commit avoids branch management complexity, worktree overhead, and attribution confusion. The user's next commit naturally picks up the changes. CLAUDE.md includes a note so code reviewers know these changes are auto-generated and expected.

### Three Trigger Channels

| Channel | Trigger | Context Available | What It Catches |
|---------|---------|-------------------|-----------------|
| **(a) Main agent judgment** | `/classify-info` → MagicDocs | Full conversation | Non-obvious patterns, design rationale, gotchas |
| **(b) User invocation** | "remember this" or `/create-magic-doc` | Full conversation | Anything the user explicitly wants documented |
| **(c) Stop hook pruning** | Session exit + git diff | Diffs only | Stale file paths, deleted code references, structural changes |

**Reliability caveat**: Channel (a) is the primary automatic mechanism but depends on the main agent noticing something is doc-worthy — a behavioral instruction, which are known to be unreliable (see Chapter 4: behavioral rules in CLAUDE.md often don't get followed). The `/classify-info` skill's 100% classification accuracy doesn't help if the main agent never invokes it. Channel (c) partially compensates by sweeping for structural inconsistencies at session end — it can fix "what" (file paths, structure) but not "why" (rationale, gotchas).

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    Main Agent Session                    │
│                                                          │
│  Normal work → encounters non-obvious thing              │
│  → /classify-info classifies as MagicDocs                     │
│  → formulates insight + specifies target doc             │
│  → spawns fresh Sonnet subagent (background)             │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│               MagicDocs Subagent (Sonnet)                │
│                                                          │
│  Tools: Read, Edit only. No Glob, Bash, or Write.       │
│  Reads target doc → integrates insight → exits           │
│  Edits left unstaged for user to commit                  │
│  Fresh per dispatch — no persistence, no stale state     │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                  Stop Hook (Pruning)                     │
│                                                          │
│  Session ends → git diff check                           │
│  If meaningful changes: headless claude -p --model sonnet │
│  Reconciles magic docs against diff                      │
│  Fixes stale file paths, removes deleted references      │
│  Does NOT add new insights — only prunes inconsistencies │
│  Tools: Glob, Read, Edit, Grep (needs Grep for repo-wide│
│  discovery of co-located docs)                           │
└─────────────────────────────────────────────────────────┘
```

## MagicDocs Subagent

### Model

Sonnet (recommended). MVP testing showed Sonnet scores 5/5 and Haiku 4.5/5 after one REFACTOR round. Haiku is viable for cost-sensitive deployments but less reliable on borderline cases (over-edits content that's arguably already captured). Both models require the `Read, Edit` only toolset — Haiku had scope violations with Glob access.

### Tools

`Read, Edit` only. No Glob (MVP proved dropping Glob prevents scope violations — Haiku edited unrelated files when it could discover them). No Write (can't create new docs — that's `/create-magic-doc`). No Bash (prevents unconstrained shell access).

Why Read when Anthropic uses Edit only? Anthropic pre-loads doc contents via template variables. We can't use template variables, so the subagent needs to read the target doc itself. The dispatch message specifies the exact file path — the subagent doesn't need to discover anything. It always reads the most recent version on disk.

### Prompt

Adapted from Anthropic's `agent-prompt-update-magic-docs.md`. Two substitutions:

1. Replace `{{docContents}}` with "read the doc yourself" — the subagent uses Read to get current contents
2. Replace "Based on the user conversation above" with the focused insight from the dispatch message

The full MagicDocs philosophy (terseness, current-state-only, what to/not to document, header preservation, self-pruning) is embedded verbatim in the prompt so it's fresh in context at point of action.

The prompt also includes: "If the insight is not substantial, is already captured in the doc, or doesn't belong in architectural documentation, respond with a brief explanation and make no edits."

### Access Control

- **Writes**: PreToolUse hook on Edit validates the target file has a `# MAGIC DOC:` header. Mechanical enforcement.
- **Reads**: Prompt instructs the subagent to only read magic doc files. This is a behavioral instruction, not mechanical enforcement — acknowledged as a known limitation. The agent could read non-magic-doc files, but it has no reason to (its tools don't include Bash or Write, and its prompt is narrowly focused).

### Insight Message Format

The main agent formulates insights in this format:

```
An agent working on [area] would assume [wrong assumption].
Actually, [correct understanding]. [Why — design rationale if known.]
The relevant code is in [file paths].
```

Example:
```
An agent modifying the auth middleware would assume sessions are
stateless JWTs. Actually, sessions are Redis-backed with server-side
revocation — this was chosen for compliance. The relevant code is
in src/middleware/auth.ts and src/services/session.ts.
```

Short, specific, actionable. The subagent knows what the confusion is, what the truth is, why, and where.

### Dispatch Mechanism

**Before dispatching, the main agent must verify all file paths in the insight exist on disk.** The MVP showed that incorrect paths cause false negatives — the subagent correctly refuses to add dead links, but the insight was about a real file at a different path. Path verification is the main agent's responsibility.

The main agent spawns the subagent directly using the Agent tool:
- `model: "sonnet"`
- `run_in_background: true` (fire-and-forget, doesn't block main work)
- Tools: `Read, Edit`
- Prompt: adapted MagicDocs prompt + insight + target doc path

No intermediate queue, no task list, no coordination layer. The simplest dispatch that works.

## Doc Discovery

Two-pass discovery, supporting both conventional and co-located docs:

1. **Conventional**: Glob `docs/magic/*.md`
2. **Co-located**: Grep repo-wide for `^# MAGIC DOC:` headers (e.g., `src/auth/MAGIC_DOC.md`)

The bootstrap skill creates `docs/magic/` as the default location. Users can also place docs next to their code. Both patterns are supported because Anthropic's internal system uses regex scanning (docs can live anywhere), and different projects have different preferences.

## Doc Segmentation

The bootstrap skill does NOT impose a segmentation strategy. Different repos need different approaches:
- By subsystem/domain ("Authentication", "Billing")
- By code boundary (one doc per top-level directory)
- By entry point (API server, worker queue, CLI tool)
- Hybrid (directory-based for code, concern-based for cross-cutting)

Instead, `/setup-magicdocs` explores the repo structure, proposes 2-3 segmentation strategies tailored to what it finds, and the user picks one. The skill is opinionated about the **system** (update mechanics, philosophy, conventions) but collaborative about the **segmentation** (how to slice up this specific codebase).

## Self-Pruning

Inline during every update, not a separate step. The subagent prompt says:
- "Remove or replace outdated information rather than adding 'Previously...' notes"
- "Clean up or DELETE sections that are no longer relevant"
- "Update information IN-PLACE to reflect the current state"

Orphaned docs (for entirely deleted subsystems) are out of scope — handled manually. The system can't detect that a subsystem no longer exists because no insights will reference it.

## Stop Hook: Pruning Pass

A `Stop` hook that runs at session exit. This is a **core part of the design**, not optional — it's the only trigger channel that doesn't depend on the main agent's judgment.

**What it does**: Checks `git diff` for meaningful code changes. If found, spawns a headless `claude -p --model sonnet` that reconciles magic docs against the diff.

**What it catches**: Stale file paths, deleted code still referenced, changed structures. For example: auth middleware was renamed from `auth.ts` to `session-auth.ts`, but the magic doc still says `src/middleware/auth.ts` — the pruning pass fixes this.

**What it doesn't catch**: Design rationale, gotchas, non-obvious patterns — anything that requires conversation context to understand. The pruning pass is reconciliation, not synthesis.

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

Tools include Grep (in addition to Glob, Read, Edit) because the pruning pass needs to discover co-located magic docs repo-wide.

## PreToolUse Hook: Edit Guard

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Edit",
      "hooks": [{
        "type": "command",
        "command": "if echo \"$ARGUMENTS\" | grep -q 'MAGIC DOC:'; then echo '{\"continue\": true}'; elif echo \"$ARGUMENTS\" | grep -q 'docs/magic/'; then head -1 \"$(echo $ARGUMENTS | jq -r .file_path)\" | grep -q 'MAGIC DOC' && echo '{\"continue\": true}' || echo '{\"continue\": false, \"systemMessage\": \"Cannot edit magic doc file without MAGIC DOC header\"}'; else echo '{\"continue\": true}'; fi"
      }]
    }]
  }
}
```

Note: This is a rough sketch. The exact implementation depends on how `$ARGUMENTS` is structured for Edit tool calls. Needs refinement during implementation.

## Discoverability

The bootstrap skill appends two items to CLAUDE.md:

1. **Pointer**: "Architectural documentation is maintained in docs/magic/ and may also be co-located with code (grep for `# MAGIC DOC:` headers). Read the relevant Magic Doc before making changes to a subsystem you're unfamiliar with."

2. **Reviewer note**: "Files with `# MAGIC DOC:` headers are auto-maintained by the magicdocs system. Changes to these files may appear in unstaged diffs — this is expected."

Both verified via `/classify-info` decision tree: prescriptive, always-relevant priors → CLAUDE.md.

## Deliverables

### Skill 1: `/setup-magicdocs` (bootstrap installer)

Built using `/writing-skills`. Run once per repo.

**What it does:**
1. Explores the repo structure
2. Proposes 2-3 segmentation strategies tailored to the project
3. User picks a segmentation approach
4. Creates `docs/magic/` directory + initial skeleton docs
5. Installs `/create-magic-doc` skill (using `/writing-skills`)
6. Appends pointer and reviewer note to CLAUDE.md (with user confirmation)
7. Adds PreToolUse edit guard hook and Stop pruning hook to `.claude/settings.json` (with user confirmation)

**What it does NOT do:**
- Install an `/update-docs` skill (updates are automatic via `/classify-info` dispatch)

### Skill 2: `/create-magic-doc <title>`

Built using `/writing-skills`. For adding individual magic docs after initial setup.

**What it does:**
1. Checks if a doc with a similar title already exists
2. Explores the relevant area of the codebase (entry points, architecture, patterns)
3. Writes the doc to `docs/magic/<slug>.md` (or co-located if user prefers)
4. Follows MagicDocs philosophy: terse, architectural, entry-points-focused
5. Keeps total doc under ~500 words
6. Shows the user the created doc for review

**Template:**
```markdown
# MAGIC DOC: <title>

*<one-line description>*

## Overview
## Key Entry Points
## Non-Obvious Patterns
## Dependencies (if applicable)
```

### Skill 3: `/prune-magic-docs` (staleness check)

Built using `/writing-skills`. Manual invocation to detect and fix stale content across all magic docs.

**What it does:**
1. Discovers all magic docs (two-pass: `docs/magic/*.md` + grep for `# MAGIC DOC:` headers)
2. For each doc, runs mechanical staleness checks:
   - **Dead file references** — doc mentions files that don't exist on disk
   - **Deleted exports/functions** — doc mentions functions or methods that grep can't find
   - **Structural drift** — doc describes directory contents that don't match reality
   - **Dependency changes** — doc mentions libraries not in package manifest
   - **Git divergence** — files referenced by the doc have been heavily modified since the doc was last updated (git blame age vs git log on referenced files)
   - **Contradiction with CLAUDE.md** — doc claims something CLAUDE.md contradicts
3. Produces a staleness report: which docs have issues, what's stale, severity
4. For each stale item, dispatches a focused insight to the magicdocs subagent (same Read+Edit loop as automatic updates) OR makes the fix directly for simple cases (dead links, renamed files)
5. Reports what was fixed and what needs human judgment

**Design notes:**
- Most checks are mechanical (file existence, grep, git log) — no LLM needed for detection
- Only the *fix* goes through the subagent loop — detection is scripted
- Keeps the architecture consistent: everything flows through insight → subagent → edit
- Start manual (`/prune-magic-docs`), later can be incorporated as a periodic agent or Stop hook enhancement

### Integration: `/classify-info` → MagicDocs Dispatch

No new skill needed. The flow uses existing pieces:

1. Main agent encounters non-obvious architectural insight during work
2. Runs `/classify-info` → classifies as MagicDocs
3. `/classify-info` returns the classification — does NOT dispatch
4. Main agent formulates the insight (format described above)
5. Main agent specifies target doc and **verifies all file paths exist on disk**
6. Main agent spawns fresh Sonnet subagent with `run_in_background: true`, tools: `Read, Edit`
7. Subagent reads the doc, integrates the insight (or declines if already captured / not substantial), exits
8. Edits left unstaged

### Chapter 5 Update

`docs/05-building-magicdocs.md` describes the system as triggering post-conversation via a Stop hook. Our research found MagicDocs triggers incrementally via `postSamplingHook`. Chapter 5 needs updating to reflect the incremental dispatch architecture. This is part of the deliverable.

## Future Upgrade: Agent Teams

If concurrent sessions editing the same magic docs becomes a real problem, Agent Teams (code.claude.com/docs/en/agent-teams) could provide coordination via shared task lists and file-locking. This is not part of the current design — the fresh-per-insight model handles concurrency adequately for most cases (last writer wins, edits are idempotent-ish). Revisit if teams report frequent edit conflicts.

## Uninstall Path

- Remove `.claude/skills/create-magic-doc/` and `.claude/skills/prune-magic-docs/`
- Revert CLAUDE.md additions (pointer + reviewer note)
- Remove PreToolUse edit guard hook and Stop hook from `.claude/settings.json`
- `docs/magic/` content preserved by default — it's useful documentation even without the automation
- User can delete `docs/magic/` manually if desired

## Growth Phases

| Phase | What | Depends On |
|-------|------|-----------|
| **MVP** | Manual magic doc + manual subagent dispatch → validate edit quality | Nothing |
| **Phase 1** | `/setup-magicdocs` skill (using `/writing-skills`) | MVP passes |
| **Phase 2** | `/create-magic-doc` skill (using `/writing-skills`) | Phase 1 |
| **Phase 3** | `/classify-info` → MagicDocs dispatch integration | Phase 2 |
| **Phase 4** | Stop hook pruning pass | Phase 1 |
| **Phase 5** | PreToolUse edit guard | Phase 1 |
| **Phase 6** | `/prune-magic-docs` skill (using `/writing-skills`) | Phase 2 |
| **Phase 7** | Chapter 5 rewrite | Phase 3-6 stable |
| **Deferred** | Proactive idle scanning (git diff during lulls) | Core system proven |
| **Deferred** | Automate `/prune-magic-docs` as periodic agent | Phase 6 proven manually |

Skills in phases 1-2 are built serially using `/writing-skills`, not by subagents.

## Known Limitations

1. **Trigger reliability**: The main agent may not notice doc-worthy insights. The Stop hook partially compensates but only catches structural changes, not rationale/gotchas. The real risk is the main agent not invoking `/classify-info` in the first place — this has never been measured.

2. **Read access not restricted**: The PreToolUse hook only guards writes. Read restriction relies on prompt compliance — the subagent could read non-magic-doc files, but has no reason to with its narrow toolset and focused prompt.

3. **No bad-edit alerting**: Edits are left unstaged and visible in `git diff`, but there's no proactive notification. The user discovers them on `git status`.

4. **Concurrent edit semantics**: If two sessions dispatch insights about the same doc simultaneously, last writer wins. Edits are idempotent-ish (in-place, current-state-only) so redundant edits are low-harm. Contradictory edits are possible but unlikely at expected update frequency.

5. **Orphaned docs**: Docs for deleted subsystems aren't automatically removed. Manual cleanup required.

6. **Proactive mode deferred**: The idea of scanning git diffs during idle time was deferred because the coordination mechanism (getting diff output to a no-Bash agent) was underspecified. The primary value is the insight-dispatch path.

## Key Research Findings

These findings shaped the design and are recorded here for future reference:

1. **Agent hooks (`type: "agent"`) do NOT have conversation context.** They spawn independent subagents that only see `$ARGUMENTS` JSON. Cannot be used for context-rich doc updates.

2. **Compaction timing is adjustable earlier only.** `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` env var triggers compaction sooner (e.g., at 75% capacity), but cannot delay past the default ~83.5% cap.

3. **MagicDocs triggers incrementally, not post-conversation.** `postSamplingHook` fires after each tool-call-bearing model response, not at session end. This validated the incremental-dispatch design.

4. **Agent Teams exists** (code.claude.com/docs/en/agent-teams) and could provide cross-session coordination if needed in the future, but is not part of the current design.

5. **Nobody has documented how Anthropic persists MagicDocs edits.** No public information about commit strategy, worktree usage, or conflict handling. The simplest inference: edits are written to dedicated files and left for the user to commit.

6. **Subagent context is always fresh.** Each subagent starts with zero conversation history. This is why focused insights work better than transcript dumps.

## Design Review Summary

The design was reviewed by a subagent that identified 13 issues. Key changes made:

- **Flipped from daemon to fresh-per-insight** (daemon has worse context hygiene)
- **Main agent picks target doc** (subagent has insufficient context for relevance judgment)
- **CLAUDE.md pointer updated** to mention both `docs/magic/` and co-located docs
- **Proactive mode deferred** (coordination mechanism was underspecified)
- **Stop hook promoted** from optional to core (only channel not dependent on behavioral instruction)
- **Reliability caveat added** (100% `/classify-info` accuracy is the wrong metric — upstream trigger reliability is the real risk)
- **Unstaged edits** chosen over auto-commit (avoids worktree/branch complexity, attribution confusion)

# MagicDocs Remaining Work — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the magicdocs system by updating the spec to reflect current state, rewriting Chapter 5 to match the incremental dispatch architecture, and testing the PreToolUse edit guard hook.

**Architecture:** This is primarily documentation work — rewriting Chapter 5 and updating the spec. The edit guard hook is a configuration task. No new skills to build.

**Tech Stack:** Markdown docs, Claude Code hooks (settings.json), git.

---

### Task 1: Update Spec — Mark Completed Phases

The growth phases table still lists phases 3-5 as separate future work, but they're already covered by existing skills. Update the spec to reflect reality.

**Files:**
- Modify: `docs/specs/2026-04-02-magicdocs-full.md`

- [ ] **Step 1: Update the growth phases table**

Replace the current growth phases table with:

```markdown
## Growth Phases

| Phase | What | Status |
|-------|------|--------|
| **MVP** | Core loop validation (Sonnet 5/5, Haiku 4.5/5) | **DONE** |
| **Phase 1** | `/setup-magicdocs` skill (TDD 9/9) | **DONE** |
| **Phase 2** | `/create-magicdoc` skill (TDD 7/7) | **DONE** |
| **Phase 3** | `/classify-info` → MagicDocs dispatch | **DONE** — no deliverable needed, flow works naturally via existing skill + CLAUDE.md pointer |
| **Phase 4** | Stop hook pruning pass | **DONE** — configured by `/setup-magicdocs` |
| **Phase 5** | PreToolUse edit guard | **DONE** — configured by `/setup-magicdocs` (rough sketch, needs live testing) |
| **Phase 6** | Chapter 5 rewrite | **THIS PLAN** |
| **Pruning** | Staleness detection | **DROPPED** — RED baseline showed agent handles this naturally (5/4) |
| **Deferred** | Proactive idle scanning (git diff during lulls) | Not started |
```

- [ ] **Step 2: Remove the "Skills in phases 1-2 are built serially" note**

This note is no longer relevant since all skills are built.

- [ ] **Step 3: Commit**

```bash
git add docs/specs/2026-04-02-magicdocs-full.md
git commit -m "docs: update spec — mark phases 1-5 complete, pruning dropped"
```

---

### Task 2: Test the PreToolUse Edit Guard Hook

The spec has a rough sketch of the edit guard hook. Before we declare it done, test whether it actually works. This needs to be done in a repo with magicdocs set up.

**Files:**
- Modify: `docs/specs/2026-04-02-magicdocs-full.md` (update hook if needed)

- [ ] **Step 1: Research how $ARGUMENTS works for PreToolUse hooks**

We need to know: when a PreToolUse hook fires on an Edit tool call, what does `$ARGUMENTS` contain? Is it JSON with `file_path`, `old_string`, `new_string`? Or something else?

Search Claude Code docs or run a test hook that echoes `$ARGUMENTS` to a file to see the format.

- [ ] **Step 2: If hook works, update spec to remove "rough sketch" note**

If the hook format is confirmed and the guard works, update the spec to remove the "This is a rough sketch" caveat.

- [ ] **Step 3: If hook doesn't work, fix and update spec**

If `$ARGUMENTS` has a different format than expected, fix the hook command and update both the spec and the `/setup-magicdocs` skill (which installs the hook). Note: the setup skill currently does NOT include the PreToolUse hook — only the Stop hook. If we want the edit guard, we need to add it to the skill's Step 5.

- [ ] **Step 4: Commit**

```bash
git add docs/specs/2026-04-02-magicdocs-full.md skills/setup-magicdocs/SKILL.md
git commit -m "fix: confirm or fix PreToolUse edit guard hook"
```

---

### Task 3: Rewrite Chapter 5 — Introduction and Philosophy

Chapter 5 currently describes a post-conversation Stop hook model. Our research found MagicDocs triggers incrementally via `postSamplingHook`. The chapter needs rewriting to describe the actual architecture while keeping the philosophy sections (Steps 1-2) which are still correct.

**Files:**
- Modify: `docs/05-building-magicdocs.md`

- [ ] **Step 1: Read the current Chapter 5 in full**

Read `docs/05-building-magicdocs.md`. Note which sections are still correct and which need rewriting:

- **Step 1 (philosophy)**: Still correct — keep as-is
- **Step 2 (create manually)**: Still correct — keep as-is
- **"What we're building" intro**: WRONG — says "runs post-conversation", needs to say "triggers incrementally via postSamplingHook"
- **"We'll replicate this using a skill..."**: Needs reframing — we built a plugin with multiple skills, not a single skill + hook

- [ ] **Step 2: Rewrite the intro section**

Replace lines 1-21 (the intro and "What we're building") with updated content that:
- Corrects the trigger timing: `postSamplingHook` during sessions, not post-conversation
- Mentions the airbender plugin as the replication approach
- Keeps the reference architecture description accurate
- Preserves the source citation

The new intro should explain:
- MagicDocs is internal, gated to Anthropic employees
- Our research found it triggers incrementally via `postSamplingHook`, not post-conversation
- We replicated it as a plugin (airbender) with: `/setup-magicdocs` (bootstrap), `/create-magicdoc` (add docs), `/classify-info` (route insights), and a Stop hook (pruning pass)
- The rest of the chapter walks through the underlying philosophy and manual process for understanding before using the plugin

- [ ] **Step 3: Commit intro rewrite**

```bash
git add docs/05-building-magicdocs.md
git commit -m "docs: rewrite Ch5 intro — correct trigger timing, mention airbender plugin"
```

---

### Task 4: Rewrite Chapter 5 — Skills and Automation Sections

Steps 3-5 of the current Chapter 5 describe a manual skill approach (`/update-docs`, `/create-doc`) and a Stop hook automation. These need rewriting to describe the actual system we built.

**Files:**
- Modify: `docs/05-building-magicdocs.md`

- [ ] **Step 1: Rewrite Step 3 (update skill)**

The current Step 3 describes a manual `/update-docs` skill. Our system doesn't have this — updates happen automatically via `/classify-info` dispatch. Rewrite to describe the actual update flow:

1. Main agent encounters non-obvious insight during work
2. `/classify-info` classifies it as MagicDocs
3. Main agent formulates terse insight + specifies target doc
4. Fresh Sonnet subagent dispatched with Read+Edit tools
5. Subagent integrates the insight, exits
6. Edits left unstaged

Include the MagicDocs subagent prompt (from `docs/magic/PROMPT.md`) or reference it.

- [ ] **Step 2: Rewrite Step 4 (creation skill)**

The current Step 4 describes a `/create-doc` skill. Replace with `/create-magicdoc` from the airbender plugin. Update the skill content to match our actual `skills/create-magicdoc/SKILL.md`.

- [ ] **Step 3: Rewrite Step 5 (automation)**

The current Step 5 describes a Stop hook as the primary automation mechanism. Our system uses three trigger channels:

1. **Primary**: `/classify-info` → insight dispatch (during session, with full context)
2. **Manual**: User invokes `/create-magicdoc` or says "remember this"
3. **Safety net**: Stop hook pruning pass (session exit, diffs only — reconciliation, not synthesis)

Rewrite to describe all three channels with the correct framing: the Stop hook is a pruning safety net, not the primary update mechanism.

- [ ] **Step 4: Commit skills/automation rewrite**

```bash
git add docs/05-building-magicdocs.md
git commit -m "docs: rewrite Ch5 skills and automation — match actual system"
```

---

### Task 5: Rewrite Chapter 5 — Summary and Diagram

The "Putting it all together" section has a diagram showing the post-conversation flow. Replace with the actual architecture.

**Files:**
- Modify: `docs/05-building-magicdocs.md`

- [ ] **Step 1: Replace the architecture diagram**

Replace the current linear flow diagram (Session → Stop Hook → Headless Claude → Next Session) with the actual architecture from the full spec:

```
┌─────────────────────────────────────────────────────────┐
│                    Main Agent Session                    │
│                                                          │
│  Normal work → encounters non-obvious thing              │
│  → /classify-info classifies as MagicDocs                │
│  → formulates insight + specifies target doc             │
│  → spawns fresh Sonnet subagent (background)             │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│               MagicDocs Subagent (Sonnet)                │
│                                                          │
│  Tools: Read, Edit only                                  │
│  Reads target doc → integrates insight → exits           │
│  Edits left unstaged for user to commit                  │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│              Stop Hook (Pruning Safety Net)              │
│                                                          │
│  Session ends → checks git diff                          │
│  If changes: reconciles docs against diff                │
│  Fixes stale file paths, removes dead references         │
│  Does NOT add new insights — only prunes                 │
└─────────────────────────────────────────────────────────┘
```

- [ ] **Step 2: Update the discoverability section**

The current section mentions CLAUDE.md pointer and memory files. Update to match what `/setup-magicdocs` actually installs: the CLAUDE.md pointer (two items — location pointer + reviewer note). Drop the memory file suggestion since the CLAUDE.md pointer covers it.

- [ ] **Step 3: Update the verification and maintenance sections**

These are mostly still correct but need minor updates:
- "Check after a hook-triggered update" → clarify this refers to the Stop hook pruning pass, not the primary update mechanism
- Add: "Check `git diff docs/magic/` after working sessions to see insight-triggered updates"
- Keep the maintenance advice (periodic review, keep terse, one doc per concern)

- [ ] **Step 4: Commit summary and diagram rewrite**

```bash
git add docs/05-building-magicdocs.md
git commit -m "docs: rewrite Ch5 summary — correct architecture diagram, update discoverability"
```

---

### Task 6: Final Review and Commit

- [ ] **Step 1: Read the full rewritten Chapter 5**

Read `docs/05-building-magicdocs.md` end to end. Check for:
- Internal consistency (no references to the old Stop-hook-as-primary model)
- Source citations still valid
- No references to `/update-docs` or `/create-doc` (old names)
- All references use `/classify-info`, `/setup-magicdocs`, `/create-magicdoc`

- [ ] **Step 2: Cross-check against the full spec**

Read `docs/specs/2026-04-02-magicdocs-full.md` and verify Chapter 5 doesn't contradict it. Key points to verify:
- Trigger timing (incremental, not post-conversation)
- Three channels (classify-info, manual, Stop hook pruning)
- Subagent toolset (Read+Edit only)
- Edits left unstaged
- Model recommendation (Sonnet)

- [ ] **Step 3: Fix any inconsistencies found**

If the review finds issues, fix them and re-read the affected sections.

- [ ] **Step 4: Final commit**

```bash
git add docs/05-building-magicdocs.md docs/specs/2026-04-02-magicdocs-full.md
git commit -m "docs: Ch5 rewrite complete — matches incremental dispatch architecture"
```

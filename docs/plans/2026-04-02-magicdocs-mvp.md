# MagicDocs MVP — Core Loop Validation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Validate that a subagent with a terse insight and the MagicDocs prompt can produce useful, terse edits to an architectural doc — the core loop that the full MagicDocs system depends on.

**Architecture:** This is a prompt-quality validation, not a code feature. The "test suite" is 5 insights with expected behaviors. The RED/GREEN/REFACTOR cycle targets the subagent prompt. RED = naive prompt (no MagicDocs philosophy). GREEN = full adapted prompt. REFACTOR = fix issues found. Each cycle is a commit on a dedicated branch.

**Tech Stack:** Claude Code Agent tool (model: sonnet and haiku), Glob/Read/Edit tools, git for version control of prompt iterations.

---

### Task 0: Setup — Create Branch and Magic Doc

**Files:**
- Create: `docs/magic/manual-architecture.md`

- [ ] **Step 1: Create a git branch for MVP work**

```bash
git checkout -b magicdocs-mvp
```

- [ ] **Step 2: Create the docs/magic directory**

```bash
mkdir -p docs/magic
```

- [ ] **Step 3: Write the magic doc by hand**

Create `docs/magic/manual-architecture.md` with this exact content:

```markdown
# MAGIC DOC: Manual Architecture

*Five-chapter manual on Claude Code context engineering internals*

## Overview

A manual explaining how Claude Code manages context — prompt construction,
subagent delegation, compaction, and documentation systems. Aimed at context
engineering learners and MagicDocs builders.

## Structure

Five chapters, each building on the previous:
1. Introduction — framing, audiences, sources
2. Context Engineering — prompt pipeline, CLAUDE.md loading, skills, memory, compaction
3. Subagent Architecture — types, context construction, result compression
4. What to Put Where — decision tree for Hook/MagicDocs/Skill/CLAUDE.md/Memory/None
5. Building MagicDocs — manual → skill → hook progression

## Key Entry Points

- `docs/01-introduction.md` — start here
- `skills/classify-info/SKILL.md` — the classification skill
- `skills/classify-info/TESTING.md` — TDD test suite and results

## Non-Obvious Patterns

- Chapter 5 describes MagicDocs as post-conversation (Stop hook), but our
  research found it triggers incrementally via postSamplingHook. Chapter 5
  needs updating.
- The /classify-info skill was developed using TDD: RED baseline (58%) → GREEN
  (85%) → REFACTOR cycles to 100%. The skill teaches only what the model
  gets wrong without help.
- Sources are two third-party repos (claw-code, claude-code-system-prompts),
  not Anthropic's own code. The manual's authors had no role in the exposure.
```

- [ ] **Step 4: Create the test expectations file**

Create `docs/magic/TESTING.md` to record results. Start with the test suite definition:

```markdown
# MagicDocs MVP — Test Results

## Test Suite: 5 Insights

| # | Insight Summary | Expected Behavior |
|---|----------------|-------------------|
| 1 | Chapter 5's Stop hook approach is wrong; postSamplingHook is incremental | Update Non-Obvious Patterns, possibly Structure |
| 2 | New magicdocs design spec exists, should be referenced | Add to Key Entry Points or References |
| 3 | /classify-info skill only adds value at MagicDocs and CLAUDE.md/Memory boundaries | Update Non-Obvious Patterns |
| 4 | "Project uses pnpm" — CLAUDE.md fact, not architecture | NO EDIT — correctly reject |
| 5 | Chapters are dependent, not independent | Update Structure or recognize already captured, either is acceptable |

## Evaluation Criteria

- **Relevance**: Correctly identifies whether insight belongs in the doc
- **Placement**: Puts information in the right section
- **Terseness**: High-signal, no filler
- **Preservation**: Preserves header and existing structure
- **Pruning**: Updates in-place rather than appending
- **Non-edit accuracy**: Correctly declines to edit when appropriate
```

- [ ] **Step 5: Commit setup**

```bash
git add docs/magic/manual-architecture.md docs/magic/TESTING.md
git commit -m "test: create magic doc and test suite for MVP validation"
```

---

### Task 1: RED — Naive Prompt Baseline (Sonnet)

Test what happens with a minimal prompt that has NO MagicDocs philosophy. This establishes the baseline we're improving from.

**Files:**
- Modify: `docs/magic/TESTING.md` (record results)
- Read: `docs/magic/manual-architecture.md` (will be edited by subagent, then reverted)

- [ ] **Step 1: Define the naive prompt**

The naive prompt is intentionally bare — no philosophy, no rules, just the task:

```
Update the documentation file at docs/magic/manual-architecture.md to
incorporate this new information:

{{insight}}

Read the file first, then use the Edit tool to update it.
```

- [ ] **Step 2: Run insight #1 with naive prompt (Sonnet)**

Spawn a Sonnet subagent with:
- Model: `sonnet`
- Tools: `Glob, Read, Edit`
- Prompt: the naive prompt with insight #1 filled in:

```
Update the documentation file at docs/magic/manual-architecture.md to
incorporate this new information:

An agent reading the manual would assume Chapter 5's automation approach
(Stop hook) is the recommended architecture. Actually, our research found
MagicDocs triggers incrementally via postSamplingHook during sessions, not
post-conversation. The manual needs a note about this.

Read the file first, then use the Edit tool to update it.
```

Wait for completion. Review the edit by running `git diff docs/magic/manual-architecture.md`.

- [ ] **Step 3: Record result for insight #1 in TESTING.md**

Score the edit on all 6 criteria. Note specific problems (verbose? wrong section? changelog-style?).

- [ ] **Step 4: Revert the magic doc to original state**

```bash
git checkout -- docs/magic/manual-architecture.md
```

- [ ] **Step 5: Repeat for insights #2-5 with naive prompt (Sonnet)**

For each insight (#2 through #5):
1. Spawn Sonnet subagent with naive prompt + that insight
2. Wait for completion
3. Review edit via `git diff docs/magic/manual-architecture.md`
4. Record result in TESTING.md
5. Revert: `git checkout -- docs/magic/manual-architecture.md`

The full insights to use:

**Insight #2:**
```
The design spec for the magicdocs system is in docs/magicdocs-design-questions.md.
This is a new document that should be referenced.
```

**Insight #3:**
```
An agent would assume the /classify-info skill covers all 6 classification categories
equally. Actually, the model natively gets Hook, Skill, CLAUDE.md core, and None
correct without help. The skill's value is entirely at the MagicDocs boundary and
the CLAUDE.md/Memory boundary.
```

**Insight #4:**
```
The project uses pnpm for package management.
```

**Insight #5:**
```
An agent would assume all five chapters are independent. Actually, each chapter
builds on the previous — you can't understand the decision tree (Ch4) without
understanding the prompt pipeline (Ch2) and subagent architecture (Ch3).
```

- [ ] **Step 6: Commit RED baseline results**

```bash
git add docs/magic/TESTING.md
git commit -m "test(red): record naive prompt baseline — sonnet"
```

---

### Task 2: RED — Naive Prompt Baseline (Haiku)

Same test suite, same naive prompt, but with Haiku. This tells us if the cheaper model is viable.

**Files:**
- Modify: `docs/magic/TESTING.md` (record results)

- [ ] **Step 1: Run all 5 insights with naive prompt (Haiku)**

For each insight (#1 through #5):
1. Spawn Haiku subagent (`model: "haiku"`) with naive prompt + that insight
2. Tools: `Glob, Read, Edit`
3. Wait for completion
4. Review edit via `git diff docs/magic/manual-architecture.md`
5. Record result in TESTING.md under a "RED Baseline — Haiku" section
6. Revert: `git checkout -- docs/magic/manual-architecture.md`

Use the exact same insight text and naive prompt from Task 1.

- [ ] **Step 2: Compare Sonnet vs Haiku baseline**

Add a comparison section in TESTING.md noting:
- Which model produced better edits?
- Did either model correctly reject insight #4?
- Any qualitative differences in terseness, placement, structure preservation?

- [ ] **Step 3: Commit RED baseline results (Haiku)**

```bash
git add docs/magic/TESTING.md
git commit -m "test(red): record naive prompt baseline — haiku"
```

---

### Task 3: GREEN — Full MagicDocs Prompt (Sonnet)

Now write the full adapted prompt with the MagicDocs philosophy and test it.

**Files:**
- Create: `docs/magic/PROMPT.md` (the prompt template, for easy iteration)
- Modify: `docs/magic/TESTING.md` (record results)

- [ ] **Step 1: Write the full adapted prompt**

Create `docs/magic/PROMPT.md` with this content:

```markdown
# MagicDocs Subagent Prompt

Template for dispatching insights to a MagicDocs update subagent.
Variables: {{insight}}, {{docPath}}

---

You are a documentation maintenance agent. Your ONLY task is to integrate
a specific insight into an architectural documentation file (Magic Doc),
then stop.

## Insight to integrate

{{insight}}

## Target document

Read the file at {{docPath}}, then update it to incorporate the insight
above. You can make multiple edits (update multiple sections as needed) —
make all Edit tool calls in parallel in a single message. If there's
nothing substantial to add, simply respond with a brief explanation and
do not call any tools.

## Critical Rules

- Preserve the Magic Doc header exactly as-is (the line starting with
  `# MAGIC DOC:`)
- If there's an italicized line immediately after the header, preserve it
  exactly as-is
- Keep the document CURRENT with the latest state of the codebase — this
  is NOT a changelog or history
- Update information IN-PLACE to reflect the current state — do NOT append
  historical notes or track changes over time
- Remove or replace outdated information rather than adding "Previously..."
  or "Updated to..." notes
- Clean up or DELETE sections that are no longer relevant
- Fix obvious errors: typos, grammar, broken formatting, incorrect
  information
- Keep the document well organized: clear headings, logical section order,
  consistent formatting

## Documentation Philosophy

BE TERSE. High signal only. No filler words or unnecessary elaboration.

Documentation is for OVERVIEWS, ARCHITECTURE, and ENTRY POINTS — not
detailed code walkthroughs.

Focus on: WHY things exist, HOW components connect, WHERE to start
reading, WHAT patterns are used.

Skip: detailed implementation steps, exhaustive API docs, play-by-play
narratives.

**What TO document:**
- High-level architecture and system design
- Non-obvious patterns, conventions, or gotchas
- Key entry points and where to start reading code
- Important design decisions and their rationale
- Critical dependencies or integration points
- References to related files, docs, or code

**What NOT to document:**
- Anything obvious from reading the code itself
- Exhaustive lists of files, functions, or parameters
- Step-by-step implementation details
- Low-level code mechanics
- Information already in CLAUDE.md or other project docs

## When NOT to edit

If the insight is not substantial, is already captured in the doc, or
doesn't belong in architectural documentation (e.g., it's a behavioral
preference, a CLAUDE.md-level fact, or an implementation detail), respond
with a brief explanation and make no edits.
```

- [ ] **Step 2: Run insight #1 with full prompt (Sonnet)**

Spawn a Sonnet subagent with:
- Model: `sonnet`
- Tools: `Glob, Read, Edit`
- Prompt: the content of PROMPT.md with `{{insight}}` replaced by insight #1 text and `{{docPath}}` replaced by `docs/magic/manual-architecture.md`

Wait for completion. Review the edit via `git diff docs/magic/manual-architecture.md`.

- [ ] **Step 3: Record result for insight #1 in TESTING.md**

Score on all 6 criteria. Compare against the RED baseline for the same insight.

- [ ] **Step 4: Revert the magic doc**

```bash
git checkout -- docs/magic/manual-architecture.md
```

- [ ] **Step 5: Repeat for insights #2-5 with full prompt (Sonnet)**

For each insight (#2 through #5):
1. Spawn Sonnet subagent with full prompt + that insight
2. Wait for completion
3. Review edit via `git diff docs/magic/manual-architecture.md`
4. Record result in TESTING.md under a "GREEN — Sonnet" section
5. Revert: `git checkout -- docs/magic/manual-architecture.md`

- [ ] **Step 6: Commit GREEN results (Sonnet)**

```bash
git add docs/magic/PROMPT.md docs/magic/TESTING.md
git commit -m "test(green): record full prompt results — sonnet"
```

---

### Task 4: GREEN — Full MagicDocs Prompt (Haiku)

Same full prompt, Haiku model. Determines if the cheaper model is good enough.

**Files:**
- Modify: `docs/magic/TESTING.md` (record results)

- [ ] **Step 1: Run all 5 insights with full prompt (Haiku)**

For each insight (#1 through #5):
1. Spawn Haiku subagent (`model: "haiku"`) with full prompt + that insight
2. Tools: `Glob, Read, Edit`
3. Wait for completion
4. Review edit via `git diff docs/magic/manual-architecture.md`
5. Record result in TESTING.md under a "GREEN — Haiku" section
6. Revert: `git checkout -- docs/magic/manual-architecture.md`

- [ ] **Step 2: Compare Sonnet vs Haiku with full prompt**

Update the comparison section in TESTING.md:
- Did the full prompt fix the same issues for both models?
- Is Haiku good enough, or does it need Sonnet?
- Any new failure patterns specific to one model?

- [ ] **Step 3: Commit GREEN results (Haiku)**

```bash
git add docs/magic/TESTING.md
git commit -m "test(green): record full prompt results — haiku"
```

---

### Task 5: REFACTOR — Analyze and Fix

Based on GREEN results, identify failures and iterate on the prompt.

**Files:**
- Modify: `docs/magic/PROMPT.md` (refine the prompt)
- Modify: `docs/magic/TESTING.md` (record refactor results)

- [ ] **Step 1: Analyze GREEN results**

Look at the TESTING.md results. For each failure, identify the pattern:

| Failure Pattern | Prompt Fix |
|----------------|------------|
| Verbose edits, filler words | Strengthen terseness: add "Maximum 2-3 sentences per addition" |
| Changelog-style ("Added X", "Updated Y") | Add explicit anti-pattern: "Never write in past tense about changes you're making" |
| Wrong section placement | Add section-matching guidance: "Place information in the most relevant existing section" |
| Edited when shouldn't (insight #4) | Strengthen the "When NOT to edit" section with examples |
| Didn't edit when should have | Lower the threshold: remove "not substantial" qualifier |
| Corrupted structure | Add "Never remove or rename existing section headers" |

- [ ] **Step 2: Update the prompt in PROMPT.md**

Apply fixes based on the failure analysis. Keep changes minimal — only fix what's broken.

- [ ] **Step 3: Re-run failed tests with updated prompt**

Only re-run the insights that failed in GREEN. Use whichever model(s) had failures.

For each re-run:
1. Spawn subagent with updated prompt + the failing insight
2. Review edit via `git diff docs/magic/manual-architecture.md`
3. Record result in TESTING.md under a "REFACTOR" section
4. Revert: `git checkout -- docs/magic/manual-architecture.md`

- [ ] **Step 4: If new failures appear, iterate**

If the prompt fix broke something that was passing before, adjust and re-run. Keep iterating until:
- All 5 insights produce correct behavior (edit or non-edit)
- No regressions from GREEN

- [ ] **Step 5: Commit REFACTOR results**

```bash
git add docs/magic/PROMPT.md docs/magic/TESTING.md
git commit -m "refactor: improve prompt based on test failures"
```

Repeat steps 2-5 if additional REFACTOR rounds are needed. Each round gets its own commit.

---

### Task 6: Evaluate and Document Outcome

**Files:**
- Modify: `docs/magic/TESTING.md` (final summary)

- [ ] **Step 1: Write the final summary in TESTING.md**

Add a "Summary" section with:

- Final score: X/5 for Sonnet, X/5 for Haiku
- Model recommendation: Sonnet, Haiku, or either
- Prompt iteration count: how many REFACTOR rounds were needed
- Key prompt adjustments that made the biggest difference
- Verdict: does the core loop work? (YES → proceed to full design, NO → rethink context model)

- [ ] **Step 2: Write the progression table**

```markdown
## Progression

| Phase | Sonnet Score | Haiku Score | Key Fixes |
|-------|-------------|-------------|-----------|
| RED baseline | X/5 | X/5 | — |
| GREEN | X/5 | X/5 | Full MagicDocs philosophy |
| REFACTOR 1 | X/5 | X/5 | [describe fixes] |
| REFACTOR N | X/5 | X/5 | [describe fixes] |
```

- [ ] **Step 3: Commit final evaluation**

```bash
git add docs/magic/TESTING.md
git commit -m "docs: MVP evaluation complete — [PASS/FAIL]"
```

- [ ] **Step 4: If MVP passes, report back**

The MVP validates the core loop. Next step: invoke `/writing-skills` to build `/setup-magicdocs` and `/create-magicdoc` per `docs/specs/2026-04-02-magicdocs-full.md`.

If the MVP fails, document what went wrong and what the context model needs (e.g., conversation summaries instead of terse insights, different prompt structure, etc.).

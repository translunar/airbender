# Spec: MagicDocs MVP — Core Loop Validation

**Date**: 2026-04-02
**Status**: Draft
**Prerequisite reading**: `docs/reference/magicdocs-design-questions.md` (design Q&A), `docs/specs/2026-04-02-magicdocs-full.md` (full spec)

## Hypothesis

A Sonnet subagent, given a terse insight message and the Anthropic MagicDocs prompt, can produce useful, terse, architecturally-focused edits to an existing magic doc — without needing conversation context or codebase exploration.

## What We're Testing

The core loop:

```
Main agent encounters non-obvious thing
  → formulates insight ("An agent would assume X, but actually Y")
  → specifies target doc
  → spawns Sonnet subagent with MagicDocs prompt + insight
  → subagent reads doc, edits it, exits
  → edit is useful and follows the MagicDocs philosophy
```

If the edit quality is bad, we rethink the context model before building any automation. If it's good, we proceed to the full design.

## What We're NOT Testing

- Trigger reliability (whether the main agent notices doc-worthy things)
- Automation (hooks, `/classify-info` integration)
- Bootstrap/setup (the installer skill)
- Concurrent sessions
- Proactive scanning

Those are all infrastructure around the core loop. They only matter if the loop works.

## Steps

### 1. Create a magic doc for this repo

Write `docs/magic/manual-architecture.md` by hand, covering the airbender manual's architecture:

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

### 2. Formulate test insights

Create 3-5 insights of varying quality and relevance to test the subagent:

| # | Insight | Target Doc | Expected Behavior |
|---|---------|------------|-------------------|
| 1 | "An agent reading the manual would assume Chapter 5's automation approach (Stop hook) is the recommended architecture. Actually, our research found MagicDocs triggers incrementally via postSamplingHook during sessions, not post-conversation. The manual needs a note about this." | manual-architecture.md | Update "Non-Obvious Patterns" section, possibly add to structure notes |
| 2 | "The design spec for the magicdocs system is in docs/magicdocs-design-questions.md. This is a new document that should be referenced." | manual-architecture.md | Add reference to Key Entry Points or a new References section |
| 3 | "An agent would assume the /classify-info skill covers all 6 classification categories equally. Actually, the model natively gets Hook, Skill, CLAUDE.md core, and None correct without help. The skill's value is entirely at the MagicDocs boundary and the CLAUDE.md/Memory boundary." | manual-architecture.md | Update Non-Obvious Patterns with this insight about the skill |
| 4 | "The project uses pnpm for package management." | manual-architecture.md | Should produce NO edit — this is a CLAUDE.md fact, not architectural documentation. Tests whether the subagent correctly ignores non-doc-worthy information. |
| 5 | "An agent would assume all five chapters are independent. Actually, each chapter builds on the previous — you can't understand the decision tree (Ch4) without understanding the prompt pipeline (Ch2) and subagent architecture (Ch3)." | manual-architecture.md | Should update Structure section to note the dependency chain, or recognize it's already captured ("each building on the previous") and make no edit. |

### 3. Build the subagent prompt

Adapt Anthropic's `agent-prompt-update-magic-docs.md` for our dispatch model. The prompt should:

- Include the full MagicDocs philosophy (what to/not to document, terseness, current-state-only)
- Accept the insight as input (replacing "Based on the user conversation above")
- Instruct the agent to read the target doc via Read tool before editing
- Include the header preservation rules
- Instruct the agent to make no edit if the insight isn't substantial or is already captured

Template:

```
You are a documentation maintenance agent. Your job is to integrate a specific
insight into an architectural documentation file (Magic Doc).

## Insight to integrate

{{insight}}

## Target document

Read the file at {{docPath}}, then update it to incorporate the insight above.

## Rules

[... Anthropic's CRITICAL RULES and DOCUMENTATION PHILOSOPHY verbatim ...]

If the insight is not substantial, is already captured in the doc, or doesn't
belong in architectural documentation (e.g., it's a behavioral preference or
an implementation detail), respond with a brief explanation and make no edits.
```

### 4. Run the tests

Run each test insight against **both Sonnet and Haiku**. Anthropic uses Sonnet, but their agent gets the full conversation transcript (harder task). Our agent gets a pre-digested insight and just needs to read a doc and make a terse edit — potentially simple enough for Haiku, which would be significantly cheaper.

For each test insight, for each model:

1. Spawn a subagent (`model: "sonnet"` or `model: "haiku"`) with `run_in_background: true`
2. Give it tools: `Glob, Read, Edit`
3. Pass the prompt with the insight and target doc path
4. Review the edit (or non-edit) against expected behavior
5. Compare Sonnet vs Haiku edit quality

### 5. Evaluate

Score each test on:

- **Relevance**: Did it correctly identify whether the insight belongs in the doc?
- **Placement**: Did it put the information in the right section?
- **Terseness**: Is the edit high-signal, no filler?
- **Preservation**: Did it preserve the header and existing structure?
- **Pruning**: Did it update in-place rather than appending?
- **Non-edit accuracy**: For insight #4, did it correctly decline to edit?

### 6. Record results

Use a git branch for the MVP work. Each RED/GREEN/REFACTOR cycle gets its own commit, making it easy to revert if things don't work out.

Document results in a format similar to `skills/classify-info/TESTING.md`:

- RED baseline: what happens with a naive prompt (no MagicDocs philosophy)
- GREEN: what happens with the full adapted prompt
- Issues found and adjustments needed

## Success Criteria

The MVP succeeds if:
- Insights #1-3 produce useful, terse edits in the right sections
- Insight #4 produces no edit (correctly rejects non-architectural info)
- Insight #5 makes a reasonable judgment (edit or correct non-edit)
- Edits follow MagicDocs philosophy (terse, current-state, no filler)
- The adapted prompt doesn't need major rework
- We have a clear recommendation on Sonnet vs Haiku (or both are fine)

## Failure Modes

- **Subagent adds too much**: verbose edits, filler words, changelog-style notes → prompt needs stronger terseness enforcement
- **Subagent edits wrong section**: places info in the wrong part of the doc → prompt needs better placement guidance
- **Subagent can't judge relevance**: edits when it shouldn't or doesn't when it should → the terse insight format doesn't give enough context, need to upgrade to conversation summary
- **Subagent corrupts structure**: breaks formatting, damages existing content → need guardrails or a different tool configuration

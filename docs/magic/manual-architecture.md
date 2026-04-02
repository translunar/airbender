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

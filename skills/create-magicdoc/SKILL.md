---
name: create-magicdoc
description: Use when adding a new Magic Doc for a subsystem or area of the codebase, after the magicdocs system has been set up with /setup-magicdocs
---

# Create Magic Doc

Create a single new Magic Doc for a subsystem or area of the codebase.

## Arguments

The title follows the command: `/create-magicdoc Authentication`

## Prerequisite Check

Before proceeding, verify the magicdocs system is set up: check that `docs/magic/` exists and CLAUDE.md mentions Magic Docs. If not, tell the user to run `/setup-magicdocs` first and stop.

## Steps

1. **Check for duplicates.** Glob `docs/magic/*.md` and grep for `^# MAGIC DOC:` repo-wide. If a doc with a similar title or covering the same subsystem exists, tell the user and stop.

2. **Explore the subsystem.** Read entry points and key files — not exhaustively. Focus on architecture: how components connect, what's non-obvious, where to start reading. Stop exploring once you understand the shape of the subsystem.

3. **Write the doc** to `docs/magic/<slug>.md` using this exact format:

```markdown
# MAGIC DOC: <Title>

*<one-line description>*

## Overview

<2-3 sentences: what this subsystem is, why it exists>

## Key Entry Points

<where to start reading, key files>

## Non-Obvious Patterns

<gotchas, conventions, things that would surprise a newcomer>
```

Add `## Dependencies` only if external dependencies are non-obvious.

4. **Show the user** the created doc and ask if anything should be adjusted.

## Content Rules

**BE TERSE.** Maximum 500 words. This is the hardest part — resist the urge to document everything you found.

**Document:**
- WHY things exist
- HOW components connect
- WHERE to start reading
- WHAT patterns would surprise a newcomer

**Do NOT document:**
- Exhaustive lists of files, functions, routes, message types, or parameters
- Implementation details (how a specific function works internally)
- Data shapes, schemas, or type definitions
- Step-by-step code walkthroughs
- Anything obvious from reading the code itself

The code IS the detail. The Magic Doc is the map.

**Section count:** Use only the standard sections (Overview, Key Entry Points, Non-Obvious Patterns, optionally Dependencies). Do NOT add extra sections for specific technical concerns — if something is important, it fits in Non-Obvious Patterns.

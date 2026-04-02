---
name: classify-info
description: Use when the user asks to remember, save, store, or persist information — or when you learn something that should outlive the current session. Classifies into the correct persistence mechanism.
---

# Classify Info

Classify information into the right persistence mechanism: Hook, MagicDocs, Skill, CLAUDE.md, Memory, or None.

## Decision tree

**Actionable?** Can Claude behave differently — in this project or any of the user's projects? No → **None**.

**Fully mechanical?** Specific command, no judgment, same every time → **Hook**. If the intent is mechanical but the exact command isn't specified, it's still a Hook — help fill in the command.

**Describes or prescribes?** Descriptions of architecture, data flow, how components connect → **MagicDocs**. "The frontend uses React context, not Redux" *describes* what the system is, even though it mentions what not to use. Prescriptions continue below.

**Has steps?** Multi-step procedures → **Skill**. Single constraints continue below.

**Always relevant?** Would Claude make a wrong assumption without this on its very first action in any session? Yes → **CLAUDE.md**. No → **Memory**.

Two common errors at this boundary:

- **"Always true" ≠ "always relevant."** "User prefers bundled PRs" is always true but not relevant when fixing a CSS bug → Memory. "Don't mock DB in integration tests" is always true but only matters when writing tests → Memory. "User finds excessive comments patronizing" is always true but many sessions are research/debugging/discussion without writing code → Memory.
- **Ubiquitous actions are always relevant.** "Make sure tests pass before committing" sounds topic-specific but committing happens most sessions → CLAUDE.md. "Deploy to Fly.io, not AWS" shapes config, CI, env vars broadly → CLAUDE.md.

## Routing

Hook and MagicDocs are always project-scoped. For Skill, CLAUDE.md, and Memory, ask: does this follow the code or follow the person?

| Classification | Action |
|---|---|
| Hook | Provide hook config for `.claude/settings.json` |
| MagicDocs | `docs/magic/` if available; CLAUDE.md with advisory if not |
| Skill | **REQUIRED SUB-SKILL:** Use superpowers:writing-skills |
| CLAUDE.md | Project `CLAUDE.md`, subdirectory, or `~/.claude/CLAUDE.md` |
| Memory | Project-scoped or `~/.claude/memory/` |
| None | Explain why it's not actionable |

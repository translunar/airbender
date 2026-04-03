# Airbender

A Claude Code reference manual for context engineering and MagicDocs plugin.

Claude Code has six different mechanisms for shaping agent behavior: CLAUDE.md, skills, memory, hooks, MagicDocs, and the insights system. Most people put everything in CLAUDE.md. This is a mistake.

CLAUDE.md is loaded once at session start, buried after five sections of Anthropic's own behavioral instructions, and has no verification loop — there's no mechanism to check whether a CLAUDE.md instruction actually changed behavior. Multi-step workflows, architectural descriptions, and sometimes-relevant preferences all end up in CLAUDE.md where they consume tokens on every API call and get ignored when it matters most. The other five mechanisms exist for good reasons, and each one outperforms CLAUDE.md for specific types of information.

This project grew from researching those differences. It includes:

1. **A five-chapter manual** explaining how Claude Code manages context internally — how it assembles its prompt, loads instructions, selects memories, compacts conversations, and maintains documentation. Every architectural claim cites source files from publicly available repositories.

2. **A Claude Code plugin** that replicates Anthropic's internal MagicDocs system — auto-maintained architectural documentation that captures non-obvious patterns, gotchas, design rationale, and entry points. MagicDocs is gated to Anthropic employees; this plugin rebuilds it using public primitives (skills, subagents, hooks).

The MagicDocs implementation was designed through iterative brainstorming, validated with TDD (RED/GREEN/REFACTOR against a real codebase), and tested against the actual Anthropic agent prompt for fidelity.

## The Decision Tree

The core problem this project addresses: *where should this instruction go?* The answer depends on properties of the information, not its topic.

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

A few examples to build intuition:

| Instruction | Classification | Why |
|-------------|---------------|-----|
| "Run `pnpm test` before any `git commit`" | **Hook** | Fully mechanical, specific command, no judgment needed |
| "The auth middleware uses Redis for sessions with a 24h TTL" | **MagicDocs** | Describes architecture — how the system works |
| "When committing: run tests, check coverage, lint, draft message, wait for approval" | **Skill** | Multi-step procedure, needs to arrive fresh at point of action |
| "This project uses pnpm, not npm" | **CLAUDE.md** | Prior that shapes assumptions before any reasoning starts, every session |
| "User prefers bundled PRs over many small ones" | **Memory** | Preference, sometimes relevant but not always |
| "The sky is blue" | **None** | Not actionable — Claude can't behave differently |

The full decision tree with 26 test cases and detailed rationale is in [Chapter 4: What to Put Where](docs/04-what-to-put-where.md). The `/classify-info` skill (included in this plugin) implements this tree and scores 100% on the test suite.

## Install

```bash
claude plugin marketplace add translunar/airbender
claude plugin install airbender
```

To upgrade:

```bash
claude plugin marketplace update airbender
claude plugin update airbender
```

## Quickstart

### Set up MagicDocs in your repo

```
/setup-magicdocs
```

This explores your repo and asks how you want to slice the docs — one per subsystem ("Authentication", "Billing"), one per top-level directory, one per entry point, or a hybrid. It then creates skeleton docs in `docs/magic/`, adds a CLAUDE.md pointer, and configures a Stop hook for automatic staleness pruning.

### Add a doc for a new subsystem

```
/create-magicdoc Authentication
```

Explores the relevant code, writes a terse architectural doc (~400 words), and shows it to you for review.

### How updates happen

Once set up, MagicDocs updates through three channels:

1. **Automatic insight dispatch.** During normal work, the agent encounters something non-obvious. The `/classify-info` skill routes it as MagicDocs. The agent formulates a terse insight, specifies the target doc, and dispatches a background Sonnet subagent that reads the doc and integrates the insight. Fire-and-forget.

2. **Manual.** Say "remember this" or run `/create-magicdoc`. Highest signal.

3. **Stop hook pruning.** At session exit, a safety-net hook checks `git diff` against existing magic docs and fixes stale file paths or dead references. This catches structural drift the agent forgot to document — reconciliation, not synthesis.

### Check for staleness

No special skill needed. Just ask:

```
Check the magic docs for stale content.
```

The agent naturally detects dead file references, deleted functions, wrong claims, and structural drift — and fixes them.

## The Manual

Five chapters, each building on the previous:

| Chapter | Topic |
|---------|-------|
| [1. Introduction](docs/01-introduction.md) | What this is, who it's for, sources |
| [2. Context Engineering](docs/02-context-engineering.md) | Prompt pipeline, CLAUDE.md loading, skills, memory, compaction, MagicDocs |
| [3. Subagent Architecture](docs/03-subagent-architecture.md) | Agent types, context construction, result compression, coordinator pattern |
| [4. What to Put Where](docs/04-what-to-put-where.md) | Decision tree, the five mechanisms, good/bad examples, few-shot test suite |
| [5. Building MagicDocs](docs/05-building-magicdocs.md) | Philosophy, manual creation, automated system, three trigger channels |

## Skills Reference

| Skill | Purpose |
|-------|---------|
| `/setup-magicdocs` | Bootstrap the MagicDocs system in a repo (run once) |
| `/create-magicdoc <title>` | Add a magic doc for a subsystem |
| `/classify-info` | Classify information into Hook / MagicDocs / Skill / CLAUDE.md / Memory / None |

## Design Docs

The full design process is documented in the repo:

- [Design questions](docs/reference/magicdocs-design-questions.md) — 13 design decisions with rationale, Anthropic comparison, and review findings
- [Full spec](docs/specs/2026-04-02-magicdocs-full.md) — complete system architecture
- [MVP spec](docs/specs/2026-04-02-magicdocs-mvp.md) — core loop validation
- [MVP test results](docs/magic/TESTING.md) — RED/GREEN/REFACTOR progression (Sonnet 5/5, Haiku 4.5/5)

## Sources

Architectural claims in the manual cite two publicly available repositories:

- [Piebald-AI/claude-code-system-prompts](https://github.com/Piebald-AI/claude-code-system-prompts) — extracted Claude Code system prompts (MIT License)
- [instructkr/claw-code](https://github.com/instructkr/claw-code) — Python/Rust reimplementation of Claude Code's architecture

The authors of this project had no role in the exposure of Claude Code's source material.

Thanks also to [@obra](https://github.com/obra) for [superpowers](https://github.com/obra/superpowers), which I relied on heavily for this work.

## Status

**Experimental.** This project replicates internal Anthropic infrastructure using public primitives — it works, but it's not battle-tested across many codebases. Use at your own risk.

Issues and PRs are welcome. If you try this on your project and something breaks, doesn't work as expected, or could be better — please [open an issue](https://github.com/translunar/airbender/issues).

## License

MIT for all original work. See [LICENSE](LICENSE) for details.

Portions of `docs/magic/PROMPT.md` contain prompt text adapted from Anthropic's internal system prompts and remain the property of Anthropic PBC.

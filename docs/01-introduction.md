# How Claude Code Thinks: A Context Engineering Manual

## What this is

This manual explains how Claude Code manages context internally — how it decides what to load into its prompt, where your instructions land relative to everything else, why some customization mechanisms work better than others, and how to build automated documentation systems that mirror Anthropic's own internal tooling.

This is not a getting-started guide or installation tutorial. It assumes you've used Claude Code and want to understand the machinery behind it.

## Who it's for

**Context engineering learners.** You use Claude Code and want to understand why it behaves the way it does. Why does it sometimes "forget" instructions you put in CLAUDE.md? Why do skills feel more reliable than CLAUDE.md? What happens to your conversation context during long sessions? This manual answers those questions by showing you the actual architecture.

**MagicDocs builders.** You want to build a system that automatically generates and maintains architectural documentation for your codebase — mirroring what Anthropic does internally with a feature called MagicDocs. This manual walks you through the progression from manual documentation to skill-based automation to fully automated hooks.

## Sources

Every architectural claim in this manual cites specific source files from two publicly available open-source repositories:

- [instructkr/claw-code](https://github.com/instructkr/claw-code) — A Python and Rust reimplementation of Claude Code's architecture by Sigrid Jin. The Rust port contains working implementations of system prompt construction, session management, context compaction, and permission handling. Where we cite Rust source files (e.g., `prompt.rs`, `compact.rs`), we're referencing this implementation.

- [Piebald-AI/claude-code-system-prompts](https://github.com/Piebald-AI/claude-code-system-prompts) — A collection of over 250 prompt files extracted from Claude Code, organized into categories including agent prompts, system prompts, system reminders, skill prompts, tool descriptions, and data references. Where we cite prompt files (e.g., `agent-prompt-update-magic-docs.md`), we're referencing this collection.

The authors of this manual are not responsible for and had no role in the exposure of Claude Code's source material. These repositories were created and published by independent third parties. We reference them as publicly available research sources. All citations link directly to source files so that readers can verify claims independently.

## How to read this manual

Each chapter builds on the previous one:

1. **Context Engineering** — The core mental model. How Claude Code assembles its prompt, loads your instructions, selects memories, compacts conversations, and maintains documentation. Read this first.

2. **Subagent Architecture** — How Claude Code delegates work to subagents running on different models with different tool sets and fresh context windows. Understanding this is important before deciding how to structure your own customizations.

3. **What to Put Where** — The practical guide. Five mechanisms for customizing Claude Code's behavior (CLAUDE.md, skills, memory, hooks, MagicDocs), with examples showing what belongs where and a decision flowchart for choosing.

4. **Building MagicDocs** — A progressive build guide. Start by understanding the philosophy, create docs manually, wrap it in a skill, then automate it with hooks.

Every architectural claim cites its source inline as a link. When you see `[source: filename](URL)`, that's a direct link to the code or prompt that supports the claim. If something sounds surprising, click the link and verify.

## Next

[Chapter 2: Context Engineering →](02-context-engineering.md)

# Context Engineering

Claude Code doesn't have a static system prompt. It assembles its prompt dynamically from multiple sources, in a specific order, managing what gets loaded, when, and how it survives over the course of a conversation. Understanding this pipeline is the foundation for everything else in this manual.

## The prompt is a pipeline

Every time Claude Code makes an API call, it constructs a system prompt from multiple sections assembled in a fixed order. A boundary marker called `SYSTEM_PROMPT_DYNAMIC_BOUNDARY` separates the static behavioral instructions (written by Anthropic) from the dynamic project-specific context (your instructions, your project state).

Everything above the boundary is the same across all Claude Code sessions. Everything below it changes based on your project, your configuration, and your CLAUDE.md files.

[source: `prompt.rs` — `build()` method and `SYSTEM_PROMPT_DYNAMIC_BOUNDARY` constant](https://github.com/instructkr/claw-code/blob/main/rust/crates/runtime/src/prompt.rs)

## System prompt construction — the 10 sections

The system prompt is built in this exact order:

| Section | What it contains | Above or below the boundary? |
|---|---|---|
| 1. Intro | Role definition ("You are an interactive agent that helps users with software engineering tasks") | Above |
| 2. Output style | Custom output style if configured (e.g., "Concise", "Prefer short answers") | Above |
| 3. System rules | Tool permissions, hooks, compression behavior, system-reminder tags | Above |
| 4. Doing tasks | Coding guidelines — read before modifying, no speculative abstractions, security awareness | Above |
| 5. Actions | Safety and reversibility — "measure twice, cut once" | Above |
| 6. **DYNAMIC BOUNDARY** | `__SYSTEM_PROMPT_DYNAMIC_BOUNDARY__` | — |
| 7. Environment | Model name, working directory, date, platform/OS | Below |
| 8. Project context | Today's date, git status snapshot | Below |
| 9. Claude instructions | **Your CLAUDE.md files** — concatenated verbatim | Below |
| 10. Runtime config | Contents of settings.json files | Below |

The critical takeaway: your CLAUDE.md content lands near the end of the system prompt — **after** five sections of Anthropic's own behavioral instructions. (When an output style is configured, CLAUDE.md is section 9; without one, it shifts to section 8 as section 2 is omitted. Either way, it's after sections 1-5.) When your CLAUDE.md says one thing and the built-in instructions say another, the built-in instructions have positional advantage.

[source: `prompt.rs` — `build()`, `get_simple_intro_section()`, `get_simple_system_section()`, `get_simple_doing_tasks_section()`, `get_actions_section()`, `render_instruction_files()`, `render_config_section()`](https://github.com/instructkr/claw-code/blob/main/rust/crates/runtime/src/prompt.rs)

## How CLAUDE.md files are loaded

Claude Code walks the directory tree from the filesystem root up to your current working directory. At each level, it looks for three files:

1. `CLAUDE.md`
2. `CLAUDE.local.md`
3. `.claude/CLAUDE.md`

Every file it finds is read and concatenated into the system prompt, in order from root to cwd. There is no processing, no summarization, and no relevance filtering. If the file exists and isn't empty, its full text goes into the prompt verbatim.

This means:
- A `CLAUDE.md` at your repo root applies to every session in that repo.
- A `CLAUDE.local.md` next to it can hold machine-specific context (local paths, personal preferences) that shouldn't be committed.
- Nested `CLAUDE.md` files in subdirectories add context as you work deeper in the tree.
- Every token in every CLAUDE.md file is consumed on every API call for the entire session, whether it's relevant to the current task or not.

[source: `prompt.rs` — `discover_instruction_files()` function](https://github.com/instructkr/claw-code/blob/main/rust/crates/runtime/src/prompt.rs)

[source: `prompt.rs` — test `discovers_instruction_files_from_ancestor_chain` confirming the ancestor walk behavior](https://github.com/instructkr/claw-code/blob/main/rust/crates/runtime/src/prompt.rs)

## How skills are loaded

Skills are not part of the system prompt at startup. They use deferred loading — their names and `when_to_use` descriptions are listed in a system-reminder at session start, but their full content is only loaded when invoked.

Skills are discovered from `.claude/skills/{name}/SKILL.md` files in your project directory. Each skill has YAML frontmatter with fields like `name`, `description`, `when_to_use`, and `allowed-tools`. At session start, only the names and descriptions are loaded — the full markdown body stays on disk until needed.

When you type a slash command like `/commit` or when the system decides a skill is relevant based on the `when_to_use` field, the `SkillTool` is called. The skill's markdown content is then injected into the conversation as a **tool result** — a message that appears in the most recent part of the conversation, right at the point of action.

This is why skills are more effective than CLAUDE.md for behavioral instructions. A skill arrives as a fresh, contextually relevant instruction at the moment Claude is about to act. CLAUDE.md was loaded thousands of tokens ago at the start of the session.

The `when_to_use` field in a skill's frontmatter is flagged as "critical for auto-invocation." The matching is semantic — Claude reads the `when_to_use` text and judges whether the current task matches. This is the same two-stage pattern used across the system (see "Descriptions are selection indices" in [Chapter 4](04-what-to-put-where.md)): cheap filter on description, then expensive load of full content. If `when_to_use` is vague ("use when helpful"), the skill won't auto-trigger. If it's specific ("use when committing code or the user asks to commit"), it matches clearly.

[source: `system-prompt-skillify-current-session.md` — skill structure and `when_to_use` criticality](https://github.com/Piebald-AI/claude-code-system-prompts/blob/main/system-prompts/system-prompt-skillify-current-session.md). The deferred loading, disk discovery, and tool-result injection behavior is inferred from Claude Code's observable architecture — skills are invoked via `SkillTool`, which returns their content as a tool result in the conversation.

## How memory is selected and injected

Claude Code maintains a file-based memory system (called "memdir") with files organized by type (user, feedback, project, and reference — as seen in the memory system prompt in this manual's own session). But not all memories are loaded into every conversation — that would consume too much context.

Instead, a subagent reads the descriptions of available memory files and selects up to 5 that are "clearly useful" to the current conversation. This is an LLM-as-judge pattern, not vector search or RAG. The subagent reads file descriptions and makes a judgment call about relevance.

Selected memories are injected via `<system-reminder>` tags, which appear fresh in each turn's context.

The implication: **memory file descriptions are critically important.** A description like "some notes about the project" won't match any specific query. A description like "API rate limiting configuration — sliding window, Redis-backed, per-endpoint limits" contains keywords that trigger selection when the conversation touches those topics.

The memory agent is explicitly told to prioritize "warnings, gotchas, and known issues about recently-used tools over basic usage documentation."

Here's what a memory file looks like on disk:

```markdown
---
name: api-rate-limiting
description: API rate limiting — sliding window, Redis-backed, per-endpoint, 100/min auth, 10/min anon
type: project
---

Rate limiting uses a sliding window algorithm backed by Redis.
Limits are per-endpoint, not global. Defaults: 100 req/min for
authenticated users, 10 req/min for anonymous. The /health and
/metrics endpoints are exempt (they bypass the middleware chain).
```

The frontmatter fields are what the selection agent reads. The body is what gets injected into the conversation if selected. The `description` field is the selection index — it should read like search keywords, not prose.

[source: `agent-prompt-determine-which-memory-files-to-attach.md`](https://github.com/Piebald-AI/claude-code-system-prompts/blob/main/system-prompts/agent-prompt-determine-which-memory-files-to-attach.md)

## How compaction works

As a conversation grows, it eventually approaches the context window limit. When this happens, Claude Code runs compaction — replacing older messages with a compressed summary while preserving recent messages verbatim.

Compaction triggers when two conditions are both met:
1. The message count exceeds a threshold (`preserve_recent_messages`, default 4)
2. The estimated token count exceeds a limit (`max_estimated_tokens`, default 10,000)

When compaction fires:
- Messages older than the most recent N are removed from the conversation.
- Each removed message is summarized: its role and content are recorded, with each content block truncated to 160 characters.
- The summary is wrapped in `<summary>` tags and injected as a new System message at the start of the compacted conversation.
- The continuation message tells Claude: "This session is being continued from a previous conversation that ran out of context."
- If recent messages are preserved, the continuation notes: "Recent messages are preserved verbatim."
- Claude is instructed to "Continue the conversation from where it left off without asking the user any further questions. Resume directly — do not acknowledge the summary."

Token estimation is simple: `(byte length of text) / 4 + 1` per content block. In Rust, `str::len()` returns byte length, not character count — so multi-byte UTF-8 characters count as more than one. This is a rough heuristic, not an exact token count.

[source: `compact.rs` — `should_compact()`, `compact_session()`, `summarize_messages()`, `get_compact_continuation_message()`, `estimate_message_tokens()`](https://github.com/instructkr/claw-code/blob/main/rust/crates/runtime/src/compact.rs)

## How session memory survives compaction

Separate from the file-based memdir memory, Claude Code maintains **session memory** — a structured notes file that tracks the current conversation's state. This is maintained by a background agent during the conversation, not after it.

The session notes follow a rigid structure with preserved section headers and italicized descriptions that cannot be modified. The agent updates content within these sections with "DETAILED, INFO-DENSE" entries including file paths, function names, error messages, and exact commands.

The "Current State" section is specifically flagged as "critical for continuity after compaction." This is the lifeline — when compaction replaces your older messages with a 160-character-per-block summary, the session notes preserve the detailed context that would otherwise be lost.

Updates must be made via the Edit tool, all edits in parallel in a single message. The agent is told to skip sections that don't have substantial new information rather than adding filler.

[source: `agent-prompt-session-memory-update-instructions.md`](https://github.com/Piebald-AI/claude-code-system-prompts/blob/main/system-prompts/agent-prompt-session-memory-update-instructions.md)

## How MagicDocs fit in

MagicDocs is an **internal Anthropic feature** — not currently available to public Claude Code users. We discuss it here because the agent prompt reveals a well-designed documentation philosophy, and because you can replicate it yourself (see [Chapter 5: Building MagicDocs](05-building-magicdocs.md)).

Internally, MagicDocs are architectural documentation files updated by a **Sonnet subagent** that runs after conversations, receiving the conversation transcript and the current doc contents, and using only the Edit tool to update the documentation.

The agent prompt reveals the philosophy:

**What MagicDocs document:**
- High-level architecture and system design
- Non-obvious patterns, conventions, or gotchas
- Key entry points and where to start reading code
- Important design decisions and their rationale
- Critical dependencies or integration points
- References to related files, docs, or code (like a wiki)

**What MagicDocs do NOT document:**
- Anything obvious from reading the code itself
- Exhaustive lists of files, functions, or parameters
- Step-by-step implementation details
- Low-level code mechanics
- Information already in CLAUDE.md or other project docs

The last point is critical: **MagicDocs are designed to avoid duplicating CLAUDE.md content.** MagicDocs handle "how the codebase works." CLAUDE.md handles "how you want Claude to behave."

MagicDocs are self-pruning. The agent is told to "Remove or replace outdated information rather than adding 'Previously...' or 'Updated to...' notes" and to "Clean up or DELETE sections that are no longer relevant." There is no separate consolidation step — freshness is maintained on every update.

Each doc preserves a header exactly as-is: `# MAGIC DOC: <title>`. The title serves as the document's identity and selection key.

### How docs are associated with code

The MagicDocs agent receives four template variables per invocation: `{{docPath}}`, `{{docContents}}`, `{{docTitle}}`, and `{{customInstructions}}`. The file is pre-loaded before the agent runs — the agent prompt says "The file {{docPath}} has already been read for you." This means **each doc gets its own agent run**. The orchestration layer decides which docs to update based on the conversation; the agent itself only edits the single doc it's given.

Docs are not mapped to code via file paths or `when_to_use` fields. Instead, they act as navigational overlays — each doc covers a subsystem or concern (like "Authentication" or "Build Pipeline"), and the agent uses the conversation transcript to judge whether the doc is relevant. If a conversation discussed auth changes, the auth doc gets an update run; the billing doc doesn't.

The agent cannot create new docs or split existing ones — it only has the Edit tool. If a doc grows too large, a human (or a separate creation skill) needs to split it.

[source: `agent-prompt-update-magic-docs.md`](https://github.com/Piebald-AI/claude-code-system-prompts/blob/main/system-prompts/agent-prompt-update-magic-docs.md)

## The dream cycle — memory consolidation

The file-based memory system (memdir) has its own maintenance mechanism, separate from MagicDocs. A background agent periodically runs a "dream" — a structured memory consolidation process with four phases:

1. **Orient**: Review the existing memory directory structure and index file. Examine current topic files to understand what's already stored and avoid duplication.

2. **Gather Recent Signal**: Look at daily logs and transcripts for new information. The agent is told: "Don't exhaustively read transcripts. Look only for things you already suspect matter." It uses narrow grep searches rather than reading everything.

3. **Consolidate**: Write or update memory files. Merge new information into existing files. Convert relative dates to absolute ones ("Thursday" → "2026-03-05"). Remove facts that have been contradicted by newer information.

4. **Prune and Index**: Maintain the index file (MEMORY.md) under specified character limits. Remove stale entries, shorten verbose lines, add new pointers, resolve contradictions between files.

This is exclusively for memdir memory files — the user, feedback, project, and reference type memories. It does not operate on MagicDocs, which handle their own pruning inline.

### Agent-specific memory

Beyond user-facing memories, Claude Code supports domain-specific memory for custom agents. A code-review agent can be instructed to "update your agent memory as you discover code patterns, style conventions, common issues, and architectural decisions." A test-runner agent might persist "test patterns, common failure modes, flaky tests, and testing best practices." These memories accumulate institutional knowledge across conversations — the agent learns the codebase through repeated use, similar to how MagicDocs self-correct through the development loop.

[source: `system-prompt-agent-memory-instructions.md`](https://github.com/Piebald-AI/claude-code-system-prompts/blob/main/system-prompts/system-prompt-agent-memory-instructions.md)

[source: `agent-prompt-dream-memory-consolidation.md`](https://github.com/Piebald-AI/claude-code-system-prompts/blob/main/system-prompts/agent-prompt-dream-memory-consolidation.md)

## The memory lifecycle — from correction to codification

The memory system, dream consolidation, and insights form a three-stage pipeline that moves information from ephemeral corrections to permanent configuration:

**Stage 1: Capture.** When a user corrects Claude mid-session ("no, put imports at the top of the file!"), the in-session memory system saves a `feedback` type memory. The trigger is explicit correction language — "no not that", "don't", "stop doing X." The memory is written to a file with a description and type, indexed in MEMORY.md.

**Stage 2: Consolidation.** The dream agent periodically reviews transcripts and existing memories, merging duplicates, removing contradictions, and pruning the index. It doesn't read transcripts exhaustively — it greps narrowly for things it already suspects matter. This keeps memory files tidy but doesn't evaluate whether the memories actually change behavior.

**Stage 3: Promotion.** The insights system analyzes usage data across sessions and flags instructions that appear multiple times as CLAUDE.md candidates. If a user told Claude the same thing in 2+ sessions, the system suggests codifying it permanently. This is the migration path from Memory (sometimes relevant, selectively loaded) to CLAUDE.md (always present, shapes every session).

[source: `agent-prompt-dream-memory-consolidation.md`](https://github.com/Piebald-AI/claude-code-system-prompts/blob/main/system-prompts/agent-prompt-dream-memory-consolidation.md), [`system-prompt-insights-suggestions.md`](https://github.com/Piebald-AI/claude-code-system-prompts/blob/main/system-prompts/system-prompt-insights-suggestions.md)

### What's missing: verification

This pipeline captures and promotes instructions but never verifies they work. A feedback memory might have a vague description (never selected), or a CLAUDE.md entry might be too far from the point of action to reliably change behavior. MagicDocs self-correct through the development loop — agents that struggle with a subsystem update the doc, and the next agent benefits. But Memory and CLAUDE.md have no equivalent feedback loop. Bad content persists silently.

The insights system detects *repeated instructions* as a lagging signal that context engineering isn't working, but there's no leading test — no way to verify upfront that a new CLAUDE.md entry or memory file will actually prevent the wrong default behavior in a fresh session.

This is an architectural asymmetry, not a minor gap. MagicDocs self-correct through the development loop — agents that struggle with a subsystem update the doc, and the next agent benefits. Skills are testable: you can run a pressure scenario without the skill (RED), write the skill (GREEN), and verify compliance (REFACTOR). But CLAUDE.md and Memory have no equivalent feedback mechanism. Bad content persists silently until a human notices — or until the insights system flags repeated corrections, which is a lagging indicator that the content already failed.

## Configuration and permissions

### Three-tier configuration

Claude Code loads settings from three locations, merged in order of increasing specificity:

1. **User config**: `~/.claude/settings.json` — your global preferences (lowest priority)
2. **Project config**: `.claude/settings.json` — shared project settings, typically committed to git
3. **Local config**: `.claude/settings.local.json` — personal overrides for this project (highest priority)

The loader discovers all three files and performs a deep merge of JSON objects. If the same key appears in multiple files, the higher-specificity file wins. For nested objects, the merge is recursive — so project-level `env` variables are merged with user-level ones, not replaced.

The entire merged configuration is rendered into the system prompt as JSON, in section 10. This means Claude sees every field from your settings files — permissions, hooks, environment variables, allowed tools, and any custom configuration. The prompt also lists which config files were loaded and from where:

```
# Runtime config
- Loaded User: /Users/you/.claude/settings.json
- Loaded Project: .claude/settings.json

{ "permissions": { ... }, "hooks": { ... }, ... }
```

[source: `config.rs` — `ConfigLoader::discover()` and `deep_merge_objects()`](https://github.com/instructkr/claw-code/blob/main/rust/crates/runtime/src/config.rs), [`prompt.rs` — `render_config_section()` rendering full JSON](https://github.com/instructkr/claw-code/blob/main/rust/crates/runtime/src/prompt.rs)

### Permission model

Claude Code uses three permission modes with per-tool overrides:

- **Allow**: Tool execution approved automatically
- **Deny**: Tool execution blocked
- **Prompt**: Interactive user decision required

A `PermissionPolicy` maintains a default mode and a map of tool-specific overrides. When a tool is called, the policy checks for a tool-specific mode first, then falls back to the default. If the mode is `Prompt`, a `PermissionPrompter` is invoked to ask the user.

This explains why subagents can read files without asking you (they operate under `Allow` for read-only tools) while your main session still prompts for bash commands (default `Prompt` mode with no override for `Bash`).

[source: `permissions.rs` — `PermissionPolicy`, `PermissionMode`, `PermissionOutcome`](https://github.com/instructkr/claw-code/blob/main/rust/crates/runtime/src/permissions.rs)

### Hooks

Hooks are shell commands that execute at specific lifecycle events. They're configured in settings.json under the `hooks` key, with events including:

- **PreToolUse** — runs before a tool executes (can block or modify the call)
- **PostToolUse** — runs after a tool executes successfully
- **PostToolUseFailure** — runs after a tool execution fails
- **Stop** — runs when a session ends
- **PreCompact** / **PostCompact** — runs around compaction
- **UserPromptSubmit** — runs when the user submits a message
- **SessionStart** — runs when a session begins
- **Notification** — runs when the system generates a notification
- **PermissionRequest** — runs when a tool requests permission

Each hook entry has a `matcher` (which tools it applies to, e.g., `"Bash"` or `"Write|Edit"`), a `hooks` array containing objects with a `type` (`command`, `prompt`, or `agent`) and the corresponding command or prompt to execute.

Hook output can return JSON with fields like `systemMessage` (user-facing text), `continue` (allow/block execution), and `hookSpecificOutput` (structured data passed back to the tool context).

[source: `system-prompt-hooks-configuration.md`](https://github.com/Piebald-AI/claude-code-system-prompts/blob/main/system-prompts/system-prompt-hooks-configuration.md)

## The insights feedback loop

Claude Code doesn't just execute tasks — it analyzes your usage patterns across sessions and generates suggestions for improving your workflow. This is the feedback loop that closes the circle between "you keep telling Claude things" and "the system suggests you codify them."

The insights system collects data across three dimensions:

- **Goal categories**: What you explicitly asked for ("can you...", "please...", "I need...")
- **Satisfaction signals**: Happy, satisfied, likely satisfied, dissatisfied, or frustrated — based on explicit language cues
- **Friction points**: Misunderstood requests, wrong approaches, buggy code, rejected actions, over-engineered solutions

From this data, the system generates three types of suggestions:

1. **CLAUDE.md additions**: Specific lines to add to your CLAUDE.md. The system explicitly prioritizes "instructions that appear MULTIPLE TIMES in the user data. If user told Claude the same thing in 2+ sessions (e.g., 'always run tests', 'use TypeScript'), that's a PRIME candidate — they shouldn't have to repeat themselves."

2. **Features to try**: Recommendations from a reference list including MCP servers, custom skills, hooks, headless mode, and task agents — personalized based on your actual sessions.

3. **Usage patterns**: Specific prompts to copy and try, based on patterns the system noticed in your work.

This means Claude Code is actively watching for repeated instructions and suggesting you move them into permanent configuration. If you find yourself saying the same thing every session, the insights system should eventually suggest codifying it.

[source: `system-prompt-insights-suggestions.md`](https://github.com/Piebald-AI/claude-code-system-prompts/blob/main/system-prompts/system-prompt-insights-suggestions.md)

[source: `system-prompt-insights-session-facets-extraction.md`](https://github.com/Piebald-AI/claude-code-system-prompts/blob/main/system-prompts/system-prompt-insights-session-facets-extraction.md)

## Next

[Chapter 3: Subagent Architecture →](03-subagent-architecture.md)

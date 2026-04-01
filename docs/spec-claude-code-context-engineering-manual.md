# Design Spec: Claude Code Context Engineering Manual

**Date**: 2026-04-01
**Status**: Draft

## Overview

A five-part manual explaining how Claude Code manages context internally, and how to build automated documentation systems that mirror Anthropic's own internal tooling (MagicDocs).

## Audiences

1. **Context engineering learners**: People who use Claude Code and want to understand why it behaves the way it does — why it sometimes "forgets" instructions, why skills feel more reliable than CLAUDE.md, how compaction affects long sessions.
2. **MagicDocs builders**: People who want to build a MagicDocs-like system — automated project documentation that updates itself after conversations, progressing from manual → skill → hook automation.

## Sources

All architectural claims cite specific source files from two publicly available open-source repositories:

- [instructkr/claw-code](https://github.com/instructkr/claw-code) — A Python and Rust reimplementation of Claude Code's architecture by Sigrid Jin, containing a Rust port with working system prompt construction, session management, compaction, and permission code.
- [Piebald-AI/claude-code-system-prompts](https://github.com/Piebald-AI/claude-code-system-prompts) — A catalog of 250 extracted Claude Code system prompts, agent prompts, skill definitions, and tool descriptions.

The authors of this manual are not responsible for and had no role in the exposure of Claude Code's source. Citations link directly to source files so readers can verify claims independently.

## File Structure

```
docs/
  01-introduction.md
  02-context-engineering.md
  03-subagent-architecture.md
  04-what-to-put-where.md
  05-building-magicdocs.md
```

---

## `01-introduction.md`

### Purpose
Frame the manual — what it is, who it's for, where the information comes from.

### Contents
- **What this is**: A guide to how Claude Code manages context internally — how it decides what to load, where your instructions land in the prompt, why some customization mechanisms work better than others, and how to build automated documentation systems that mirror Anthropic's own internal tooling.
- **Who it's for**: The two audiences described above.
- **Sources**: The two repositories above, with the framing note about having no role in the exposure.
- **How citations work**: Every architectural claim links to the specific source file. Format: `[source: filename](URL)`. When we say "the system does X," there's a link to the code or prompt that shows it.

---

## `02-context-engineering.md`

### Purpose
The core mental model — how context flows through Claude Code from startup to mid-conversation to compaction. Both audiences need this foundation.

### Contents

1. **The prompt is a pipeline, not a file**
   - Claude Code assembles the prompt dynamically from multiple sources, in a specific order, with a boundary marker separating static from dynamic content.
   - Cite: [`prompt.rs` `build()` method and `SYSTEM_PROMPT_DYNAMIC_BOUNDARY`](https://github.com/instructkr/claw-code/blob/main/rust/crates/runtime/src/prompt.rs)

2. **System prompt construction — the 10 sections**
   - Exact order: intro → output style → system rules → doing tasks → actions → DYNAMIC BOUNDARY → environment → project context → CLAUDE.md files → runtime config.
   - Everything above the boundary is Anthropic's behavioral instructions; everything below is project-specific context. CLAUDE.md lands below the boundary.
   - Cite: [`prompt.rs` `build()`, `render_instruction_files()`, `discover_instruction_files()`](https://github.com/instructkr/claw-code/blob/main/rust/crates/runtime/src/prompt.rs)

3. **How CLAUDE.md files are loaded**
   - Walks the ancestor directory chain from filesystem root to cwd.
   - Collects `CLAUDE.md`, `CLAUDE.local.md`, `.claude/CLAUDE.md` at each level.
   - Concatenated verbatim — no processing, no summarization, no relevance filtering.
   - Cite: [`prompt.rs` `discover_instruction_files()` and test `discovers_instruction_files_from_ancestor_chain`](https://github.com/instructkr/claw-code/blob/main/rust/crates/runtime/src/prompt.rs)

4. **How skills are loaded**
   - Not in the system prompt at startup — deferred loading.
   - Invoked via `SkillTool` mid-conversation; content arrives as a tool result.
   - Selection based on `when_to_use` frontmatter field, which is flagged as "critical for auto-invocation."
   - Cite: [`system-prompt-skillify-current-session.md`](https://github.com/Piebald-AI/claude-code-system-prompts/blob/main/system-prompts/system-prompt-skillify-current-session.md) for `when_to_use` criticality

5. **How memory is selected and injected**
   - A Sonnet subagent reads memory file descriptions and picks up to 5 relevant ones.
   - LLM-as-judge pattern, not vector search / RAG.
   - Injected via system-reminder tags.
   - Cite: [`agent-prompt-determine-which-memory-files-to-attach.md`](https://github.com/Piebald-AI/claude-code-system-prompts/blob/main/system-prompts/agent-prompt-determine-which-memory-files-to-attach.md)

6. **How compaction works**
   - Triggered when message count exceeds threshold AND token estimate exceeds limit.
   - Older messages summarized (each block truncated to 160 chars); recent N messages preserved verbatim.
   - Summary injected as a System message: "This session is being continued from a previous conversation..."
   - Cite: [`compact.rs` — `should_compact()`, `compact_session()`, `summarize_messages()`, `get_compact_continuation_message()`](https://github.com/instructkr/claw-code/blob/main/rust/crates/runtime/src/compact.rs)

7. **How session memory survives compaction**
   - Separate from memdir memory — a structured notes file maintained during conversation.
   - "Current State" section flagged as "critical for continuity after compaction."
   - Cite: [`agent-prompt-session-memory-update-instructions.md`](https://github.com/Piebald-AI/claude-code-system-prompts/blob/main/system-prompts/agent-prompt-session-memory-update-instructions.md)

8. **How MagicDocs fit in**
   - A post-conversation Sonnet subagent with access to only the Edit tool.
   - Receives current doc contents and conversation; updates docs in-place.
   - Philosophy: terse, high-signal, architecture and gotchas only. Explicitly complementary to CLAUDE.md.
   - Self-pruning: removes outdated info and deletes irrelevant sections as part of every update.
   - Cite: [`agent-prompt-update-magic-docs.md`](https://github.com/Piebald-AI/claude-code-system-prompts/blob/main/system-prompts/agent-prompt-update-magic-docs.md)

9. **The dream cycle — memory consolidation**
   - Periodic background agent for the memdir memory system (NOT MagicDocs).
   - 4 phases: Orient, Gather Recent Signal, Consolidate, Prune and Index.
   - Merges new info into existing files, removes contradictions, converts relative dates to absolute.
   - "Don't exhaustively read transcripts. Look only for things you already suspect matter."
   - Cite: [`agent-prompt-dream-memory-consolidation.md`](https://github.com/Piebald-AI/claude-code-system-prompts/blob/main/system-prompts/agent-prompt-dream-memory-consolidation.md)

10. **Configuration and permissions**
    - Three-tier config merge: user (`~/.claude/settings.json`) → project (`.claude/settings.json`) → local (`.claude/settings.local.json`). Higher-specificity files override lower.
    - Three permission modes: Allow, Deny, Prompt — with per-tool overrides.
    - Hooks: PreToolUse and PostToolUse arrays in settings.json.
    - Cite: [`config.rs`](https://github.com/instructkr/claw-code/blob/main/rust/crates/runtime/src/config.rs) for merge logic, [`permissions.rs`](https://github.com/instructkr/claw-code/blob/main/rust/crates/runtime/src/permissions.rs) for permission model

11. **The insights feedback loop**
    - Claude Code analyzes usage patterns across sessions: goals, satisfaction signals, friction points.
    - Generates CLAUDE.md addition suggestions, prioritizing "instructions that appear MULTIPLE TIMES in the user data" — if you keep repeating yourself, the system suggests you codify it.
    - Also suggests features to try and usage patterns to adopt.
    - Cite: [`system-prompt-insights-suggestions.md`](https://github.com/Piebald-AI/claude-code-system-prompts/blob/main/system-prompts/system-prompt-insights-suggestions.md), [`system-prompt-insights-session-facets-extraction.md`](https://github.com/Piebald-AI/claude-code-system-prompts/blob/main/system-prompts/system-prompt-insights-session-facets-extraction.md)

---

## `03-subagent-architecture.md`

### Purpose
How Claude Code delegates work to subagents — different models, tool restrictions, context construction, and result compression. Important foundation before deciding what to put where.

### Contents

1. **What subagents are and why they exist**
   - Claude Code spawns separate agent processes for complex or parallelizable work.
   - Each subagent gets its own context window, protecting the main conversation from context bloat.

2. **Subagent types — model, tools, purpose**
   - **General-purpose**: Runs on Opus (full model). Most tools available. For complex multi-step tasks. Told to "execute tasks fully" and report back.
   - **Explore**: Runs on **Haiku** (cheapest/fastest). Read-only tools only — Glob, Grep, Read, Bash. Explicitly cannot Edit, Write, or spawn sub-subagents. "Exclusively to search and analyze existing code." Three thoroughness levels: quick, medium, very thorough.
   - **Plan**: Research and design, no implementation tools.
   - Other specialized types: claude-code-guide, verification, statusline-setup.
   - Cite: [`agent-prompt-general-purpose.md`](https://github.com/Piebald-AI/claude-code-system-prompts/blob/main/system-prompts/agent-prompt-general-purpose.md), [`agent-prompt-explore.md`](https://github.com/Piebald-AI/claude-code-system-prompts/blob/main/system-prompts/agent-prompt-explore.md)

3. **How subagent context is constructed — fresh start**
   - Each subagent starts with zero conversation history. No access to prior messages.
   - The main agent must include all relevant context in the prompt: goals, reasoning, prior attempts, file paths, line numbers.
   - "Fresh subagents starting with zero context require even more thorough briefing than ongoing conversations."
   - Cite: [`system-prompt-writing-subagent-prompts.md`](https://github.com/Piebald-AI/claude-code-system-prompts/blob/main/system-prompts/system-prompt-writing-subagent-prompts.md)

4. **How to write good subagent prompts**
   - Include goals and reasoning behind the task.
   - Include what you've already attempted or discovered.
   - Provide concrete details (file paths, line numbers) rather than vague directives.
   - Specify length constraints when brevity matters.
   - For investigations, pose the question rather than prescribing steps.
   - "Never delegate understanding" — don't write "based on your findings, fix the bug."
   - Cite: [`system-prompt-writing-subagent-prompts.md`](https://github.com/Piebald-AI/claude-code-system-prompts/blob/main/system-prompts/system-prompt-writing-subagent-prompts.md)

5. **How results come back — summary compression**
   - Subagent results are summarized in 3-5 word present tense format: "Reading runAgent.ts", "Fixing null check in validate.ts".
   - Deduplicated against `PREVIOUS_AGENT_SUMMARY` to avoid repetition.
   - This prevents subagent output from consuming the main context window.
   - Cite: [`system-prompt-agent-summary-generation.md`](https://github.com/Piebald-AI/claude-code-system-prompts/blob/main/system-prompts/system-prompt-agent-summary-generation.md)

6. **The coordinator pattern**
   - After delegation, the coordinator "knows nothing about the findings yet."
   - If the user asks follow-up questions while waiting, the coordinator acknowledges without fabricating: "Still waiting on the audit."
   - When results arrive, the coordinator synthesizes findings into concise summaries.
   - For independent review, `subagent_type` ensures the subagent works independently without inheriting the coordinator's prior analysis.
   - Cite: [`system-prompt-subagent-delegation-examples.md`](https://github.com/Piebald-AI/claude-code-system-prompts/blob/main/system-prompts/system-prompt-subagent-delegation-examples.md)

7. **Practical implications**
   - Why vague prompts to subagents get bad results (zero context, need thorough briefing).
   - Why Explore agents are fast but can't change anything (Haiku, read-only).
   - When to parallelize — independent tasks with no shared state.
   - The 16-iteration limit per turn — why Claude sometimes stops mid-task.
   - Cite: [`conversation.rs` `max_iterations: 16`](https://github.com/instructkr/claw-code/blob/main/rust/crates/runtime/src/conversation.rs)

---

## `04-what-to-put-where.md`

### Purpose
Practical guide for deciding which customization mechanism to use. The "so what do I actually do" doc.

### Contents

1. **The selection problem**
   - Five mechanisms that all feel like "tell Claude what to do" but have fundamentally different injection points, survival characteristics, and effectiveness profiles.
   - Summary table:

   | Mechanism | When injected | Where in context | Survives compaction? | Relevance-filtered? | You control content? |
   |---|---|---|---|---|---|
   | CLAUDE.md | Session start | System prompt, section 9 | Yes (always present) | No (all or nothing) | Yes (verbatim) |
   | Skills | On demand, mid-conversation | Tool result | No (but doesn't need to) | Yes (`when_to_use`) | Yes (you write them) |
   | Memory | Session start, selective | System-reminder tags | Varies | Yes (LLM picks top 5) | Yes (but system-managed) |
   | Hooks | Pre/post tool use | Outside LLM context | N/A (mechanical) | N/A | Yes (shell commands) |
   | MagicDocs | Post-conversation | Updated files on disk | N/A (persisted to files) | N/A (auto-generated) | No |

   - Cite: [`prompt.rs`](https://github.com/instructkr/claw-code/blob/main/rust/crates/runtime/src/prompt.rs) for CLAUDE.md placement, [`compact.rs`](https://github.com/instructkr/claw-code/blob/main/rust/crates/runtime/src/compact.rs) for compaction behavior

2. **CLAUDE.md: environmental context**
   - Good at: environmental facts that prevent wrong assumptions (package manager, deploy target, database choice), terminology grounding, invariants, pointers to other mechanisms.
   - Bad at: workflows, conditional logic, long examples, behavioral rules you want reliably enforced, conflicting with system prompt sections above it.
   - Why: static, always present, unfiltered, positioned after Anthropic's own behavioral instructions. Sets priors, not actions. Every token consumed on every API call. No verification loop — there's no mechanism to check whether a CLAUDE.md instruction actually changed behavior.
   - **Bad example** (workflow in CLAUDE.md):
     ```markdown
     # CLAUDE.md
     When fixing a bug, always reproduce it first, then write a failing test,
     then fix the code, then verify the test passes.
     ```
     *Why it's bad: By the time Claude is fixing a bug, this instruction is thousands of tokens away. It reads it at session start but doesn't reliably follow multi-step procedures from the system prompt.*
   - **Good example** (invariant in CLAUDE.md):
     ```markdown
     # CLAUDE.md
     This project uses pnpm, not npm or yarn. All package commands use pnpm.
     ```
     *Why it works: Claude would otherwise guess npm. This prevents a wrong assumption before any reasoning happens.*
   - Cite: [`prompt.rs` `render_instruction_files()`](https://github.com/instructkr/claw-code/blob/main/rust/crates/runtime/src/prompt.rs) showing verbatim concatenation

3. **Skills: direct orders at the right moment**
   - Why they outperform CLAUDE.md: recency (injected at point of action), specificity (targeted to current task), authority (tool results carry strong instruction-following weight).
   - What belongs: workflows, checklists, verification procedures, structured output formats, "when X happens, do Y" logic.
   - **Bad example** (static fact in a skill):
     ```markdown
     ---
     when_to_use: When working in this project
     ---
     This project uses PostgreSQL 16 and runs on Node 22.
     ```
     *Why it's bad: Consumes a skill invocation for information that should be a CLAUDE.md one-liner. Skills are for procedures, not facts.*
   - **Good example** (procedure in a skill):
     ```markdown
     ---
     when_to_use: When committing code or the user asks to commit
     ---
     Before committing:
     1. Run `pnpm test` and confirm all tests pass
     2. Run `pnpm lint` and fix any issues
     3. Draft a commit message following conventional commits
     4. Show the user the message and wait for approval
     ```
     *Why it works: Arrives at the exact moment Claude is about to commit, with step-by-step instructions it follows reliably.*
   - Cite: [`system-prompt-skillify-current-session.md`](https://github.com/Piebald-AI/claude-code-system-prompts/blob/main/system-prompts/system-prompt-skillify-current-session.md) for skill structure

4. **Memory: persistent cross-conversation context**
   - Selection is LLM-based on descriptions — vague descriptions mean the memory never gets attached.
   - Memory types: user, feedback, project, reference.
   - Dream consolidation means memories are actively maintained, not just accumulating.
   - **Bad example** (vague description):
     ```markdown
     ---
     description: Some notes about the project
     ---
     The API uses rate limiting with a sliding window...
     ```
     *Why it's bad: The description "some notes about the project" won't match any specific query. The memory selection agent will never pick this.*
   - **Good example** (specific description):
     ```markdown
     ---
     description: API rate limiting configuration — sliding window, Redis-backed, per-endpoint limits
     ---
     The API uses rate limiting with a sliding window...
     ```
     *Why it works: When the user asks about rate limits, APIs, or Redis, the keywords in the description trigger selection.*
   - Cite: [`agent-prompt-determine-which-memory-files-to-attach.md`](https://github.com/Piebald-AI/claude-code-system-prompts/blob/main/system-prompts/agent-prompt-determine-which-memory-files-to-attach.md) for selection logic

5. **Hooks: automated guardrails**
   - PreToolUse and PostToolUse lifecycle events.
   - Good for: mechanical enforcement — formatting, type checking, convention enforcement.
   - Not for: behavioral instructions (skills), project context (CLAUDE.md), persistent knowledge (memory).
   - **Bad example** (behavioral instruction as hook):
     ```json
     {
       "hooks": {
         "PreToolUse": [{
           "matcher": "Bash",
           "hooks": [{
             "type": "command",
             "command": "echo '{\"systemMessage\": \"Remember to write tests first\"}'"
           }]
         }]
       }
     }
     ```
     *Why it's bad: Hook output is treated as system feedback, not behavioral instruction. Claude sees the systemMessage but it doesn't reliably change its approach. Use a skill for workflow guidance.*
   - **Good example** (mechanical enforcement as hook):
     ```json
     {
       "hooks": {
         "PostToolUse": [{
           "matcher": "Write|Edit",
           "hooks": [{
             "type": "command",
             "command": "cd $PROJECT_DIR && pnpm lint --fix $FILEPATH 2>&1 | tail -5"
           }]
         }]
       }
     }
     ```
     *Why it works: After every file write or edit, the linter runs automatically. No reliance on Claude remembering to do it — it happens mechanically.*
   - Cite: [`system-prompt-hooks-configuration.md`](https://github.com/Piebald-AI/claude-code-system-prompts/blob/main/system-prompts/system-prompt-hooks-configuration.md) for hook schema, [`config.rs`](https://github.com/instructkr/claw-code/blob/main/rust/crates/runtime/src/config.rs) for config loading

6. **MagicDocs: the system's own understanding**
   - Explicitly complementary to CLAUDE.md — MagicDocs covers architecture and gotchas, CLAUDE.md covers preferences and constraints.
   - You don't write MagicDocs; the system generates them. But you can build your own version (→ next chapter).
   - **Bad example** (CLAUDE.md doing MagicDocs' job):
     ```markdown
     # CLAUDE.md
     The auth middleware is in src/middleware/auth.ts. It talks to Redis
     for session storage. The session TTL is 24h. The middleware chain
     runs in order: cors → rateLimit → auth → validate → handler.
     Sessions are stored with prefix "sess:" in Redis key space 2.
     ```
     *Why it's bad: This is architectural documentation that will go stale. It belongs in a MagicDoc that gets updated automatically, not in a static CLAUDE.md that you have to maintain by hand.*
   - **Good example** (letting MagicDocs handle architecture, CLAUDE.md handles constraints):
     ```markdown
     # CLAUDE.md
     Never modify the auth middleware session TTL without checking with the security team.
     ```
     *Why it works: CLAUDE.md states the constraint (an invariant). The architectural details about how auth works are left to MagicDocs to discover and maintain.*
   - Cite: [`agent-prompt-update-magic-docs.md`](https://github.com/Piebald-AI/claude-code-system-prompts/blob/main/system-prompts/agent-prompt-update-magic-docs.md) for the philosophy

7. **Descriptions are selection indices — the pattern that applies everywhere**
   - The entire architecture uses a two-stage pattern: cheap filter on a description field → expensive load of full content.
   - This applies to: skills (`when_to_use`), memory (`description` frontmatter), deferred tools (name + description in `ToolSearch`), MagicDocs (document title).
   - If your skill isn't auto-triggering, your memory isn't getting attached, or your tool isn't loading — the first thing to check is the description, not the content.
   - Write descriptions like trigger conditions or search keywords, not prose documentation.

   | Mechanism | Selection field | Who reads it | Bad description | Good description |
   |---|---|---|---|---|
   | Skill | `when_to_use` | Skill matching | "Use when helpful" | "Use when committing code or the user asks to commit" |
   | Memory | `description` | Memory agent (Sonnet) | "Some project notes" | "API rate limiting — sliding window, Redis, per-endpoint" |
   | Deferred tool | Tool name + description | `ToolSearchTool` | "A tool" | "Browser automation for Chrome tabs" |
   | MagicDoc | Document title | MagicDocs agent | "Notes" | "Authentication Middleware Architecture" |

8. **Decision flowchart — sequential filter**
   - Ask these questions in order. Stop at the first "yes."
     1. "Does this need to happen mechanically, regardless of what Claude is doing?" → **Hook** *(e.g., run the linter after every file edit, block commits without tests)*
     2. "Would Claude make a wrong assumption on its very first action without this?" → **CLAUDE.md** *(e.g., "this project uses pnpm not npm", "never modify /src/generated/")*
     3. "Is this a step-by-step procedure for a specific kind of task?" → **Skill** *(e.g., "when committing: run tests, check coverage, draft message, commit")*
     4. "Is this something I learned that should carry over to future conversations?" → **Memory** *(e.g., "user prefers bundled PRs", "deploy target is Fly.io")*
     5. "Is this architectural knowledge about how the codebase works?" → **MagicDocs** *(e.g., "auth middleware talks to Redis for session storage")*
   - The ordering matters: hooks first (bypass Claude entirely), CLAUDE.md second (earliest context), skills third (most effective behavioral mechanism), memory fourth (cross-session persistence), MagicDocs last (codebase documentation).

9. **A note on behavioral rules in CLAUDE.md**
   - The tree correctly routes always-relevant priors to CLAUDE.md, but behavioral rules there often need a second enforcement layer.
   - Environmental facts (pnpm not npm) work well in CLAUDE.md — wrong assumptions surface as errors. Behavioral rules (test before commit) require Claude to remember to act, which CLAUDE.md is bad at.
   - Practitioner experience: behavioral rules in CLAUDE.md often need a code-review skill with coding standards attached, where a subagent checks compliance at point of action.
   - Framed as practitioner experience, not architectural claim.

---

## `05-building-magicdocs.md`

### Purpose
Progressive guide from manual documentation → skill-based automation → hook-based automation.

### Contents

1. **What we're building and why**
   - MagicDocs internally is a Sonnet subagent that runs post-conversation, reads existing docs, and updates them using only the Edit tool.
   - We can't hook into that exact lifecycle event, but we can replicate the behavior with increasing automation.
   - The progression: manual → skill → hooks.
   - Cite: [`agent-prompt-update-magic-docs.md`](https://github.com/Piebald-AI/claude-code-system-prompts/blob/main/system-prompts/agent-prompt-update-magic-docs.md) for the reference implementation

2. **Understand the MagicDocs philosophy**
   - What TO document: architecture, non-obvious patterns, entry points, design rationale, integration points, cross-references.
   - What NOT to document: anything obvious from code, exhaustive file/function lists, step-by-step implementation, low-level mechanics, anything already in CLAUDE.md.
   - Key rule: "Keep the document CURRENT with the latest state — this is NOT a changelog." Update in-place, remove outdated info, don't append historical notes.
   - Header convention: `# MAGIC DOC: <title>` preserved exactly.
   - Cite: CRITICAL RULES and DOCUMENTATION PHILOSOPHY sections from [`agent-prompt-update-magic-docs.md`](https://github.com/Piebald-AI/claude-code-system-prompts/blob/main/system-prompts/agent-prompt-update-magic-docs.md)

3. **Create your first Magic Doc manually**
   - Walk through creating a doc (e.g., `docs/magic/architecture.md`) for a real project.
   - Provide a template with the header convention and suggested sections.
   - Show what a good Magic Doc looks like vs. a bad one (too detailed / too vague).
   - Guidance on scoping: one doc per major subsystem or concern, not one giant doc.

4. **Build an update skill (`/update-docs`)**
   - Full skill file with frontmatter (`when_to_use`, `allowed-tools`, etc.).
   - Skill prompt maps back to the real MagicDocs agent prompt — each instruction explained.
   - The skill:
     - Reads existing Magic Doc files
     - Looks at recent git diff or conversation context
     - Updates docs following the MagicDocs philosophy
     - Shows the user what changed
   - How to invoke: `/update-docs` after a significant session.
   - Cite: real agent prompt as the reference for the skill's instructions

5. **Build a creation skill (`/create-doc <title>`)**
   - Separate skill for bootstrapping new Magic Docs.
   - Analyzes a subsystem or area of the codebase and generates the initial doc.
   - Uses the same philosophy — terse, architectural, entry-points-focused.

6. **Automate with hooks**
   - Move from manual `/update-docs` invocation to automatic execution.
   - Use a `Stop` hook event to trigger a headless `claude -p` call when a session ends, running the same update logic non-interactively.
   - Show the full `settings.json` hook configuration with `matcher`, `hooks` array, and `type: "command"` fields.
   - Trade-offs: cost (every session triggers a Sonnet call), noise (not every conversation produces doc-worthy learnings), gating strategies (e.g., only trigger after sessions longer than N turns, or only when certain files were modified).
   - Cite: [`config.rs`](https://github.com/instructkr/claw-code/blob/main/rust/crates/runtime/src/config.rs) for hook structure, [`system-prompt-insights-suggestions.md`](https://github.com/Piebald-AI/claude-code-system-prompts/blob/main/system-prompts/system-prompt-insights-suggestions.md) for the pattern of post-session analysis

7. **Putting it all together**
   - Summary of what you've built: a documentation system that mirrors Anthropic's internal MagicDocs pipeline using user-accessible primitives.
   - Flow diagram: conversation → hook triggers → headless Claude updates docs → next session loads updated docs via CLAUDE.md or memory.
   - Maintenance advice: review Magic Docs periodically, keep them terse, delete docs for subsystems that no longer exist.

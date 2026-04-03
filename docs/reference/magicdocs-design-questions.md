# MagicDocs System — Design Questions

Working spec tracking design decisions for building a magicdocs system that can be installed in any repository via a reusable skill.

## Goal

Build a skill (using the `writing-skills` skill) that bootstraps a MagicDocs system in any repo. MagicDocs are terse, auto-maintained architectural documentation files that capture non-obvious patterns, gotchas, design rationale, and entry points — things that would surprise an agent reading the codebase for the first time. They complement CLAUDE.md (which holds behavioral constraints) by holding architectural knowledge that would otherwise go stale.

The deliverable is a **modular set of skills** (not a monolithic one) that gets installed into a target repo. The bootstrap skill is the installer.

## How Anthropic's Internal MagicDocs Works

Anthropic has an internal MagicDocs feature (not available to public Claude Code users). Key details from the extracted `agent-prompt-update-magic-docs.md` and source code analysis:

- **Model**: Sonnet subagent, cost-optimized
- **Tools**: Edit only — can't Read, create files, or run commands. Doc contents are pre-loaded via template variables (`{{docPath}}`, `{{docContents}}`, `{{docTitle}}`, `{{customInstructions}}`)
- **Trigger**: `postSamplingHook` after model responses that involved tool calls — NOT post-conversation as Chapter 5 of our manual assumed. This means updates happen incrementally during the session, not as a batch at the end.
- **Timing**: Fires during idle lulls when the user hasn't sent a new message
- **Scope**: Each doc gets its own agent run. The orchestration layer decides which docs are relevant to the conversation; the agent only edits the single doc it's given.
- **Discovery**: Regex scan `^#\s*MAGIC\s+DOC:\s*(.+)$/im` finds docs by header convention
- **Cannot create new docs** — only edits existing ones. A separate process handles creation.
- **Activation**: Fully gated to internal builds. Creating `# MAGIC DOC:` files in a public repo does nothing. No settings key, env var, or CLI flag to enable it.

### MagicDocs Philosophy (from the extracted agent prompt)

**What TO document**: High-level architecture, non-obvious patterns/gotchas, key entry points, design decision rationale, critical dependencies, cross-references to related code.

**What NOT to document**: Anything obvious from reading code, exhaustive file/function lists, step-by-step implementation details, low-level mechanics, anything already in CLAUDE.md.

**Update rules**: Current state only — NOT a changelog. Update in-place, remove outdated info, delete irrelevant sections. "BE TERSE. High signal only. No filler words."

**Header convention**: `# MAGIC DOC: <title>` preserved exactly.

## Design Questions

### Decided

- [x] **#3 What context does the subagent get?**
  - **Anthropic**: Full conversation transcript + doc contents via template variables.
  - **Us**: Main agent formulates a focused insight in a standard format: "An agent working on X would assume Y, but actually Z. The relevant code is in [file paths]." Minimal information — no transcript dump. The main agent already did the hard work of discovering the insight; the subagent's job is to integrate it into the right doc, not re-derive it.
  - **Rationale**: We don't have access to the conversation transcript from outside the session. Even if we did, passing 95%+ of a context window to a subagent would be slow and expensive with no guarantee the subagent wouldn't hit the same context limits. Minimal, focused insights are cheaper, faster, and sufficient — the main agent is the researcher, the subagent is the editor.
  - **Upgrade path**: If subagent doc updates turn out to be low quality because they lack context, we can add a conversation summary. Start minimal.

- [x] **#1 When does it trigger?**
  - **Anthropic**: `postSamplingHook` after tool-call-bearing model responses.
  - **Us**: Combination of three mechanisms for maximum coverage:
    - **(a) Main agent judgment + `/classify-info` classification** (primary): During normal work, the main agent encounters something non-obvious. It runs the `/classify-info` skill's decision tree. If classified as MagicDocs (describes architecture, not prescribes behavior), the agent dispatches the insight to the magicdocs subagent.
    - **(b) Explicit user invocation** (manual override): User says "remember this" or invokes an update skill directly. Highest signal.
    - **(c) Code-review subagent** (bonus): The review agent flags non-obvious patterns as a side effect of its normal review work. Only fires during reviews but catches things the main agent might miss.
  - **Reliability caveat**: The primary automatic channel (a) depends on the main agent noticing something is doc-worthy — a behavioral instruction, which are known to be unreliable. The `/classify-info` skill's 100% classification accuracy doesn't help if the main agent never invokes it. The Stop hook safety net (see below) partially mitigates this by sweeping for undocumented changes at session end.

- [x] **#8 Which docs get updated?**
  - **Anthropic**: Orchestration layer (with full conversation context) judges relevance; spawns one agent per relevant doc.
  - **Us**: The **main agent specifies the target doc** as part of the dispatch. The main agent just encountered the insight — it knows which subsystem it relates to and is better positioned to judge relevance than a subagent with only a terse insight and a list of filenames. The dispatch message includes the doc path (e.g., "update docs/magic/auth.md"). If the main agent doesn't know which doc is relevant, it can say "relates to auth" and the subagent resolves it to a specific file.
  - **Rationale**: Reviewer feedback — pushing doc-selection to a minimally-contexted subagent is asking it to make a hard judgment with insufficient information. The main agent has full context and can make this call cheaply. If no existing doc matches, the subagent reports "no doc covers this, suggest creating one."

- [x] **#12/13 Agent persistence and cardinality**
  - **Anthropic**: Fresh agent per doc per update. No persistence.
  - **Us**: **Fresh-per-insight as the primary architecture.** Each dispatch spawns a fresh Sonnet subagent that reads the current doc, applies the edit, and exits. No persistent state, no stale context, no compaction issues. Runs in background (`run_in_background: true`) so it doesn't block the main agent.
  - **Agent Teams as optional enhancement**: For teams with multiple concurrent sessions, Agent Teams provides coordination via shared task lists and file-locking. The bootstrap skill can optionally enable this (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`). When enabled, insights are queued as tasks and a teammate processes them. When not enabled, the main agent dispatches directly.
  - **Rationale**: Reviewer identified that a persistent daemon accumulates stale context via compaction, contradicting the "always reads most recent version" principle. Fresh-per-insight matches Anthropic's design (fresh agent per update), has better context hygiene, and is simpler. Agent Teams adds value for concurrent sessions but shouldn't be required.

- [x] **#2 What does "idle" mean / when does the subagent run?**
  - **Anthropic**: Background subagent fires during lulls when user hasn't sent a new message.
  - **Us**: `run_in_background: true` on the Agent tool. The subagent runs without blocking the main conversation. Fire-and-forget from the main agent's perspective.
  - **With Agent Teams**: Insights are queued as tasks. The teammate processes them independently.
  - **Proactive mode (deferred)**: The idea of scanning git diffs during idle time is deferred. The primary value is the insight-dispatch path. Proactive scanning can be added later once the core system works and the coordination mechanism is designed.

- [x] **#5 What tools does the subagent have?**
  - **Anthropic**: Edit only — doc contents are pre-loaded via template variables.
  - **Us**: `Glob, Read, Edit` only. No Write (can't create new docs — that's `/create-magicdoc`). No Bash.
  - **Rationale**: The subagent needs Glob to find docs (two-pass discovery) and Read to get current contents, since we can't use template variables. Minimal toolset keeps the agent scoped. No Bash prevents unconstrained shell access.

- [x] **#11 How are docs discoverable to future sessions?**
  - **Anthropic**: Internal pipeline loads them automatically.
  - **Us**: CLAUDE.md pointer installed by the bootstrap skill: "Architectural documentation is maintained in docs/magic/ and may also be co-located with code (grep for `# MAGIC DOC:` headers). Read the relevant Magic Doc before making changes to a subsystem you're unfamiliar with."
  - **Rationale**: Verified via `/classify-info` decision tree — prescriptive, always-relevant prior → CLAUDE.md. Updated to reflect that docs can live in both locations.

- [x] **#4 What prompt does the magicdocs subagent get?**
  - **Anthropic**: `agent-prompt-update-magic-docs.md` — philosophy, rules, template variables for doc contents.
  - **Us**: Replicate the philosophy and rules nearly verbatim. Two adaptations: (1) the subagent reads the doc itself (Glob + Read) instead of receiving template variables, and (2) the insight comes from the dispatch message, not the conversation transcript. The subagent always reads the most recent version of the doc on disk.
  - **Access control**: Prompt instructs the subagent to only read/edit files containing `# MAGIC DOC:` headers. A PreToolUse hook on Edit enforces writes mechanically by validating the target file has the header. Note: this only restricts writes, not reads — read restriction relies on prompt compliance (partial enforcement, acknowledged as a known limitation).

- [x] **#6 What model?**
  - **Anthropic**: Sonnet.
  - **Us**: Sonnet. Cost-optimized, fast enough for doc edits.

- [x] **#9 Can the agent create new docs?**
  - **Anthropic**: No — Edit only.
  - **Us**: No. Separate `/create-magicdoc` skill handles creation. The update subagent reports "no existing doc covers this" and suggests the user create one.

- [x] **#7 How are docs discovered on disk?**
  - **Anthropic**: Regex `^#\s*MAGIC\s+DOC:\s*(.+)$/im` — scans anywhere in repo.
  - **Us**: Support both: (1) conventional directory `docs/magic/*.md`, and (2) scattered docs co-located with code (e.g., `src/auth/MAGIC_DOC.md`). Discovery is two-pass: glob the conventional directory, then grep repo-wide for `^# MAGIC DOC:` headers. The bootstrap skill creates `docs/magic/` as the default location.
  - **Rationale**: Matches Anthropic's flexibility. Users choose what fits their project.

- [x] **#10 How do docs stay current / self-pruning?**
  - **Anthropic**: "Remove outdated info", "delete irrelevant sections", update in-place on every edit.
  - **Us**: Same — pruning is inline during updates, not a separate step. The prompt tells the subagent to remove outdated info and delete irrelevant sections as part of every edit. Orphaned docs (for deleted subsystems) are out of scope — handled manually.

## Open Architectural Questions

- [x] **Should we use Agent Teams for the magicdocs agent?** Optional enhancement for multi-session coordination. Fresh-per-insight is the primary architecture.
- [x] **What does the bootstrap skill install?**
  - **`/setup-magicdocs`** (the bootstrap skill itself): Explores the repo structure, proposes 2-3 segmentation strategies tailored to the project (by subsystem, by directory, by entry point, etc.), user picks one, skill creates the initial skeleton docs. Opinionated about the system (update mechanics, philosophy, conventions) but collaborative about segmentation (how to slice up this specific codebase).
  - **Files created**: `docs/magic/` directory + initial skeleton docs based on chosen segmentation, `.claude/skills/create-doc/SKILL.md` (for adding individual docs later)
  - **Files modified** (with user confirmation): `CLAUDE.md` (append pointer), `.claude/settings.json` (PreToolUse edit guard hook). Optionally: Agent Teams config, Stop hook safety net.
  - **No `/update-docs` skill** — updates are handled automatically via `/classify-info` → MagicDocs classification → fresh subagent dispatch. Manual override is just the user saying "remember this."
  - **`/create-doc <title>`**: Simpler skill for adding one new magic doc when a new subsystem is added later. Explores the relevant code, writes the initial doc following the MagicDocs philosophy.
  - **Uninstall**: Remove skills directories, revert CLAUDE.md additions, remove hooks from settings.json. `docs/magic/` content preserved by default (user can delete manually).
- [x] **How does `/classify-info` integration work?** `/classify-info` classifies and returns "MagicDocs" — that's it. The main agent handles dispatch: formulates the insight message, specifies the target doc, spawns a fresh Sonnet subagent with the MagicDocs prompt. This keeps `/classify-info` a pure classification skill (testable independently at 100%) and leaves the codebase-context-dependent work (insight formulation, doc targeting) to the main agent.
- [x] **Should there be a Stop hook as a safety net?** Yes — core part of the design, not optional. A `Stop` hook gated on meaningful code changes (`git diff --stat`) runs a headless `claude -p --model sonnet` that reconciles magic docs against the diff. This is a **pruning pass**, not an insight pass — it doesn't add new architectural knowledge (that requires conversation context), it checks whether existing doc claims are contradicted by code changes (wrong file paths, deleted code still referenced, changed structure). Simpler and more reliable task for a context-poor agent. The prompt is different from the insight-dispatch prompt — it's reconciliation, not synthesis.
- [x] **How are bad edits detected / how are edits persisted?** The subagent edits files and leaves them **unstaged**. No auto-commit, no worktrees, no branch management. Magic doc files are "owned" by the magicdocs system — no other subagent should be editing them, so unstaged changes don't interfere with concurrent work. The user's next commit naturally picks up the changes. CLAUDE.md includes a note so code reviewers and other subagents know magic doc changes are auto-generated and expected: "Files with `# MAGIC DOC:` headers are auto-maintained by the magicdocs system. Changes to these files may appear in unstaged diffs — this is expected." Bad edits are visible in `git diff` and recoverable via `git checkout -- docs/magic/file.md`.
- [x] **What is the uninstall path?** Remove `.claude/skills/create-doc/`, revert CLAUDE.md additions (pointer + reviewer note), remove PreToolUse edit guard hook and Stop hook from settings.json. `docs/magic/` content preserved by default — it's useful documentation even without the automation. User can delete manually if desired.
- [x] **Chapter 5 update.** Chapter 5 (`docs/05-building-magicdocs.md`) describes the system as triggering post-conversation via a Stop hook. Our research found MagicDocs triggers incrementally via `postSamplingHook`. Chapter 5 should be updated to reflect the spec's architecture. This is part of the deliverable.

## Key Research Findings

1. **Agent hooks (`type: "agent"`) do NOT have conversation context.** They spawn independent subagents that only see `$ARGUMENTS` JSON. Cannot be used for context-rich doc updates.

2. **Compaction timing is adjustable earlier only.** `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` env var triggers compaction sooner (e.g., at 75% capacity), but cannot delay past the default ~83.5% cap. "Trigger with 5% remaining" (95% used) is not possible — only "trigger with more remaining."

3. **MagicDocs is fully internal.** No public activation. The code exists at `src/services/MagicDocs/` with the header regex, but it's gated to internal builds. Matt Palmer confirms it's an employee feature.

4. **MagicDocs triggers incrementally, not post-conversation.** `postSamplingHook` fires after each tool-call-bearing model response, not at session end. This validates our incremental-dispatch design over the batch-update model from Chapter 5.

5. **Agent Teams (experimental)** provides cross-session IPC: shared task lists with file-locking, mailbox messaging between teammates, idle notifications. Enable with `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in settings.json env. Confirmed real and documented at code.claude.com/docs/en/agent-teams.

6. **Community MCP solutions exist** for cross-session messaging without Agent Teams: `claude-peers-mcp` (SQLite broker, localhost), `claude-ipc-broker` (HTTP+SSE, cross-machine). These are third-party and add infrastructure dependencies.

7. **Subagent context is always fresh.** Each subagent starts with zero conversation history and only sees the prompt written for it. This is why focused insights work better than transcript dumps — the subagent needs to understand one specific thing, not reconstruct an entire conversation.

## Review Findings (from subagent review)

Issues identified and how we addressed them:

1. **Daemon model has worse context hygiene than fresh-per-insight** — Flipped: fresh-per-insight is now the primary architecture. Agent Teams is optional enhancement.
2. **Subagent asked to judge doc relevance with minimal context** — Fixed: main agent now specifies the target doc.
3. **PreToolUse hook only restricts writes, not reads** — Acknowledged as known limitation. Read restriction relies on prompt compliance.
4. **100% /classify-info accuracy is answering the wrong question** — Added reliability caveat. The real risk is the main agent not invoking /classify-info in the first place. Stop hook safety net partially mitigates.
5. **CLAUDE.md pointer inconsistent with scattered docs** — Fixed: pointer now mentions both locations.
6. **Proactive mode coordination is underspecified** — Deferred entirely. Ship core insight-dispatch first.
7. **Chapter 5 contradicts the spec** — Added to open questions as a deliverable.
8. **Bootstrap skill scope underspecified** — Promoted to open question with requirements for full specification.
9. **Agent Teams fallback underspecified** — Flipped: fresh-per-insight is now primary, Agent Teams is the optional upgrade.
10. **No conflict resolution for concurrent edits** — Known limitation. Magic docs are idempotent-ish (in-place updates, current-state-only), so redundant edits are low-harm. Contradictory edits are possible but unlikely at expected update frequency.
11. **/classify-info integration handoff unclear** — Still open. Leaning toward: /classify-info classifies, separate dispatch mechanism handles subagent spawn.
12. **No bad-edit detection** — Added to open questions. At minimum, make edits visible via logging.
13. **Missing: token budget, testing strategy, uninstall path, staleness detection** — Uninstall path added to open questions. Token budget and testing strategy to be addressed in the implementation plan. Staleness detection out of scope (manual).

## Existing Project Context

This spec lives in the `airbender` project, which is a manual about Claude Code's context engineering internals. The project contains:
- `docs/01-05`: Five-chapter manual covering context engineering, subagents, what-to-put-where, and building MagicDocs
- `skills/classify-info/`: A classification skill that routes information to Hook/MagicDocs/Skill/CLAUDE.md/Memory/None, with a 26-item test suite achieving 100% accuracy
- `docs/spec-claude-code-context-engineering-manual.md`: Design spec for the manual itself

The magicdocs system should work in **any** repo, not just this one. The bootstrap skill will be designed for portability.

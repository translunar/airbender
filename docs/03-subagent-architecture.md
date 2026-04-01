# Subagent Architecture

Claude Code doesn't do everything in a single conversation thread. It spawns separate agent processes — subagents — for complex or parallelizable work. Each subagent gets its own context window, runs on a model chosen for the task, and has access to a restricted set of tools. This protects the main conversation from context bloat — subagent work happens in a separate context, and only a compressed summary flows back. Understanding how subagents work is important before deciding how to structure your own customizations, because the context engineering rules change when work is delegated.

## Subagent types

Claude Code has several built-in subagent types, each optimized for different work:

### General-purpose

- **Model**: Opus (the full, most capable model)
- **Tools**: Most tools available — Edit, Write, Bash, Glob, Grep, Read, and more
- **Purpose**: Complex multi-step tasks that require both research and implementation
- **Behavior**: Told to "execute tasks fully" using available tools, then deliver concise reports of actions and findings for the main agent to relay to the user
- **Constraints**: Explicitly told "NEVER create files unless absolutely necessary" and prohibited from proactively creating documentation files

[source: `agent-prompt-general-purpose.md`](https://github.com/Piebald-AI/claude-code-system-prompts/blob/main/system-prompts/agent-prompt-general-purpose.md). The model assignment (Opus) and tool list (`*` wildcard) come from the agent definition in `generalPurposeAgent.ts`, referenced in [`tools_snapshot.json`](https://github.com/instructkr/claw-code/blob/main/src/reference_data/tools_snapshot.json).

### Explore

- **Model**: **Haiku** (the cheapest, fastest model)
- **Tools**: Read-only only — Glob, Grep, Read, Bash. Explicitly **cannot** Edit, Write, or spawn sub-subagents
- **Purpose**: Rapid codebase exploration — finding files, searching code, answering questions about structure
- **Behavior**: "Exclusively to search and analyze existing code." Three thoroughness levels: quick, medium, very thorough
- **Constraints**: Strict prohibitions against file creation, modification, deletion, or system state changes. Should leverage parallel tool calls for efficiency

This is why Explore agents are fast — they run on the cheapest model and can only read. It's also why they can't make changes, even if they discover a problem.

[source: `agent-prompt-explore.md`](https://github.com/Piebald-AI/claude-code-system-prompts/blob/main/system-prompts/agent-prompt-explore.md)

### Other specialized types

- **Plan**: Research and design agent, no implementation tools
- **Claude-code-guide**: Answers questions about Claude Code itself — features, settings, MCP servers
- **Verification**: Validates completed work against requirements
- **Statusline-setup**: Configures the CLI status line display

[source: `tools_snapshot.json` — built-in agent entries under `tools/AgentTool/built-in/`](https://github.com/instructkr/claw-code/blob/main/src/reference_data/tools_snapshot.json). Descriptions are inferred from agent names and corresponding prompt files in [claude-code-system-prompts](https://github.com/Piebald-AI/claude-code-system-prompts/tree/main/system-prompts).

## How subagent context is constructed

This is the most important thing to understand about subagents: **each one starts with zero conversation history.** A subagent has no access to the messages exchanged between you and the main agent. It receives only the prompt that the main agent writes for it.

Because fresh subagents start with zero context, they require thorough briefing. The prompt should be written as if briefing "a smart colleague who just walked into the room." This means including:

- Your **goals** and reasoning behind the task
- What you've **already attempted** or discovered
- **Surrounding problem details** that enable sound judgment
- **Concrete details** like file paths and line numbers rather than vague directives

[source: `system-prompt-writing-subagent-prompts.md`](https://github.com/Piebald-AI/claude-code-system-prompts/blob/main/system-prompts/system-prompt-writing-subagent-prompts.md)

## How to write good subagent prompts

Beyond the general context requirements, the prompts guide has specific stylistic recommendations:

- **Specify length constraints** when brevity matters ("report in under 200 words")
- **For investigations, pose the question** rather than prescribing steps — let the subagent figure out how to investigate
- **Provide concrete details** — file paths and line numbers, not "look at the auth code"
- **"Never delegate understanding"** — don't write "based on your findings, fix the bug." The main agent should demonstrate its own comprehension by offering specific guidance about what needs changing and where

The key principle: avoid terse, command-style prompts. "Fix the bug in auth" will get shallow results from a subagent that has never seen your codebase and has no conversation context. "There's a null pointer exception in `src/middleware/auth.ts:47` when `session.user` is undefined. The middleware assumes authenticated requests always have a user object, but the `/health` endpoint bypasses auth. Fix the null check" gives the subagent everything it needs.

[source: `system-prompt-writing-subagent-prompts.md`](https://github.com/Piebald-AI/claude-code-system-prompts/blob/main/system-prompts/system-prompt-writing-subagent-prompts.md)

## How results come back

When a subagent completes its work, the results don't flow back to the main context as raw output. They're compressed through a summary generation step that produces **3-5 word present tense descriptions** of what the agent is doing:

- "Reading runAgent.ts"
- "Fixing null check in validate.ts"
- "Running auth module tests"
- "Adding retry logic to fetchUser"

These summaries are:
- Always present tense (gerund form)
- Focused on specific files or functions, never branch names
- Compared against `PREVIOUS_AGENT_SUMMARY` to avoid repetition
- Short enough that they don't consume significant context

The practical effect is that subagent output doesn't blow up the main context window — the detailed findings are available in the subagent's response, but what gets shown in the conversation is a concise summary.

[source: `system-prompt-agent-summary-generation.md`](https://github.com/Piebald-AI/claude-code-system-prompts/blob/main/system-prompts/system-prompt-agent-summary-generation.md). The context window protection benefit is the authors' interpretation of this design, not an explicit claim in the source.

## The coordinator pattern

When the main agent delegates work to a subagent, it enters a coordinator role with specific behavioral rules:

**Transparent waiting.** After delegation, the coordinator "knows nothing about the findings yet." The turn ends. If you ask follow-up questions while the subagent is working, the coordinator acknowledges the pending task without fabricating results: "Still waiting on the audit — that's one of the things it's checking."

**Independent review.** When requesting a second opinion (e.g., having a subagent review code that the main agent wrote), specifying a `subagent_type` ensures the subagent works independently. The prompt provides full context so the subagent doesn't inherit the coordinator's prior analysis, enabling genuinely separate assessment.

**Result synthesis.** When subagent results arrive via notifications, the coordinator synthesizes findings into concise summaries for the user rather than dumping raw output.

[source: `system-prompt-subagent-delegation-examples.md`](https://github.com/Piebald-AI/claude-code-system-prompts/blob/main/system-prompts/system-prompt-subagent-delegation-examples.md)

## Practical implications

**Why vague prompts to subagents fail.** A subagent starts with no conversation history. If the main agent writes a terse prompt like "explore the auth system," the subagent has no idea what the project is, what stack it uses, or what specifically about auth is relevant. Front-load context.

**Why Explore agents are fast but limited.** They run on Haiku (the cheapest model) with read-only tools. This makes them ideal for "find all files matching X" or "how does this module work?" but useless for "fix this bug." If you need changes made, use a general-purpose agent.

**When to parallelize.** Subagents are independent — they don't share state with each other or with the main conversation. This means truly independent tasks (search for X while searching for Y) can be parallelized effectively. Tasks that depend on each other's results cannot.

**The 16-iteration limit.** Each conversation turn has a maximum of 16 iterations in the tool-use loop. If Claude calls a tool, gets a result, calls another tool, gets a result, and so on — it will stop after 16 cycles even if the task isn't complete. This is why complex tasks sometimes stop mid-way. Breaking work into smaller, delegated chunks avoids hitting this limit.

[source: `conversation.rs` — `max_iterations: 16`](https://github.com/instructkr/claw-code/blob/main/rust/crates/runtime/src/conversation.rs)

## Real-world example: subagent-driven development

The [superpowers](https://github.com/nichochar/superpowers) plugin for Claude Code includes a "subagent-driven-development" skill that demonstrates these principles in practice. The skill acts as a controller that:

1. **Reads an implementation plan** and identifies independent tasks
2. **Dispatches each task to a fresh subagent** with thorough context — the skill explicitly provides file paths, requirements, and constraints rather than vague directives
3. **Runs two-stage review** on each subagent's output: first checking spec compliance, then code quality — using separate review subagents to get genuinely independent assessment
4. **Coordinates results** back into the main context without flooding it

This pattern — controller coordinates, subagents execute independently, reviewers validate — mirrors the coordinator pattern described above. The skill also demonstrates the importance of context isolation: each subagent gets exactly the context it needs for its specific task, not the entire conversation history.

Other skills in the same suite show complementary subagent patterns: "dispatching parallel agents" for grouping independent tasks by problem domain, and "verification before completion" for ensuring subagent work is validated before claiming success.

## Next

[Chapter 4: What to Put Where →](04-what-to-put-where.md)

# Airbender

This project is a manual about Claude Code's context engineering internals — how it assembles prompts, manages subagents, handles compaction, and maintains documentation. It also contains skills (like `/classify-info`) and design specs for building systems that replicate Anthropic's internal tooling.

Architectural documentation is maintained in docs/magic/ and may also be co-located with code (grep for `# MAGIC DOC:` headers). Read the relevant Magic Doc before making changes to a subsystem you're unfamiliar with.

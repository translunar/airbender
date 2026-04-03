# Testing: /create-magicdoc skill

## Test Environment

**Target repo**: ~/Projects/social (with magicdocs already set up via /setup-magicdocs)
**Target subsystem**: Browser extension (extension/ directory)
**Model**: Sonnet
**Date**: 2026-04-03

## RED Baseline (without skill)

**Prompt**: "Create a new Magic Doc for the browser extension subsystem"
**Prerequisite**: Magicdocs system already set up with 3 existing docs
**Score**: 2/7

| # | Criterion | Result | Notes |
|---|-----------|--------|-------|
| 1 | `# MAGIC DOC:` header | PASS | Learned from existing docs in repo |
| 2 | Italicized one-liner | PASS | Learned from existing docs |
| 3 | Word count <500 | FAIL | 934 words — nearly 2x limit |
| 4 | Standard sections only | FAIL | 7 sections including "Message Types", "Sync Phase State Machine", "DOM Scraping Patterns", "Post Data Shape" |
| 5 | No exhaustive lists | FAIL | Full message type table, data shapes |
| 6 | Architecture focus | FAIL | Code walkthrough, not architecture |
| 7 | Checked for duplicates | UNCLEAR | Didn't mention checking |

### Failure patterns

1. **Convention learned, philosophy not**: The agent copied the header format from existing docs but had no concept of terseness or content rules
2. **Implementation detail magnet**: Added sections for every technical concern discovered — message types, data shapes, DOM patterns
3. **Exploration = documentation**: Agent documented everything it explored rather than filtering for architectural significance

## GREEN (with skill)

**Score**: 7/7

| # | Criterion | Result | Notes |
|---|-----------|--------|-------|
| 1 | `# MAGIC DOC:` header | PASS | Correct format |
| 2 | Italicized one-liner | PASS | Present |
| 3 | Word count <500 | PASS | 411 words |
| 4 | Standard sections only | PASS | 4 sections: Overview, Key Entry Points, Non-Obvious Patterns, Dependencies |
| 5 | No exhaustive lists | PASS | No tables, no exhaustive lists |
| 6 | Architecture focus | PASS | WHY and HOW: shared scope, navigation survival, health indicator design |
| 7 | Checked for duplicates | PASS | Checked existing docs first |

### Key improvement

Content went from code walkthrough (934 words, 7 sections) to architectural map (411 words, 4 sections). The "Do NOT document" list and 500-word limit were the key constraints. The "Section count" rule prevented the agent from creating extra sections for every technical concern.

## Progression

| Phase | Score | Key Fixes |
|-------|-------|-----------|
| RED | 2/7 | — |
| GREEN | 7/7 | 500-word limit, "Do NOT document" list, standard sections only |

No REFACTOR needed — GREEN passed cleanly on all criteria.

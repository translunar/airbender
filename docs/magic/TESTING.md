# MagicDocs MVP — Test Results

## Test Suite: 5 Insights

| # | Insight Summary | Expected Behavior |
|---|----------------|-------------------|
| 1 | Chapter 5's Stop hook approach is wrong; postSamplingHook is incremental | Update Non-Obvious Patterns, possibly Structure |
| 2 | New magicdocs design spec exists, should be referenced | Add to Key Entry Points or References |
| 3 | /classify-info skill only adds value at MagicDocs and CLAUDE.md/Memory boundaries | Update Non-Obvious Patterns |
| 4 | "Project uses pnpm" — CLAUDE.md fact, not architecture | NO EDIT — correctly reject |
| 5 | Chapters are dependent, not independent | Update Structure or recognize already captured, either is acceptable |

## Evaluation Criteria

- **Relevance**: Correctly identifies whether insight belongs in the doc
- **Placement**: Puts information in the right section
- **Terseness**: High-signal, no filler
- **Preservation**: Preserves header and existing structure
- **Pruning**: Updates in-place rather than appending
- **Non-edit accuracy**: Correctly declines to edit when appropriate

## RED Baseline — Sonnet

**Model**: Sonnet
**Prompt**: Naive — no MagicDocs philosophy, just "update the doc with this info"
**Score**: 1/5

| # | Expected | Result | Relevance | Placement | Terseness | Preservation | Pruning | Non-edit |
|---|----------|--------|-----------|-----------|-----------|-------------|---------|----------|
| 1 | Update Non-Obvious Patterns | Added 5-line note under Ch5 in Structure | PASS | PARTIAL — belongs in Non-Obvious Patterns, not Structure | FAIL — verbose, filler phrases | PASS | FAIL — appended instead of updating existing bullet about Ch5 | — |
| 2 | Add to Key Entry Points | Added bullet to Key Entry Points | PASS | PASS | PARTIAL — long but informative | PASS | PASS | — |
| 3 | Update Non-Obvious Patterns | Updated existing skill bullet in Non-Obvious Patterns | PASS | PASS | FAIL — 6 lines added where 1-2 suffice | PASS | PARTIAL — in-place but bloated the bullet | — |
| 4 | NO EDIT | Created new "Project Setup" section with pnpm | FAIL | — | — | PASS | — | FAIL — should not have edited |
| 5 | Update Structure or no edit | Added 4-line bullet to Non-Obvious Patterns | PARTIAL — already captured | OK | FAIL — redundant with "each building on the previous" | PASS | FAIL — appended instead of recognizing already captured | FAIL |

### Failure patterns

1. **Verbose**: Every edit added more text than needed. No concept of terseness.
2. **No rejection capability**: Insight #4 (pnpm) was accepted and given a whole new section. Without philosophy, the agent has no basis to reject non-architectural info.
3. **Duplication over update**: Insights #1 and #5 both added new content instead of updating/recognizing existing content that already covered the topic.
4. **Insight #2 was actually decent**: Correct placement, reasonable content. Simple "add a reference" tasks work fine without philosophy.

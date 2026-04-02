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

## RED Baseline — Haiku

**Model**: Haiku
**Prompt**: Naive — no MagicDocs philosophy, just "update the doc with this info"
**Score**: 1/5

| # | Expected | Result | Relevance | Placement | Terseness | Preservation | Pruning | Non-edit |
|---|----------|--------|-----------|-----------|-----------|-------------|---------|----------|
| 1 | Update Non-Obvious Patterns | Updated existing Ch5 bullet in Non-Obvious Patterns in-place | PASS | PASS | PARTIAL — one filler sentence ("Readers should note...") | PASS | PASS — correctly updated in-place | — |
| 2 | Add to Key Entry Points | Created new "Design Specification" section | PASS | FAIL — new section instead of bullet in Key Entry Points | FAIL — verbose description | PASS | FAIL — new section instead of using existing structure | — |
| 3 | Update Non-Obvious Patterns | Updated existing skill bullet in-place | PASS | PASS | PASS — 3 lines, concise | PASS | PASS — in-place update | — |
| 4 | NO EDIT | Added pnpm line to Overview | FAIL | — | — | PASS | — | FAIL — should not have edited |
| 5 | Update Structure or no edit | Modified header, added dependency note under Ch4, added paragraph | PARTIAL — already captured | OK | FAIL — 3 separate changes for info already in doc | PARTIAL — modified section header | FAIL — over-edited existing content | FAIL |

### Failure patterns

1. **Same rejection failure as Sonnet**: Insight #4 (pnpm) accepted by both models. Neither can reject non-architectural info without philosophy.
2. **Better in-place updates than Sonnet**: Insights #1 and #3 were correctly updated in-place (Sonnet appended or bloated these).
3. **Worse on structure**: Created a new section for #2 where Sonnet correctly used Key Entry Points. Over-edited #5 with 3 separate changes.
4. **Slightly more terse**: Haiku's edits were generally shorter than Sonnet's, especially on #3.

### Sonnet vs Haiku Comparison

| # | Sonnet | Haiku | Better |
|---|--------|-------|--------|
| 1 | FAIL — wrong section, appended | PASS — in-place, right section | **Haiku** |
| 2 | PASS — right section, one bullet | FAIL — new section | **Sonnet** |
| 3 | FAIL — 6 lines, bloated | PASS — 3 lines, concise | **Haiku** |
| 4 | FAIL — both accepted pnpm | FAIL — both accepted pnpm | **Tie (both fail)** |
| 5 | FAIL — appended redundant bullet | FAIL — over-edited 3 places | **Tie (both fail)** |

Neither model rejects non-architectural info. Haiku is better at in-place terse updates. Sonnet is better at using existing structure (Key Entry Points). Both fail on the same fundamental issues — the philosophy should fix these.

## GREEN — Sonnet

**Model**: Sonnet
**Prompt**: Full MagicDocs philosophy (PROMPT.md)
**Score**: 3.5/5

| # | Expected | Result | Pass? | Notes |
|---|----------|--------|-------|-------|
| 1 | Update Non-Obvious Patterns | Updated existing Ch5 bullet in-place, terse, direct | **PASS** | Huge improvement — replaced vague "needs updating" with clear statement. 3 lines, no filler. |
| 2 | Add to Key Entry Points | NO EDIT — rejected because `docs/magicdocs-design-questions.md` doesn't exist at that path | **PARTIAL FAIL** | Correct rejection logic (don't add dead links) but the file exists at `docs/reference/magicdocs-design-questions.md`. The insight gave the wrong path. This is an insight quality issue, not a prompt quality issue. |
| 3 | Update Non-Obvious Patterns | Updated existing skill bullet in-place, terse | **PASS** | 4 lines, concise. Named the 4 native categories and 2 boundaries. Much better than RED's 6-line bloat. |
| 4 | NO EDIT | Correctly rejected — "CLAUDE.md-level fact, not architectural information" | **PASS** | Perfect. Exactly the reasoning we wanted. RED baseline failed this completely. |
| 5 | Update Structure or no edit | Added terse bullet to Non-Obvious Patterns about Ch2→Ch3→Ch4 dependency | **PARTIAL** | Acceptable — the edit is terse and well-placed, but the info is arguably already captured by "each building on the previous." The subagent acknowledged this but added specifics. Both outcomes are valid per spec. |

### What improved from RED

1. **Rejection capability**: Insight #4 (pnpm) correctly rejected with precise reasoning. This was the biggest RED failure.
2. **In-place updates**: #1 and #3 both updated existing bullets rather than appending new content.
3. **Terseness**: All edits are significantly shorter and higher-signal.
4. **Pruning**: #1 replaced outdated phrasing ("needs updating") with current-state language.

### Remaining issues

1. **Insight #2 false negative**: The subagent verified the file path and correctly refused to add a dead link, but the file exists at a different path. The insight should have provided the correct path — this is an insight quality issue, not a prompt quality issue. The main agent (which dispatches insights) should verify paths before dispatching.
2. **Insight #5 borderline**: Added content that's arguably already captured. Not a failure, but shows the "already captured" detection could be sharper.

## GREEN — Haiku

**Model**: Haiku
**Prompt**: Full MagicDocs philosophy (PROMPT.md) + added "IMPORTANT: Only edit the target document"
**Score**: 2.5/5

| # | Expected | Result | Pass? | Notes |
|---|----------|--------|-------|-------|
| 1 | Update Non-Obvious Patterns | SCOPE VIOLATION — edited target doc AND Chapter 5 AND Chapter 4 | **FAIL** | Correct edit to target doc (in-place update) but also made extensive edits to docs/05-building-magicdocs.md and docs/04-what-to-put-where.md. Haiku went way beyond scope despite being told to only edit the target doc. Added "IMPORTANT: Only edit the target document" to subsequent prompts. |
| 2 | Add to Key Entry Points | NO EDIT — reasoned the design spec is "reference material, not an architectural pattern" | **PARTIAL** | Thoughtful reasoning but wrong conclusion — a key entry point IS a reference. Different rejection reason than Sonnet (Sonnet checked file existence, Haiku judged relevance). |
| 3 | Update Non-Obvious Patterns | Updated existing skill bullet in-place, 3 lines, terse | **PASS** | Excellent. Very similar quality to Sonnet #3. Concise, correct placement. |
| 4 | NO EDIT | Correctly rejected — cited the decision tree from Chapter 4 and our own TESTING.md | **PASS** | Even better reasoning than Sonnet — explicitly referenced the project's own classification framework. Did read extra files to justify the rejection. |
| 5 | Update Structure or no edit | Modified header ("with specific dependencies"), added parenthetical to Ch4, added separate note | **FAIL** | Over-edited. Changed "each building on the previous" to "with specific dependencies" which loses information (sequential nature). Three separate changes for info already captured. Same failure as RED Haiku #5. |

### What improved from RED

1. **Rejection capability**: Insight #4 correctly rejected (same as Sonnet). The philosophy's "When NOT to edit" section works.
2. **Insight #3 quality**: Terse, in-place — excellent. Consistent with RED Haiku (which was already good on this one).

### Remaining issues

1. **Scope violation on #1**: Haiku edited multiple files despite being told to edit only the target. Even after adding an explicit "IMPORTANT: Only edit the target document" instruction, this is a risk. The prompt needs stronger scope constraints, or Haiku's tool access needs to be more restricted.
2. **Insight #2 false negative**: Different reasoning than Sonnet but same outcome — no edit. Haiku decided the design spec isn't architecturally relevant; Sonnet decided the file didn't exist. Both wrong, but for different reasons.
3. **Insight #5 still over-edits**: Same failure pattern as RED baseline — Haiku modifies existing content that already captures the insight instead of recognizing it's already there. The "already captured" detection doesn't improve with the full prompt for Haiku.

### Sonnet vs Haiku GREEN Comparison

| # | Sonnet GREEN | Haiku GREEN | Better |
|---|-------------|-------------|--------|
| 1 | PASS — terse in-place update | FAIL — scope violation | **Sonnet** |
| 2 | PARTIAL — refused (file not found) | PARTIAL — refused (not relevant) | **Tie (both fail differently)** |
| 3 | PASS — 4 lines, in-place | PASS — 3 lines, in-place | **Tie (both good)** |
| 4 | PASS — rejected as CLAUDE.md fact | PASS — rejected, cited decision tree | **Tie (both good, Haiku more thorough)** |
| 5 | PARTIAL — added terse bullet, borderline | FAIL — over-edited, lost info | **Sonnet** |

**Sonnet scores 3.5/5, Haiku scores 2.5/5 with full prompt.** Sonnet is more reliable — it respects scope and handles borderline cases better. Haiku's scope violation (#1) is a serious concern for an automated system. Haiku is cheaper but less trustworthy for this task.

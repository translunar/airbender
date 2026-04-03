# Prune MagicDocs — Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and TDD-validate a `/prune-magicdocs` skill that detects and fixes stale content in magic docs.

**Architecture:** This is a skill (SKILL.md), not code. The TDD cycle follows writing-skills: RED (baseline without skill) → GREEN (write skill, re-test) → REFACTOR (close loopholes). Testing uses ~/Projects/social with intentionally corrupted magic docs as test fixtures.

**Tech Stack:** Claude Code skills (SKILL.md), Agent tool for subagent testing, ~/Projects/social as test repo.

---

### Task 0: Set Up Test Fixtures in Social

Create corrupted magic docs in ~/Projects/social to test against. We need the magicdocs system set up first, then inject specific problems.

**Files:**
- Create: `/Users/juno/Projects/social/docs/magic/` (via /setup-magicdocs)
- Modify: Magic docs to inject corruption

- [ ] **Step 1: Run /setup-magicdocs in social**

Spawn a Sonnet subagent to set up magicdocs in ~/Projects/social using the setup-magicdocs skill. Simulate user choices (pick the suggested segmentation, confirm CLAUDE.md and hooks changes).

- [ ] **Step 2: Inject corruption — dead file references**

Pick one of the created magic docs and add a reference to a file that doesn't exist. For example, in whichever doc covers the server, add to Key Entry Points:

```markdown
- `server_middleware.py` — request validation and rate limiting
```

This file doesn't exist. The pruning skill should detect and flag it.

- [ ] **Step 3: Inject corruption — wrong architectural claim**

In whichever doc covers the analysis pipeline, change a factual claim to be wrong. For example, if it says the analysis uses Claude for classification, change it to say it uses GPT-4. The pruning skill should detect this by checking the actual code.

- [ ] **Step 4: Inject corruption — deleted function reference**

In whichever doc covers the server or data layer, add a reference to a function that doesn't exist in the code:

```markdown
- `validate_post_schema()` is called before every merge to ensure data integrity
```

Grep for `validate_post_schema` should return nothing. The pruning skill should catch this.

- [ ] **Step 5: Inject corruption — stale directory description**

In whichever doc mentions directory structure, add a claim about a directory or file that doesn't exist:

```markdown
The `analysis/cache/` directory stores precomputed embeddings for faster re-runs.
```

If `analysis/cache/` doesn't exist, the pruning skill should flag it.

- [ ] **Step 6: Record the corruptions**

Note exactly what was corrupted, in which files, and what the expected detection/fix is. This is the test suite:

| # | Corruption Type | What Was Injected | Expected Detection |
|---|----------------|-------------------|-------------------|
| 1 | Dead file reference | `server_middleware.py` in Key Entry Points | File doesn't exist on disk |
| 2 | Wrong architectural claim | Changed API provider name | Grep actual code, find contradiction |
| 3 | Deleted function reference | `validate_post_schema()` | Grep finds no definition |
| 4 | Stale directory description | `analysis/cache/` directory | Directory doesn't exist |

- [ ] **Step 7: Commit the test fixtures (do not commit to social)**

These changes are intentional corruptions — do NOT commit them to social's git. They exist only as unstaged modifications for testing. Verify with `git diff` in social that the corruptions are present.

---

### Task 1: RED — Baseline Without Skill

Ask a subagent to check magic docs for staleness without the prune-magicdocs skill.

**Files:**
- Create: `skills/prune-magicdocs/TESTING.md` (in airbender)

- [ ] **Step 1: Run RED baseline**

Spawn a Sonnet subagent with this prompt (no skill):

```
The repository at /Users/juno/Projects/social has magic docs in docs/magic/.
Check all magic docs for stale or incorrect content — references to files
that don't exist, functions that have been deleted, wrong claims about the
architecture, etc. Report what you find and fix what you can.
```

- [ ] **Step 2: Review what the subagent found and fixed**

Check:
- Did it detect all 4 corruptions?
- Did it fix them or just report them?
- Did it make any false positives (flagging correct content as stale)?
- How did it approach the task (systematic checks vs reading and guessing)?
- Did it check file existence mechanically, or just read the docs and reason about them?

- [ ] **Step 3: Record RED results in TESTING.md**

Create `skills/prune-magicdocs/TESTING.md` in airbender with the baseline results. Score each corruption on detection and fix quality.

- [ ] **Step 4: Revert any fixes the subagent made in social**

```bash
cd /Users/juno/Projects/social && git checkout -- docs/magic/
```

Then re-inject the corruptions (repeat Task 0 steps 2-5) so the docs are corrupted again for GREEN testing.

- [ ] **Step 5: Commit RED results to airbender**

```bash
cd /Users/juno/Projects/airbender
git add skills/prune-magicdocs/TESTING.md
git commit -m "test(red): prune-magicdocs baseline — record detection without skill"
```

---

### Task 2: GREEN — Write and Test the Skill

Write the skill addressing RED failures, then re-test.

**Files:**
- Create: `skills/prune-magicdocs/SKILL.md` (in airbender)
- Modify: `skills/prune-magicdocs/TESTING.md`

- [ ] **Step 1: Write SKILL.md**

Create `skills/prune-magicdocs/SKILL.md` in airbender. The skill should instruct the agent to:

1. Check prerequisite (docs/magic/ exists, CLAUDE.md mentions Magic Docs)
2. Discover all magic docs (two-pass: glob + grep)
3. For each doc, run mechanical checks:
   - Every file path mentioned → verify it exists on disk
   - Every function/method name mentioned → grep for its definition
   - Every directory mentioned → verify it exists
   - Check git log for referenced files — if heavily modified since doc was last updated, flag for review
4. Produce a staleness report (what's stale, severity, which doc)
5. Fix simple issues directly (dead links where the file was clearly renamed — grep for the filename)
6. Flag complex issues for human review (wrong architectural claims, ambiguous references)
7. Report what was fixed and what needs attention

Key design decisions for the skill:
- Detection is mechanical (file existence, grep) — don't rely on the LLM to "reason about" whether content is stale
- Explicit instructions to check EVERY file path and function name, not just scan and guess
- Distinguish between "fix it" (dead links, simple renames) and "flag it" (wrong claims that need human judgment)

- [ ] **Step 2: Run GREEN test**

Spawn a Sonnet subagent with the skill loaded, pointed at ~/Projects/social with the corrupted magic docs. The prompt should include the full skill content.

- [ ] **Step 3: Review GREEN results**

Check same criteria as RED:
- Did it detect all 4 corruptions?
- Did it fix simple ones (dead file, dead function) and flag complex ones (wrong claim)?
- Any false positives?
- Did it use mechanical checks (file existence, grep) not just reasoning?

- [ ] **Step 4: Record GREEN results in TESTING.md**

Update TESTING.md with GREEN scores. Compare to RED baseline.

- [ ] **Step 5: Revert social and commit to airbender**

```bash
cd /Users/juno/Projects/social && git checkout -- .
cd /Users/juno/Projects/airbender
git add skills/prune-magicdocs/SKILL.md skills/prune-magicdocs/TESTING.md
git commit -m "feat: add /prune-magicdocs skill — GREEN passes"
```

---

### Task 3: REFACTOR — Close Loopholes (if needed)

If GREEN missed any corruptions or had false positives, iterate.

**Files:**
- Modify: `skills/prune-magicdocs/SKILL.md`
- Modify: `skills/prune-magicdocs/TESTING.md`

- [ ] **Step 1: Analyze GREEN failures**

For each missed corruption, identify why:
- Did the skill not instruct the agent to check that type of issue?
- Did the agent skip the check despite instructions?
- Was the check ambiguous?

- [ ] **Step 2: Update SKILL.md**

Fix the skill to address specific failures. Keep changes minimal.

- [ ] **Step 3: Re-inject corruptions and re-test**

Re-corrupt social's magic docs (same corruptions), run the updated skill, verify the failures are fixed without introducing regressions.

- [ ] **Step 4: Record REFACTOR results and commit**

Update TESTING.md with REFACTOR scores. Commit to airbender.

---

### Task 4: Clean Up

- [ ] **Step 1: Revert social repo to clean state**

```bash
cd /Users/juno/Projects/social && git checkout -- . && rm -rf docs/magic/ .claude/ && git clean -fd docs/ .claude/
```

- [ ] **Step 2: Final commit**

```bash
cd /Users/juno/Projects/airbender
git add skills/prune-magicdocs/
git commit -m "docs: prune-magicdocs skill complete — final TESTING.md"
```

"""Tests for prompt modification history analysis."""

import json
import unittest
from pathlib import Path

from prompt_history import (
    get_prompt_modification_counts,
    get_prompt_lifespan,
    get_prompt_details,
    PromptInfo,
)


PROMPTS_REPO = Path.home() / "Projects" / "claude-code-system-prompts"


class TestPromptModificationCounts(unittest.TestCase):
    """Count how many commits touched each prompt file."""

    def test_returns_dict_of_filename_to_count(self) -> None:
        result = get_prompt_modification_counts(PROMPTS_REPO)
        self.assertIsInstance(result, dict)
        self.assertGreater(len(result), 0)
        for filename, count in result.items():
            self.assertIsInstance(filename, str)
            self.assertIsInstance(count, int)
            self.assertGreaterEqual(count, 0)

    def test_includes_known_prompts(self) -> None:
        result = get_prompt_modification_counts(PROMPTS_REPO)
        # These should exist in the repo (or have existed)
        all_names = set(result.keys())
        # At least some agent prompts should be present
        agent_prompts = [n for n in all_names if n.startswith("agent-prompt-")]
        self.assertGreater(len(agent_prompts), 5)

    def test_counts_are_plausible(self) -> None:
        """Most-modified prompts should have more commits than least-modified."""
        result = get_prompt_modification_counts(PROMPTS_REPO)
        counts = sorted(result.values())
        # There should be variation — not all the same count
        self.assertGreater(counts[-1], counts[0])

    def test_excludes_batch_commits(self) -> None:
        """Commits that touch many files at once (repo setup, batch metadata)
        should be excluded — they don't represent Anthropic iterating on a prompt."""
        result = get_prompt_modification_counts(PROMPTS_REPO)
        # MagicDocs was never modified by Anthropic — only touched by
        # repo setup commits and a batch metadata addition.
        # With batch filtering, it should have 0 content modifications.
        magicdocs = result.get("agent-prompt-update-magic-docs.md", 0)
        self.assertEqual(magicdocs, 0)

    def test_counts_dont_go_below_zero(self) -> None:
        """Filtering should never produce negative counts."""
        result = get_prompt_modification_counts(PROMPTS_REPO)
        for filename, count in result.items():
            self.assertGreaterEqual(count, 0, f"{filename} has negative count")


class TestPromptLifespan(unittest.TestCase):
    """Track when prompts were created and removed."""

    def test_returns_first_and_last_seen(self) -> None:
        result = get_prompt_lifespan(PROMPTS_REPO)
        self.assertIsInstance(result, dict)
        for filename, info in result.items():
            self.assertIsInstance(info, PromptInfo)
            self.assertIsNotNone(info.first_seen)
            self.assertIsNotNone(info.last_seen)
            self.assertIsNotNone(info.modification_count)

    def test_removed_prompts_have_removed_flag(self) -> None:
        """Prompts that no longer exist should be marked as removed."""
        result = get_prompt_lifespan(PROMPTS_REPO)
        # MagicDocs was removed — should be flagged
        magic_docs = result.get("agent-prompt-update-magic-docs.md")
        if magic_docs:
            self.assertTrue(magic_docs.removed)

    def test_active_prompts_not_removed(self) -> None:
        """Prompts currently in the repo should not be flagged as removed."""
        result = get_prompt_lifespan(PROMPTS_REPO)
        # Pick a prompt we know exists
        current_files = set(
            f.name for f in (PROMPTS_REPO / "system-prompts").iterdir()
            if f.suffix == ".md"
        )
        for filename in list(current_files)[:5]:
            info = result.get(filename)
            if info:
                self.assertFalse(info.removed, f"{filename} should not be removed")


class TestPromptDetails(unittest.TestCase):
    """Get detailed history for a specific prompt."""

    def test_returns_commit_dates(self) -> None:
        result = get_prompt_details(PROMPTS_REPO, "agent-prompt-update-magic-docs.md")
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        for entry in result:
            self.assertIn("date", entry)
            self.assertIn("version", entry)


class TestOutputFormat(unittest.TestCase):
    """The script should produce a JSON report when run directly."""

    def test_cli_produces_json(self) -> None:
        import subprocess
        result = subprocess.run(
            ["python3", str(Path(__file__).parent / "prompt_history.py"),
             str(PROMPTS_REPO)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        self.assertEqual(result.returncode, 0)
        data = json.loads(result.stdout)
        self.assertIn("prompts", data)
        self.assertIsInstance(data["prompts"], list)
        self.assertGreater(len(data["prompts"]), 0)


if __name__ == "__main__":
    unittest.main()

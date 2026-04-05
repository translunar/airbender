"""Tests for TDD cost estimation model.

Models the cost of running RED/GREEN/REFACTOR cycles for CLAUDE.md
instructions vs skill instructions, accounting for prompt caching
and context position.
"""

import unittest

from tdd_cost_model import (
    ModelPricing,
    ContextProfile,
    CacheProfile,
    estimate_cycle_cost,
    generate_report,
    HAIKU,
    SONNET,
    OPUS,
)


class TestModelPricing(unittest.TestCase):
    """Verify pricing constants match Anthropic's published rates."""

    def test_haiku_pricing(self) -> None:
        self.assertAlmostEqual(HAIKU.input_per_token, 1.00 / 1_000_000)
        self.assertAlmostEqual(HAIKU.output_per_token, 5.00 / 1_000_000)

    def test_sonnet_pricing(self) -> None:
        self.assertAlmostEqual(SONNET.input_per_token, 3.00 / 1_000_000)
        self.assertAlmostEqual(SONNET.output_per_token, 15.00 / 1_000_000)

    def test_opus_pricing(self) -> None:
        self.assertAlmostEqual(OPUS.input_per_token, 5.00 / 1_000_000)
        self.assertAlmostEqual(OPUS.output_per_token, 25.00 / 1_000_000)


class TestContextProfile(unittest.TestCase):
    """Context profiles for different TDD scenarios."""

    def test_skill_tdd_is_small_context(self) -> None:
        """Skill TDD uses fresh subagents with minimal context."""
        profile = ContextProfile.skill_tdd()
        self.assertLessEqual(profile.total_input_tokens, 20_000)

    def test_claudemd_fresh_context(self) -> None:
        """CLAUDE.md TDD with fresh conversation — just system prompt."""
        profile = ContextProfile.claudemd_tdd(conversation_fill=0.0)
        # System prompt (~10K) + CLAUDE.md (~2K) + test prompt (~1K)
        self.assertGreater(profile.total_input_tokens, 10_000)
        self.assertLess(profile.total_input_tokens, 30_000)

    def test_claudemd_full_context(self) -> None:
        """CLAUDE.md TDD with 93% full context — the realistic worst case."""
        profile = ContextProfile.claudemd_tdd(conversation_fill=0.93)
        # 200K * 0.93 = ~186K tokens
        self.assertGreater(profile.total_input_tokens, 180_000)
        self.assertLess(profile.total_input_tokens, 200_000)

    def test_cacheable_tokens_for_claudemd(self) -> None:
        """When testing CLAUDE.md changes, sections 1-8 are cacheable.
        Section 9 (CLAUDE.md) changes each iteration, so it and everything
        after it (section 10 + conversation) cannot be cached."""
        profile = ContextProfile.claudemd_tdd(conversation_fill=0.93)
        # Sections 1-8 are roughly 8-10K tokens
        self.assertGreater(profile.cacheable_tokens, 5_000)
        self.assertLess(profile.cacheable_tokens, 15_000)
        # The rest is uncacheable
        self.assertGreater(profile.uncacheable_tokens, 170_000)

    def test_cacheable_tokens_for_skill(self) -> None:
        """Skill TDD: subagent gets system prompt (cacheable) + task prompt."""
        profile = ContextProfile.skill_tdd()
        self.assertGreater(profile.cacheable_tokens, 0)


class TestCycleCosting(unittest.TestCase):
    """One RED/GREEN/REFACTOR cycle = 3 API calls."""

    def test_cycle_has_three_calls(self) -> None:
        """RED, GREEN, REFACTOR = 3 calls."""
        result = estimate_cycle_cost(SONNET, ContextProfile.skill_tdd())
        self.assertEqual(result.num_calls, 3)

    def test_skill_tdd_cheaper_than_claudemd_full_context(self) -> None:
        """The core claim: skill TDD is dramatically cheaper."""
        skill_cost = estimate_cycle_cost(SONNET, ContextProfile.skill_tdd())
        claudemd_cost = estimate_cycle_cost(
            SONNET, ContextProfile.claudemd_tdd(conversation_fill=0.93),
        )
        self.assertGreater(claudemd_cost.total_cost, skill_cost.total_cost * 5)

    def test_full_context_haiku_more_expensive_than_skill_opus(self) -> None:
        """The striking comparison from the blog post."""
        haiku_full = estimate_cycle_cost(
            HAIKU, ContextProfile.claudemd_tdd(conversation_fill=0.93),
        )
        opus_skill = estimate_cycle_cost(OPUS, ContextProfile.skill_tdd())
        self.assertGreater(haiku_full.total_cost, opus_skill.total_cost)

    def test_caching_reduces_cost(self) -> None:
        """Prompt caching should reduce cost vs no caching."""
        no_cache = estimate_cycle_cost(
            SONNET,
            ContextProfile.claudemd_tdd(conversation_fill=0.93),
            cache=CacheProfile.none(),
        )
        with_cache = estimate_cycle_cost(
            SONNET,
            ContextProfile.claudemd_tdd(conversation_fill=0.93),
            cache=CacheProfile.five_minute(),
        )
        self.assertLess(with_cache.total_cost, no_cache.total_cost)

    def test_caching_limited_benefit_for_claudemd_changes(self) -> None:
        """When testing CLAUDE.md changes, only sections 1-8 cache.
        The conversation (bulk of tokens) doesn't cache because it follows
        the changed section. So caching helps, but not dramatically."""
        no_cache = estimate_cycle_cost(
            SONNET,
            ContextProfile.claudemd_tdd(conversation_fill=0.93),
            cache=CacheProfile.none(),
        )
        with_cache = estimate_cycle_cost(
            SONNET,
            ContextProfile.claudemd_tdd(conversation_fill=0.93),
            cache=CacheProfile.five_minute(),
        )
        # Caching should save less than 20% here because only ~10K of ~190K
        # tokens are cacheable
        savings_pct = 1.0 - (with_cache.total_cost / no_cache.total_cost)
        self.assertLess(savings_pct, 0.20)

    def test_output_tokens_same_across_scenarios(self) -> None:
        """Output tokens are similar regardless of input context size."""
        skill = estimate_cycle_cost(SONNET, ContextProfile.skill_tdd())
        full = estimate_cycle_cost(
            SONNET, ContextProfile.claudemd_tdd(conversation_fill=0.93),
        )
        self.assertEqual(skill.output_tokens_per_call, full.output_tokens_per_call)


class TestCostReport(unittest.TestCase):
    """The script should produce a readable comparison table."""

    def test_report_includes_all_models(self) -> None:
        report = generate_report()
        self.assertIn("Haiku", report)
        self.assertIn("Sonnet", report)
        self.assertIn("Opus", report)

    def test_report_includes_both_scenarios(self) -> None:
        report = generate_report()
        self.assertIn("Skill", report)
        self.assertIn("CLAUDE.md", report)

    def test_report_includes_caching(self) -> None:
        report = generate_report()
        self.assertIn("cache", report.lower())


if __name__ == "__main__":
    unittest.main()

"""Cost model for TDD cycles: CLAUDE.md vs skill-based testing.

Models the real cost of running RED/GREEN/REFACTOR cycles, accounting
for context size, prompt caching, and where the changed instruction
sits in the prompt pipeline.

Pricing source: https://platform.claude.com/docs/en/about-claude/pricing
"""

from dataclasses import dataclass


# --- Prompt structure constants (from claw-code prompt.rs) ---

# Sections 1-5: Anthropic's static behavioral instructions (above dynamic boundary)
# Roughly 8,000 tokens based on extracted prompt lengths
SECTIONS_1_THROUGH_5_TOKENS: int = 8_000

# Sections 6-8: Dynamic boundary, environment, project context
# Roughly 1,500 tokens (model name, cwd, date, git status)
SECTIONS_6_THROUGH_8_TOKENS: int = 1_500

# Section 9: CLAUDE.md files — varies, but typical project is ~1-3K
CLAUDEMD_TOKENS: int = 2_000

# Section 10: Runtime config (settings.json) — usually small
RUNTIME_CONFIG_TOKENS: int = 500

# Total system prompt (no conversation)
SYSTEM_PROMPT_TOKENS: int = (
    SECTIONS_1_THROUGH_5_TOKENS
    + SECTIONS_6_THROUGH_8_TOKENS
    + CLAUDEMD_TOKENS
    + RUNTIME_CONFIG_TOKENS
)

# Skill TDD subagent: system prompt + task briefing + test scenario
SKILL_SUBAGENT_INPUT_TOKENS: int = 15_000

# Output tokens per call (response with test results or implementation)
OUTPUT_TOKENS_PER_CALL: int = 2_000

# Context window size
MAX_CONTEXT_TOKENS: int = 200_000

# Number of API calls per RED/GREEN/REFACTOR cycle
CALLS_PER_CYCLE: int = 3


@dataclass(frozen=True)
class ModelPricing:
    name: str
    input_per_token: float
    output_per_token: float


HAIKU = ModelPricing(
    name="Haiku 4.5",
    input_per_token=1.00 / 1_000_000,
    output_per_token=5.00 / 1_000_000,
)

SONNET = ModelPricing(
    name="Sonnet 4.6",
    input_per_token=3.00 / 1_000_000,
    output_per_token=15.00 / 1_000_000,
)

OPUS = ModelPricing(
    name="Opus 4.6",
    input_per_token=5.00 / 1_000_000,
    output_per_token=25.00 / 1_000_000,
)

ALL_MODELS: list[ModelPricing] = [HAIKU, SONNET, OPUS]


@dataclass(frozen=True)
class CacheProfile:
    """Prompt caching parameters."""
    write_multiplier: float  # multiplier on base input price for cache write
    read_multiplier: float   # multiplier on base input price for cache read
    enabled: bool

    @staticmethod
    def none() -> "CacheProfile":
        return CacheProfile(write_multiplier=1.0, read_multiplier=1.0, enabled=False)

    @staticmethod
    def five_minute() -> "CacheProfile":
        return CacheProfile(write_multiplier=1.25, read_multiplier=0.10, enabled=True)

    @staticmethod
    def one_hour() -> "CacheProfile":
        return CacheProfile(write_multiplier=2.00, read_multiplier=0.10, enabled=True)


@dataclass(frozen=True)
class ContextProfile:
    """Describes the token distribution for a TDD scenario."""
    total_input_tokens: int
    cacheable_tokens: int
    uncacheable_tokens: int

    @staticmethod
    def skill_tdd() -> "ContextProfile":
        """Fresh subagent with minimal context."""
        # Subagent gets its own system prompt (cacheable across calls)
        # plus the task-specific prompt (uncacheable)
        cacheable = SECTIONS_1_THROUGH_5_TOKENS  # anthropic's static instructions
        uncacheable = SKILL_SUBAGENT_INPUT_TOKENS - cacheable
        return ContextProfile(
            total_input_tokens=SKILL_SUBAGENT_INPUT_TOKENS,
            cacheable_tokens=cacheable,
            uncacheable_tokens=uncacheable,
        )

    @staticmethod
    def claudemd_tdd(conversation_fill: float = 0.0) -> "ContextProfile":
        """Main session context with conversation history.

        When testing CLAUDE.md changes, sections 1-8 are stable (cacheable).
        Section 9 (CLAUDE.md itself) changes each iteration, which
        invalidates the cache for everything from section 9 onward —
        including section 10 and the entire conversation history.
        """
        conversation_tokens = int(MAX_CONTEXT_TOKENS * conversation_fill)
        total = SYSTEM_PROMPT_TOKENS + conversation_tokens

        # Only sections 1-8 are cacheable (before the CLAUDE.md we're changing)
        cacheable = SECTIONS_1_THROUGH_5_TOKENS + SECTIONS_6_THROUGH_8_TOKENS
        uncacheable = total - cacheable

        return ContextProfile(
            total_input_tokens=total,
            cacheable_tokens=cacheable,
            uncacheable_tokens=uncacheable,
        )


@dataclass(frozen=True)
class CycleCostResult:
    """Cost breakdown for one RED/GREEN/REFACTOR cycle."""
    model: str
    scenario: str
    num_calls: int
    input_tokens_per_call: int
    output_tokens_per_call: int
    cost_per_call: float
    total_cost: float
    cached_savings: float


def estimate_cycle_cost(
    model: ModelPricing,
    context: ContextProfile,
    cache: CacheProfile | None = None,
    scenario_name: str = "",
) -> CycleCostResult:
    """Estimate cost of one RED/GREEN/REFACTOR cycle (3 API calls)."""
    if cache is None:
        cache = CacheProfile.none()

    if cache.enabled:
        # First call: cache write (pay write multiplier on cacheable tokens)
        # Subsequent calls: cache read (pay read multiplier on cacheable tokens)
        # Uncacheable tokens always pay full price
        first_call_input_cost = (
            context.cacheable_tokens * model.input_per_token * cache.write_multiplier
            + context.uncacheable_tokens * model.input_per_token
        )
        subsequent_call_input_cost = (
            context.cacheable_tokens * model.input_per_token * cache.read_multiplier
            + context.uncacheable_tokens * model.input_per_token
        )
        total_input_cost = first_call_input_cost + subsequent_call_input_cost * (CALLS_PER_CYCLE - 1)
    else:
        per_call_input_cost = context.total_input_tokens * model.input_per_token
        total_input_cost = per_call_input_cost * CALLS_PER_CYCLE

    total_output_cost = OUTPUT_TOKENS_PER_CALL * model.output_per_token * CALLS_PER_CYCLE

    total_cost = total_input_cost + total_output_cost

    # Calculate savings vs no caching
    no_cache_input = context.total_input_tokens * model.input_per_token * CALLS_PER_CYCLE
    no_cache_total = no_cache_input + total_output_cost
    savings = no_cache_total - total_cost

    return CycleCostResult(
        model=model.name,
        scenario=scenario_name,
        num_calls=CALLS_PER_CYCLE,
        input_tokens_per_call=context.total_input_tokens,
        output_tokens_per_call=OUTPUT_TOKENS_PER_CALL,
        cost_per_call=total_cost / CALLS_PER_CYCLE,
        total_cost=total_cost,
        cached_savings=savings,
    )


def generate_report() -> str:
    """Generate a comparison table of TDD costs across models and scenarios."""
    lines: list[str] = []
    lines.append("# TDD Cost Comparison: CLAUDE.md vs Skill-Based Testing")
    lines.append("")
    lines.append("One RED/GREEN/REFACTOR cycle = 3 API calls")
    lines.append(f"Output tokens per call: {OUTPUT_TOKENS_PER_CALL:,}")
    lines.append("")

    # Header
    lines.append(f"{'Scenario':<40} {'Model':<12} {'Input/call':>12} {'Cost/cycle':>12} {'Cache savings':>14}")
    lines.append("-" * 92)

    scenarios: list[tuple[str, ContextProfile, CacheProfile | None]] = [
        ("Skill TDD (fresh subagent)", ContextProfile.skill_tdd(), None),
        ("CLAUDE.md TDD (fresh conversation)", ContextProfile.claudemd_tdd(0.0), None),
        ("CLAUDE.md TDD (93% full context)", ContextProfile.claudemd_tdd(0.93), None),
        ("CLAUDE.md TDD (93% full, 5min cache)", ContextProfile.claudemd_tdd(0.93), CacheProfile.five_minute()),
    ]

    for model in ALL_MODELS:
        for scenario_name, context, cache in scenarios:
            result = estimate_cycle_cost(model, context, cache, scenario_name)
            cache_str = f"${result.cached_savings:.2f}" if result.cached_savings > 0.001 else "—"
            lines.append(
                f"{scenario_name:<40} {model.name:<12} {result.input_tokens_per_call:>10,}  ${result.total_cost:>9.4f}  {cache_str:>13}"
            )
        lines.append("")

    # Key comparisons
    lines.append("## Key Comparisons")
    lines.append("")

    haiku_full = estimate_cycle_cost(HAIKU, ContextProfile.claudemd_tdd(0.93))
    opus_skill = estimate_cycle_cost(OPUS, ContextProfile.skill_tdd())
    lines.append(f"Full-context Haiku:  ${haiku_full.total_cost:.4f}/cycle")
    lines.append(f"Skill-based Opus:   ${opus_skill.total_cost:.4f}/cycle")
    lines.append(f"→ Full-context Haiku costs {haiku_full.total_cost / opus_skill.total_cost:.1f}x more than skill-based Opus")
    lines.append("")

    sonnet_full = estimate_cycle_cost(SONNET, ContextProfile.claudemd_tdd(0.93))
    sonnet_skill = estimate_cycle_cost(SONNET, ContextProfile.skill_tdd())
    lines.append(f"Sonnet full-context: ${sonnet_full.total_cost:.4f}/cycle")
    lines.append(f"Sonnet skill-based:  ${sonnet_skill.total_cost:.4f}/cycle")
    lines.append(f"→ {sonnet_full.total_cost / sonnet_skill.total_cost:.1f}x ratio")
    lines.append("")

    # Caching impact
    sonnet_cached = estimate_cycle_cost(
        SONNET, ContextProfile.claudemd_tdd(0.93), CacheProfile.five_minute(),
    )
    lines.append("## Prompt Caching Impact (CLAUDE.md changes)")
    lines.append("")
    lines.append(f"When testing CLAUDE.md changes, only sections 1-8 of the system prompt")
    lines.append(f"are cacheable ({SECTIONS_1_THROUGH_5_TOKENS + SECTIONS_6_THROUGH_8_TOKENS:,} tokens).")
    lines.append(f"Section 9 (CLAUDE.md) changes each iteration, invalidating the cache")
    lines.append(f"for everything after it — including the conversation ({int(MAX_CONTEXT_TOKENS * 0.93):,} tokens).")
    lines.append("")
    lines.append(f"Sonnet without cache: ${sonnet_full.total_cost:.4f}")
    lines.append(f"Sonnet with 5min cache: ${sonnet_cached.total_cost:.4f}")
    lines.append(f"Savings: ${sonnet_cached.cached_savings:.4f} ({sonnet_cached.cached_savings / sonnet_full.total_cost * 100:.1f}%)")
    lines.append(f"→ Caching helps minimally because only {SECTIONS_1_THROUGH_5_TOKENS + SECTIONS_6_THROUGH_8_TOKENS:,} of {ContextProfile.claudemd_tdd(0.93).total_input_tokens:,} tokens are cacheable")

    return "\n".join(lines)


if __name__ == "__main__":
    print(generate_report())

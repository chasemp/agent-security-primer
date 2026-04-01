"""Tests for the live token counter.

The token counter is the audience's "speedometer" — it shows tokens consumed
and estimated cost after every API call. It's the most visible shared component:

  - Demo 3 (Death Spiral): counter climbs as the agent retries a broken tool
  - Demo 5 (Error Translation): two counters diverge side-by-side
  - Every demo: running cost in the corner so the audience sees real spend

We test the math (token accumulation, cost calculation) and the Rich
renderable output (what the audience actually sees on screen).
"""

import pytest
from rich.console import Console

from shared.models import HAIKU, OPUS, SONNET
from shared.token_counter import TokenCounter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_usage(
    input_tokens: int = 0,
    output_tokens: int = 0,
    cache_read: int = 0,
    cache_creation: int = 0,
) -> dict:
    """Build a usage dict matching the shape of response.usage from the API.

    The Anthropic API returns usage as an object with these fields.
    We use plain dicts in tests to avoid importing SDK types.
    """
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_read_input_tokens": cache_read,
        "cache_creation_input_tokens": cache_creation,
    }


# ---------------------------------------------------------------------------
# Token accumulation
# ---------------------------------------------------------------------------

class TestTokenAccumulation:
    """The counter must keep running totals across multiple API calls."""

    def test_initial_state_is_zero(self) -> None:
        counter = TokenCounter(model=HAIKU)
        assert counter.total_input == 0
        assert counter.total_output == 0

    def test_single_update(self) -> None:
        counter = TokenCounter(model=HAIKU)
        counter.update(_make_usage(input_tokens=100, output_tokens=50))
        assert counter.total_input == 100
        assert counter.total_output == 50

    def test_multiple_updates_accumulate(self) -> None:
        """Each API call adds to the running total — tokens don't reset."""
        counter = TokenCounter(model=HAIKU)
        counter.update(_make_usage(input_tokens=100, output_tokens=50))
        counter.update(_make_usage(input_tokens=200, output_tokens=75))
        assert counter.total_input == 300
        assert counter.total_output == 125

    def test_cache_tokens_tracked_separately(self) -> None:
        """Cache hits reduce cost but we still track them for visibility."""
        counter = TokenCounter(model=HAIKU)
        counter.update(_make_usage(
            input_tokens=500,
            output_tokens=100,
            cache_read=300,
            cache_creation=50,
        ))
        assert counter.total_cache_read == 300
        assert counter.total_cache_creation == 50


# ---------------------------------------------------------------------------
# Cost calculation
# ---------------------------------------------------------------------------

class TestCostCalculation:
    """Cost = (input_tokens * input_price + output_tokens * output_price) / 1M.

    The audience sees this as a dollar amount updating in real time.
    Getting the math wrong would undermine the "credit card on a while loop"
    message in Demo 3.
    """

    def test_zero_tokens_zero_cost(self) -> None:
        counter = TokenCounter(model=HAIKU)
        assert counter.cost_usd == pytest.approx(0.0)

    def test_haiku_cost(self) -> None:
        """Haiku: $1/1M input, $5/1M output.
        1000 input tokens = $0.001, 500 output tokens = $0.0025.
        Total = $0.0035."""
        counter = TokenCounter(model=HAIKU)
        counter.update(_make_usage(input_tokens=1000, output_tokens=500))
        assert counter.cost_usd == pytest.approx(0.0035)

    def test_sonnet_cost(self) -> None:
        """Sonnet: $3/1M input, $15/1M output."""
        counter = TokenCounter(model=SONNET)
        counter.update(_make_usage(input_tokens=1000, output_tokens=500))
        expected = (1000 * 3.00 + 500 * 15.00) / 1_000_000
        assert counter.cost_usd == pytest.approx(expected)

    def test_opus_cost(self) -> None:
        """Opus: $5/1M input, $25/1M output.
        Used in the GoPro demo — most expensive per call."""
        counter = TokenCounter(model=OPUS)
        counter.update(_make_usage(input_tokens=1000, output_tokens=500))
        expected = (1000 * 5.00 + 500 * 25.00) / 1_000_000
        assert counter.cost_usd == pytest.approx(expected)

    def test_cost_accumulates_across_updates(self) -> None:
        counter = TokenCounter(model=HAIKU)
        counter.update(_make_usage(input_tokens=1000, output_tokens=500))
        counter.update(_make_usage(input_tokens=1000, output_tokens=500))
        assert counter.cost_usd == pytest.approx(0.007)


# ---------------------------------------------------------------------------
# Rich renderable output
# ---------------------------------------------------------------------------

class TestRenderable:
    """The counter renders as a Rich panel showing tokens and cost.

    We capture the console output to a string and verify the structure.
    The exact formatting may change, but the data must be present.
    """

    def test_renders_without_error(self) -> None:
        counter = TokenCounter(model=HAIKU)
        console = Console(file=None, force_terminal=True, width=80)
        # __rich_console__ protocol — Rich knows how to render it
        with console.capture() as capture:
            console.print(counter)
        output = capture.get()
        assert len(output) > 0

    def test_shows_token_counts(self) -> None:
        counter = TokenCounter(model=HAIKU)
        counter.update(_make_usage(input_tokens=1234, output_tokens=567))
        console = Console(file=None, force_terminal=True, width=80)
        with console.capture() as capture:
            console.print(counter)
        output = capture.get()
        assert "1,234" in output or "1234" in output
        assert "567" in output

    def test_shows_cost(self) -> None:
        counter = TokenCounter(model=HAIKU)
        counter.update(_make_usage(input_tokens=1000, output_tokens=500))
        console = Console(file=None, force_terminal=True, width=80)
        with console.capture() as capture:
            console.print(counter)
        output = capture.get()
        # Cost should appear as a dollar amount
        assert "$" in output


class TestReset:
    """Support resetting for demos that run multiple comparisons."""

    def test_reset_clears_all(self) -> None:
        counter = TokenCounter(model=HAIKU)
        counter.update(_make_usage(input_tokens=100, output_tokens=50))
        counter.reset()
        assert counter.total_input == 0
        assert counter.total_output == 0
        assert counter.cost_usd == pytest.approx(0.0)

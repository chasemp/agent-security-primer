"""Tests for shared model constants and pricing.

These tests verify the constants that every demo imports. Getting a model ID
or price wrong would silently break cost displays across the entire suite,
so we pin the expected values here.
"""

from shared.models import (
    DEFAULT_DEMO_MODEL,
    HAIKU,
    OPUS,
    PRICING,
    SONNET,
)


class TestModelIds:
    """Model IDs must match the Anthropic API's expected format."""

    def test_haiku_id(self) -> None:
        assert HAIKU == "claude-haiku-4-5"

    def test_sonnet_id(self) -> None:
        assert SONNET == "claude-sonnet-4-6"

    def test_opus_id(self) -> None:
        assert OPUS == "claude-opus-4-6"

    def test_default_is_haiku(self) -> None:
        """Haiku is the default because it's cheapest ($1/$5 per 1M tokens).
        All 10 demos cost under $1 total at Haiku pricing."""
        assert DEFAULT_DEMO_MODEL == HAIKU


class TestPricing:
    """Pricing per 1M tokens. Used by the token counter to show live cost."""

    def test_all_models_have_pricing(self) -> None:
        for model_id in (HAIKU, SONNET, OPUS):
            assert model_id in PRICING, f"Missing pricing for {model_id}"

    def test_pricing_has_input_and_output(self) -> None:
        for model_id, prices in PRICING.items():
            assert "input" in prices, f"{model_id} missing input price"
            assert "output" in prices, f"{model_id} missing output price"

    def test_haiku_pricing(self) -> None:
        assert PRICING[HAIKU] == {"input": 1.00, "output": 5.00}

    def test_sonnet_pricing(self) -> None:
        assert PRICING[SONNET] == {"input": 3.00, "output": 15.00}

    def test_opus_pricing(self) -> None:
        assert PRICING[OPUS] == {"input": 5.00, "output": 25.00}

    def test_no_extra_models(self) -> None:
        """Only the three models we use should have pricing entries.
        This prevents stale entries from accumulating."""
        assert set(PRICING.keys()) == {HAIKU, SONNET, OPUS}

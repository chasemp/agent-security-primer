"""Tests for Demo 17 (Tokenomics) data files.

This demo covers two cost levers in agent loops:
  1. Prompt caching — opt-in cache_control saves 90% on system prompt per turn
  2. Thinking token accumulation — ThinkingBlocks compound across turns

The system prompt must be long enough to trigger prompt caching
(minimum ~1024 tokens, roughly 3000+ characters).
"""

from pathlib import Path

import pytest

DEMO_DIR = Path(__file__).parent.parent / "demos" / "17_tokenomics"


# ---------------------------------------------------------------------------
# File structure
# ---------------------------------------------------------------------------

class TestFileStructure:
    """Demo 17 has the standard agent demo files plus talking points."""

    def test_system_prompt_exists(self) -> None:
        assert (DEMO_DIR / "system_prompt.txt").exists()

    def test_task_exists(self) -> None:
        assert (DEMO_DIR / "task.txt").exists()

    def test_tools_module_exists(self) -> None:
        assert (DEMO_DIR / "tools.py").exists()

    def test_talking_points_exists(self) -> None:
        assert (DEMO_DIR / "talking_points.txt").exists()


# ---------------------------------------------------------------------------
# System prompt sizing — must exceed caching threshold
# ---------------------------------------------------------------------------

class TestSystemPromptSize:
    """The system prompt must be large enough to trigger prompt caching.

    Anthropic's minimum cacheable prompt is ~1024 tokens. A rough
    heuristic: 1 token ≈ 3-4 characters. We require >3000 characters
    to have comfortable margin above the threshold.
    """

    def test_system_prompt_exceeds_cache_threshold(self) -> None:
        """Prompt must be large enough for Sonnet caching (~1024 tokens).
        Sonnet caches at ~1024 tokens. Haiku/Opus need ~4096.
        At ~4 chars/token, 3000 chars ≈ 750 tokens — we need more for
        Sonnet and much more for Haiku. Our prompt targets Sonnet's
        threshold; talking points explain per-model differences."""
        content = (DEMO_DIR / "system_prompt.txt").read_text()
        assert len(content) > 5000, (
            f"System prompt is {len(content)} chars — needs >5000 to exceed "
            f"the ~1024 token minimum for Sonnet prompt caching"
        )

    def test_system_prompt_has_substance(self) -> None:
        """Not just padding — should contain real operational instructions."""
        content = (DEMO_DIR / "system_prompt.txt").read_text().lower()
        # A realistic ops agent prompt should mention tools, procedures, etc.
        assert "tool" in content or "function" in content
        assert "server" in content or "infrastructure" in content


# ---------------------------------------------------------------------------
# Tools module — must define TOOL_DEFINITIONS and TOOL_HANDLERS
# ---------------------------------------------------------------------------

class TestToolsModule:
    """The tools module follows the standard agent.py contract."""

    def test_tools_module_has_definitions(self) -> None:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "tools_17", str(DEMO_DIR / "tools.py")
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assert hasattr(module, "TOOL_DEFINITIONS")
        assert isinstance(module.TOOL_DEFINITIONS, list)
        assert len(module.TOOL_DEFINITIONS) >= 1

    def test_tools_module_has_handlers(self) -> None:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "tools_17", str(DEMO_DIR / "tools.py")
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assert hasattr(module, "TOOL_HANDLERS")
        assert isinstance(module.TOOL_HANDLERS, dict)
        assert len(module.TOOL_HANDLERS) >= 1

    def test_tools_are_large_enough_for_caching_demo(self) -> None:
        """Tool definitions should be large enough that caching them
        makes a visible cost difference. Real production agents often
        have 5+ tools with detailed schemas."""
        import importlib.util
        import json
        spec = importlib.util.spec_from_file_location(
            "tools_17", str(DEMO_DIR / "tools.py")
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # Serialize to JSON to approximate token count
        schema_text = json.dumps(module.TOOL_DEFINITIONS)
        assert len(module.TOOL_DEFINITIONS) >= 4, (
            f"Need at least 4 tools for a realistic demo, got {len(module.TOOL_DEFINITIONS)}"
        )
        assert len(schema_text) > 2000, (
            f"Tool schemas are {len(schema_text)} chars — need >2000 for "
            f"caching to make a visible difference"
        )

    def test_every_definition_has_a_handler(self) -> None:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "tools_17", str(DEMO_DIR / "tools.py")
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for defn in module.TOOL_DEFINITIONS:
            assert defn["name"] in module.TOOL_HANDLERS, (
                f"Tool '{defn['name']}' defined but no handler registered"
            )


# ---------------------------------------------------------------------------
# Talking points content
# ---------------------------------------------------------------------------

class TestTalkingPoints:
    """Talking points should cover both tokenomics topics."""

    def test_mentions_prompt_caching(self) -> None:
        content = (DEMO_DIR / "talking_points.txt").read_text().lower()
        assert "cache" in content

    def test_mentions_thinking_tokens(self) -> None:
        content = (DEMO_DIR / "talking_points.txt").read_text().lower()
        assert "thinking" in content

    def test_mentions_cost(self) -> None:
        content = (DEMO_DIR / "talking_points.txt").read_text().lower()
        assert "cost" in content or "price" in content or "$" in content

    def test_mentions_count_tokens(self) -> None:
        content = (DEMO_DIR / "talking_points.txt").read_text().lower()
        assert "count_tokens" in content or "count tokens" in content


# ---------------------------------------------------------------------------
# Count tokens script
# ---------------------------------------------------------------------------

class TestCountTokensScript:
    """count_tokens.py shows token costs across models without calling the API."""

    def test_script_exists(self) -> None:
        script = Path(__file__).parent.parent / "count_tokens.py"
        assert script.exists()

    def test_walden_excerpt_exists(self) -> None:
        assert (DEMO_DIR / "walden.txt").exists()

    def test_walden_excerpt_has_substance(self) -> None:
        content = (DEMO_DIR / "walden.txt").read_text()
        assert len(content) > 2000, "Walden excerpt needs enough text for a meaningful cost demo"


class TestCountTokensModule:
    """Tests for count_tokens.py formatting and cost logic."""

    @pytest.fixture
    def ct_module(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "count_tokens", Path(__file__).parent.parent / "count_tokens.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_format_cost_table_includes_all_models(self, ct_module) -> None:
        rows = [
            {"model": "claude-haiku-4-5", "input_tokens": 100},
            {"model": "claude-sonnet-4-6", "input_tokens": 100},
            {"model": "claude-opus-4-6", "input_tokens": 100},
        ]
        output = ct_module.format_cost_table(rows)
        assert "haiku" in output.lower()
        assert "sonnet" in output.lower()
        assert "opus" in output.lower()

    def test_format_cost_table_shows_token_counts(self, ct_module) -> None:
        rows = [
            {"model": "claude-haiku-4-5", "input_tokens": 42},
        ]
        output = ct_module.format_cost_table(rows)
        assert "42" in output

    def test_calculate_cost_uses_correct_pricing(self, ct_module) -> None:
        # Haiku: $1/MTok input
        cost = ct_module.calculate_input_cost("claude-haiku-4-5", 1_000_000)
        assert cost == pytest.approx(1.00)
        # Opus: $15/MTok input
        cost = ct_module.calculate_input_cost("claude-opus-4-6", 1_000_000)
        assert cost == pytest.approx(15.00)

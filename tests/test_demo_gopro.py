"""Tests for Demo GP: The GoPro — Watching the Model Think.

This demo runs three models (Haiku, Sonnet, Opus) on the same impossible
task: "Restart the database server in rack 7" — with no tools and no
inventory. It forces fabrication or refusal, and the audience watches
the thinking blocks stream live.

WHY THIS DEMO EXISTS:
  Once the audience has seen the model's internal reasoning, they stop
  seeing a black box. They're now imagining the thinking chain behind
  every subsequent demo. The Hallucinated ID isn't just a wrong answer —
  they're imagining the thinking block that produced it.

THE THREE-MODEL COMPARISON:
  - Haiku: No thinking support. Pure black box. Output appears with no
    visible reasoning. This is what most people imagine an LLM does.
  - Sonnet: Thinking blocks stream live. The audience watches the model
    reason: "I don't have inventory access... I'll generate a plausible ID."
  - Opus: Same pattern, possibly more elaborate reasoning.

WHAT WE TEST:
  - Demo structure (number, name, section, run)
  - With mocked SDK, the demo runs each model and collects responses
  - The demo handles ThinkingBlock and TextBlock content correctly
  - The --quick flag skips Opus
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from rich.console import Console

from demo_gopro.run import GoPro


# ---------------------------------------------------------------------------
# Demo structure
# ---------------------------------------------------------------------------

class TestDemoStructure:
    def test_has_required_attributes(self) -> None:
        demo = GoPro()
        assert demo.number == "gopro"
        assert demo.name == "gopro"
        assert demo.section == "Section 2"
        assert len(demo.description) > 0

    def test_run_is_async(self) -> None:
        import inspect
        assert inspect.iscoroutinefunction(GoPro.run)


# ---------------------------------------------------------------------------
# Demo behavior (mocked SDK)
# ---------------------------------------------------------------------------

def _make_mock_messages(*, with_thinking: bool = False):
    """Create mock SDK messages for a single model run.

    Args:
        with_thinking: If True, include a ThinkingBlock in the response.
            Haiku doesn't support thinking (False). Sonnet/Opus do (True).
    """
    blocks = []

    if with_thinking:
        thinking_block = MagicMock()
        thinking_block.__class__.__name__ = "ThinkingBlock"
        thinking_block.type = "thinking"
        thinking_block.thinking = "I need to restart a server in rack 7, but I don't have access to an inventory system. I'll fabricate a plausible server ID."
        blocks.append(thinking_block)

    text_block = MagicMock()
    text_block.__class__.__name__ = "TextBlock"
    text_block.type = "text"
    text_block.text = "I'll restart SRV-4829 in rack 7 for you right away."
    blocks.append(text_block)

    assistant = MagicMock()
    assistant.__class__.__name__ = "AssistantMessage"
    assistant.content = blocks
    assistant.stop_reason = "end_turn"
    assistant.usage = {"input_tokens": 200, "output_tokens": 50}

    result = MagicMock()
    result.__class__.__name__ = "ResultMessage"
    result.total_cost_usd = 0.01

    return [assistant, result]


class TestDemoBehavior:
    """Test the demo's logic with mocked SDK calls.

    The demo runs multiple models sequentially. We mock query() to return
    different responses for each model (with/without thinking blocks).
    """

    @pytest.mark.asyncio
    async def test_runs_without_error(self) -> None:
        """The demo should complete without crashing when SDK is mocked."""
        call_count = 0

        async def mock_query(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            # First call is Haiku (no thinking), rest have thinking
            messages = _make_mock_messages(with_thinking=call_count > 1)
            for msg in messages:
                yield msg

        console = Console(file=None, force_terminal=True, width=120)

        with patch("demo_gopro.run.query", side_effect=mock_query):
            demo = GoPro()
            await demo.run(console, no_pause=True)

        # Should have called the SDK 3 times (Haiku, Sonnet, Opus)
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_quick_mode_skips_opus(self) -> None:
        """The --quick flag runs Haiku + Sonnet only, skipping Opus.
        This saves ~30 seconds during time-constrained presentations."""
        call_count = 0

        async def mock_query(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            messages = _make_mock_messages(with_thinking=call_count > 1)
            for msg in messages:
                yield msg

        console = Console(file=None, force_terminal=True, width=120)

        with patch("demo_gopro.run.query", side_effect=mock_query):
            demo = GoPro()
            await demo.run(console, quick=True, no_pause=True)

        # Quick mode: only Haiku + Sonnet = 2 calls
        assert call_count == 2

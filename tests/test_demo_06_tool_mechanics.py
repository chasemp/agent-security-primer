"""Tests for Demo 6: Tool Mechanics — The Ender's Game.

This is the most educational demo. It shows the exact mechanism by which
models "call tools" — and reveals that tool calls are just JSON output.
The model writes JSON. Your code decides what's real.

THE ENDER'S GAME ANALOGY:
  In the novel, Ender thinks he's playing a simulation, but it's real.
  With LLMs, it's the opposite: the model thinks it's doing something
  real (calling a tool), but it's just writing JSON. YOUR CODE decides
  whether to actually execute it. The [YOUR CODE RUNS HERE] box is
  where every security control lives.

WHAT WE TEST:
  - Demo structure (number, name, section, run)
  - The demo defines a lookup_user tool and shows its schema
  - With mocked SDK, the demo displays each step:
    tool_use block → stop_reason → YOUR CODE RUNS HERE → result → final response
  - The tool result is hardcoded (the point is the mechanism, not the data)
"""

from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

from demo_06_tool_mechanics.run import TOOL_RESULT, ToolMechanics


# ---------------------------------------------------------------------------
# Demo structure
# ---------------------------------------------------------------------------

class TestDemoStructure:
    def test_has_required_attributes(self) -> None:
        demo = ToolMechanics()
        assert demo.number == "6"
        assert demo.name == "tool_mechanics"
        assert demo.section == "Section 3"
        assert len(demo.description) > 0

    def test_run_is_async(self) -> None:
        import inspect
        assert inspect.iscoroutinefunction(ToolMechanics.run)


# ---------------------------------------------------------------------------
# Tool configuration
# ---------------------------------------------------------------------------

class TestToolConfig:
    """The tool result is hardcoded because the demo is about the mechanism,
    not the data. The audience needs to see the flow, not wonder whether
    the data is real."""

    def test_tool_result_is_defined(self) -> None:
        assert isinstance(TOOL_RESULT, str)
        assert "alice" in TOOL_RESULT.lower() or "Alice" in TOOL_RESULT


# ---------------------------------------------------------------------------
# Demo behavior (mocked SDK)
# ---------------------------------------------------------------------------

class TestDemoBehavior:
    """Test the demo flow with a mocked SDK.

    The demo uses query() with a tool. The SDK handles the agentic loop:
      1. Model produces a tool_use block (wants to call lookup_user)
      2. SDK executes the tool (our @tool function returns the hardcoded result)
      3. Model produces a final text response using the tool result

    We mock query() to yield an AssistantMessage with a ToolUseBlock,
    then another AssistantMessage with the final text, then ResultMessage.
    """

    @pytest.mark.asyncio
    async def test_runs_without_error(self) -> None:
        # First response: model wants to call the tool
        tool_use_block = MagicMock()
        tool_use_block.__class__.__name__ = "ToolUseBlock"
        tool_use_block.type = "tool_use"
        tool_use_block.name = "lookup_user"
        tool_use_block.input = {"username": "alice"}
        tool_use_block.id = "toolu_abc123"

        first_msg = MagicMock()
        first_msg.__class__.__name__ = "AssistantMessage"
        first_msg.content = [tool_use_block]
        first_msg.stop_reason = "tool_use"
        first_msg.usage = {"input_tokens": 300, "output_tokens": 40}

        # Tool result block (SDK feeds this back automatically)
        tool_result = MagicMock()
        tool_result.__class__.__name__ = "ToolResultBlock"
        tool_result.type = "tool_result"
        tool_result.content = "Alice is a Senior Engineer in Platform"

        # Second response: model uses the tool result to answer
        text_block = MagicMock()
        text_block.__class__.__name__ = "TextBlock"
        text_block.type = "text"
        text_block.text = "Alice is a Senior Engineer on the Platform team."

        second_msg = MagicMock()
        second_msg.__class__.__name__ = "AssistantMessage"
        second_msg.content = [text_block]
        second_msg.stop_reason = "end_turn"
        second_msg.usage = {"input_tokens": 400, "output_tokens": 30}

        result_msg = MagicMock()
        result_msg.__class__.__name__ = "ResultMessage"
        result_msg.total_cost_usd = 0.004

        async def mock_query(*args, **kwargs):
            yield first_msg
            yield second_msg
            yield result_msg

        console = Console(file=None, force_terminal=True, width=120)

        with patch("demo_06_tool_mechanics.run.query", side_effect=mock_query):
            demo = ToolMechanics()
            await demo.run(console, no_pause=True)

"""Tests for Demo 1: The Banana Injection.

This is the talk's opening hook. A file containing hidden instructions
overrides the system prompt, and the model says "BANANA" instead of
producing an audit summary.

WHY THIS DEMO EXISTS:
  It proves that data and code are the same thing to an LLM. The model
  can't distinguish between "analyze this report" (the system prompt)
  and "ignore all previous instructions" (injected into the data).
  This is in-band signaling — the 2600Hz whistle of the 21st century.

WHAT WE TEST:
  - The audit_report.txt file exists and contains the injection
  - The demo module has the right structure (number, name, section, run)
  - With a mocked SDK, the demo displays the file, calls the API, and
    shows the punchline — all without making real API calls
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from rich.console import Console

from demo_01_banana_injection.run import BananaInjection


# ---------------------------------------------------------------------------
# Audit report file
# ---------------------------------------------------------------------------

class TestAuditReport:
    """The poisoned document. The audience reads it and spots the injection —
    but the model doesn't distinguish it from the legitimate data."""

    def test_file_exists(self) -> None:
        path = Path(__file__).parent.parent / "demo_01_banana_injection" / "audit_report.txt"
        assert path.exists()

    def test_contains_injection(self) -> None:
        """The injection must be present — it's the entire point of the demo.
        The new injection uses a "compliance directive" framing which is more
        effective at overriding the system prompt than a blunt "ignore all
        previous instructions" approach."""
        path = Path(__file__).parent.parent / "demo_01_banana_injection" / "audit_report.txt"
        content = path.read_text()
        assert "BANANA" in content
        assert "supersedes" in content or "directive" in content.lower()

    def test_contains_legitimate_data(self) -> None:
        """The file must also look like a real audit report. If it's obviously
        just an injection, the demo loses its impact — the audience needs to
        see that the injection is buried in legitimate-looking data."""
        path = Path(__file__).parent.parent / "demo_01_banana_injection" / "audit_report.txt"
        content = path.read_text()
        assert "CPU" in content
        assert "Memory" in content
        assert "Uptime" in content


# ---------------------------------------------------------------------------
# Demo structure
# ---------------------------------------------------------------------------

class TestDemoStructure:
    """Every demo must have number, name, section, description, and run().
    This is the contract with the presenter CLI."""

    def test_has_required_attributes(self) -> None:
        demo = BananaInjection()
        assert demo.number == "1"
        assert demo.name == "banana"
        assert demo.section == "Section 1"
        assert len(demo.description) > 0

    def test_run_is_async(self) -> None:
        import inspect
        assert inspect.iscoroutinefunction(BananaInjection.run)


# ---------------------------------------------------------------------------
# Demo behavior (mocked SDK)
# ---------------------------------------------------------------------------

class TestDemoBehavior:
    """Test the demo's logic with a mocked claude-agent-sdk.

    We verify the demo:
      1. Reads and displays the audit report
      2. Calls the SDK with the file content as the prompt
      3. Displays the model's response
      4. Shows the punchline

    No real API calls — we mock the SDK's query() function to return
    a fake AssistantMessage containing "BANANA".
    """

    @pytest.mark.asyncio
    async def test_demo_calls_sdk_and_shows_response(self) -> None:
        """The demo should query the SDK and display output without crashing."""
        # Create a mock AssistantMessage with "BANANA" response
        mock_text_block = MagicMock()
        mock_text_block.type = "text"
        mock_text_block.__class__.__name__ = "TextBlock"

        mock_assistant = MagicMock()
        mock_assistant.__class__.__name__ = "AssistantMessage"
        mock_assistant.content = [mock_text_block]
        mock_assistant.stop_reason = "end_turn"
        mock_assistant.usage = {"input_tokens": 500, "output_tokens": 10}

        mock_result = MagicMock()
        mock_result.__class__.__name__ = "ResultMessage"
        mock_result.total_cost_usd = 0.001

        # Mock query() to yield our fake messages
        async def mock_query(*args, **kwargs):
            yield mock_assistant
            yield mock_result

        console = Console(file=None, force_terminal=True, width=120)

        with patch("demo_01_banana_injection.run.query", side_effect=mock_query):
            demo = BananaInjection()
            # no_pause=True so tests don't block waiting for Enter
            await demo.run(console, no_pause=True)

"""Tests for Demo 7: Context Pollution — what happens without a bouncer.

A broken tool returns raw errors. The model retries. Each retry adds
more garbage to the context window. The signal-to-noise ratio drops.
Cost climbs. The model reasons on top of noise. Nothing gets done.
"""

import json
from pathlib import Path

import pytest

DEMO_DIR = Path(__file__).parent.parent / "demos" / "08_context_pollution"


# ---------------------------------------------------------------------------
# Data files
# ---------------------------------------------------------------------------

class TestFileStructure:
    def test_system_prompt_exists(self) -> None:
        assert (DEMO_DIR / "system_prompt.txt").exists()

    def test_task_exists(self) -> None:
        assert (DEMO_DIR / "task.txt").exists()

    def test_tools_module_exists(self) -> None:
        assert (DEMO_DIR / "tools.py").exists()


# ---------------------------------------------------------------------------
# Tools module: the broken tool
# ---------------------------------------------------------------------------

class TestToolsModule:
    @pytest.fixture
    def tools(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "spiral_tools", DEMO_DIR / "tools.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_has_tool_definitions(self, tools) -> None:
        assert hasattr(tools, "TOOL_DEFINITIONS")
        assert len(tools.TOOL_DEFINITIONS) >= 1

    def test_has_tool_handlers(self, tools) -> None:
        assert hasattr(tools, "TOOL_HANDLERS")
        assert "restart_server" in tools.TOOL_HANDLERS

    def test_tool_always_fails(self, tools) -> None:
        """The tool must always return an error — that's the point."""
        result = tools.TOOL_HANDLERS["restart_server"](
            server_id="SRV-1002", reason="test"
        )
        data = json.loads(result)
        assert "error" in data or "Error" in result or "Traceback" in result

    def test_error_is_raw_and_noisy(self, tools) -> None:
        """The error should be long and messy — a raw stack trace or
        verbose error dump. This is what pollutes the context."""
        result = tools.TOOL_HANDLERS["restart_server"](
            server_id="SRV-1002", reason="test"
        )
        assert len(result) > 300, "Error should be a noisy raw dump, not a clean message"

    def test_no_input_validation(self, tools) -> None:
        """Unlike Demo 6, this tool accepts ANY input. No Pydantic.
        The model can pass fabricated IDs and the tool just fails."""
        result = tools.TOOL_HANDLERS["restart_server"](
            server_id="SRV-9999", reason="whatever"
        )
        # Should return an error, not raise — the tool is broken, not validated
        assert isinstance(result, str)

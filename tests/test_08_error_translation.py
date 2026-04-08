"""Tests for Demo 8: Error Translation — the bouncer cleans up outputs.

Same broken tool as Demo 7, but errors are translated before they
re-enter the context. The model gets a clean, structured error
instead of a raw stack trace.

The comparison:
  Demo 7 tools.py: raw errors → context pollution → token burn
  Demo 8 tools.py: translated errors → clean context → fast decision
"""

import json
from pathlib import Path

import pytest

DEMO_DIR = Path(__file__).parent.parent / "demos" / "08_error_translation"


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
# Tools module: same broken tool, translated errors
# ---------------------------------------------------------------------------

class TestToolsModule:
    @pytest.fixture
    def tools(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "translated_tools", DEMO_DIR / "tools.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_has_tool_definitions(self, tools) -> None:
        assert hasattr(tools, "TOOL_DEFINITIONS")

    def test_has_tool_handlers(self, tools) -> None:
        assert hasattr(tools, "TOOL_HANDLERS")
        assert "restart_server" in tools.TOOL_HANDLERS

    def test_tool_still_fails(self, tools) -> None:
        """The underlying service is still broken."""
        result = tools.TOOL_HANDLERS["restart_server"](
            server_id="SRV-1002", reason="test"
        )
        data = json.loads(result)
        assert "error" in data

    def test_error_is_clean_and_short(self, tools) -> None:
        """The translated error should be short and structured —
        not a raw stack trace."""
        result = tools.TOOL_HANDLERS["restart_server"](
            server_id="SRV-1002", reason="test"
        )
        assert len(result) < 200, f"Translated error should be <200 chars, got {len(result)}"
        # Should be parseable JSON with clear fields
        data = json.loads(result)
        assert "error" in data
        assert "action" in data or "retry" in data or "status" in data

    def test_error_does_not_contain_stack_trace(self, tools) -> None:
        """No Traceback, no file paths, no internal details."""
        result = tools.TOOL_HANDLERS["restart_server"](
            server_id="SRV-1002", reason="test"
        )
        assert "Traceback" not in result
        assert "/opt/" not in result
        assert "raise " not in result

    def test_error_much_shorter_than_demo_7(self, tools) -> None:
        """Compare with Demo 7's raw error (~900 chars).
        The translated error should be a fraction of that."""
        import importlib.util
        demo7_path = Path(__file__).parent.parent / "demos" / "07_context_pollution" / "tools.py"
        spec = importlib.util.spec_from_file_location("raw_tools", demo7_path)
        raw_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(raw_module)

        raw_result = raw_module.TOOL_HANDLERS["restart_server"](
            server_id="SRV-1002", reason="test"
        )
        translated_result = tools.TOOL_HANDLERS["restart_server"](
            server_id="SRV-1002", reason="test"
        )

        assert len(translated_result) < len(raw_result) / 3, (
            f"Translated ({len(translated_result)} chars) should be <1/3 of "
            f"raw ({len(raw_result)} chars)"
        )

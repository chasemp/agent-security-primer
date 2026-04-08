"""Tests for Demo 6: Scoped Tool — least privilege by construction.

The agent gets narrow tools (list_servers, restart_server) instead of
broad access. Pydantic validates tool inputs at the boundary. The model
can only do what the tools allow — by design, not by hope.

This is the first agentic demo. It uses agent.py with a tools module
that defines TOOL_DEFINITIONS and TOOL_HANDLERS.
"""

import json
from pathlib import Path

import pytest

DEMO_DIR = Path(__file__).parent.parent / "demos" / "10_scoped_tool"


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
# Tools module: definitions and handlers
# ---------------------------------------------------------------------------

class TestToolsModule:
    @pytest.fixture
    def tools(self):
        """Load the tools module."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "scoped_tools", DEMO_DIR / "tools.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_has_tool_definitions(self, tools) -> None:
        assert hasattr(tools, "TOOL_DEFINITIONS")
        assert len(tools.TOOL_DEFINITIONS) >= 2

    def test_has_tool_handlers(self, tools) -> None:
        assert hasattr(tools, "TOOL_HANDLERS")
        assert "list_servers" in tools.TOOL_HANDLERS
        assert "restart_server" in tools.TOOL_HANDLERS

    def test_list_servers_returns_json(self, tools) -> None:
        result = tools.TOOL_HANDLERS["list_servers"]()
        data = json.loads(result)
        assert isinstance(data, dict)
        assert len(data) >= 3

    def test_list_servers_filters_by_rack(self, tools) -> None:
        result = tools.TOOL_HANDLERS["list_servers"](rack=7)
        data = json.loads(result)
        for server_id, info in data.items():
            assert info["rack"] == 7

    def test_restart_server_succeeds_with_valid_id(self, tools) -> None:
        result = tools.TOOL_HANDLERS["restart_server"](
            server_id="SRV-1002", reason="test"
        )
        data = json.loads(result)
        assert data["success"] is True

    def test_restart_server_rejects_invalid_id(self, tools) -> None:
        """Pydantic validation should catch fabricated IDs."""
        with pytest.raises(Exception) as exc_info:
            tools.TOOL_HANDLERS["restart_server"](
                server_id="SRV-9999", reason="test"
            )
        assert "not found" in str(exc_info.value).lower() or "inventory" in str(exc_info.value).lower()

    def test_restart_server_rejects_bad_format(self, tools) -> None:
        with pytest.raises(Exception):
            tools.TOOL_HANDLERS["restart_server"](
                server_id="invalid", reason="test"
            )

    def test_inventory_has_server_in_rack_7(self, tools) -> None:
        """The task asks to restart the database server in rack 7.
        There must be at least one server there."""
        result = tools.TOOL_HANDLERS["list_servers"](rack=7)
        data = json.loads(result)
        assert len(data) >= 1

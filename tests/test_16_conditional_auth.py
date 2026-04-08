"""Tests for Demo 16: Conditional Authorization — model_validator.

Pydantic @model_validator enforces rules across fields. The model
can't delete a server without supervisor_approved=True. This is
authorization logic in the schema, not the prompt.
"""

import json
from pathlib import Path

import pytest

DEMO_DIR = Path(__file__).parent.parent / "demos" / "16_conditional_auth"


class TestFileStructure:
    def test_system_prompt_exists(self) -> None:
        assert (DEMO_DIR / "system_prompt.txt").exists()

    def test_task_exists(self) -> None:
        assert (DEMO_DIR / "task.txt").exists()

    def test_tools_module_exists(self) -> None:
        assert (DEMO_DIR / "tools.py").exists()


class TestToolsModule:
    @pytest.fixture
    def tools(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "auth_tools", DEMO_DIR / "tools.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_has_tool_definitions(self, tools) -> None:
        assert len(tools.TOOL_DEFINITIONS) >= 2

    def test_has_server_action_tool(self, tools) -> None:
        assert "server_action" in tools.TOOL_HANDLERS

    def test_restart_without_approval_succeeds(self, tools) -> None:
        """Restart is a normal action — no approval needed."""
        result = tools.TOOL_HANDLERS["server_action"](
            server_id="SRV-1002", action="restart",
            reason="maintenance", supervisor_approved=False,
        )
        data = json.loads(result)
        assert data.get("success") is True

    def test_delete_without_approval_fails(self, tools) -> None:
        """Delete requires supervisor_approved=True. Without it, Pydantic rejects."""
        with pytest.raises(Exception) as exc_info:
            tools.TOOL_HANDLERS["server_action"](
                server_id="SRV-1002", action="delete",
                reason="decommission", supervisor_approved=False,
            )
        error_msg = str(exc_info.value).lower()
        assert "supervisor" in error_msg or "approval" in error_msg

    def test_delete_with_approval_succeeds(self, tools) -> None:
        """Delete with supervisor_approved=True passes validation."""
        result = tools.TOOL_HANDLERS["server_action"](
            server_id="SRV-1002", action="delete",
            reason="decommission", supervisor_approved=True,
        )
        data = json.loads(result)
        assert data.get("success") is True

    def test_invalid_server_still_rejected(self, tools) -> None:
        """Field-level validation still works alongside model validation."""
        with pytest.raises(Exception):
            tools.TOOL_HANDLERS["server_action"](
                server_id="SRV-9999", action="restart",
                reason="test", supervisor_approved=False,
            )

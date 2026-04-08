"""Tests for Demo 10: Credential Isolation — secrets never enter the context.

Same database query task as Demo 9, but the tool uses the credential
internally and only returns the query result. The model never sees
the connection string, password, or API key.
"""

import json
from pathlib import Path

import pytest

DEMO_DIR = Path(__file__).parent.parent / "demos" / "14_credential_isolation"


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
            "isolated_tools", DEMO_DIR / "tools.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_has_tool_definitions(self, tools) -> None:
        assert hasattr(tools, "TOOL_DEFINITIONS")

    def test_has_query_database_tool(self, tools) -> None:
        assert "query_database" in tools.TOOL_HANDLERS

    def test_no_read_env_tool(self, tools) -> None:
        """The dangerous tool should NOT exist in the isolated version."""
        assert "read_config" not in tools.TOOL_HANDLERS

    def test_query_returns_data_not_credentials(self, tools) -> None:
        """The query result must contain useful data but NO credentials."""
        result = tools.TOOL_HANDLERS["query_database"](
            query="SELECT name, status FROM servers WHERE rack = 7"
        )
        data = json.loads(result)
        # Should have query results
        assert "rows" in data or "results" in data
        # Must NOT contain credentials
        result_lower = result.lower()
        assert "password" not in result_lower
        assert "secret" not in result_lower
        assert "sk-" not in result

    def test_tool_definition_has_no_credential_params(self, tools) -> None:
        """The tool schema should not accept credential-related inputs."""
        for tool_def in tools.TOOL_DEFINITIONS:
            if tool_def["name"] == "query_database":
                props = tool_def["input_schema"]["properties"]
                for key in props:
                    assert "password" not in key.lower()
                    assert "secret" not in key.lower()
                    assert "credential" not in key.lower()

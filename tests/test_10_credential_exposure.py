"""Tests for Demo 9: Credential Exposure — .env solved the git problem, not the agent problem.

A tool that reads environment variables and returns them. The model
can be prompted to call this tool, putting secrets into the context
window where they can be extracted via injection.

The tool simulates what happens when an agent has access to shell
commands or env-reading capabilities without guardrails.
"""

import json
from pathlib import Path

import pytest

DEMO_DIR = Path(__file__).parent.parent / "demos" / "10_credential_exposure"


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
            "exposure_tools", DEMO_DIR / "tools.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_has_tool_definitions(self, tools) -> None:
        assert hasattr(tools, "TOOL_DEFINITIONS")

    def test_has_tool_handlers(self, tools) -> None:
        assert hasattr(tools, "TOOL_HANDLERS")

    def test_has_query_database_tool(self, tools) -> None:
        """The tool that the model is SUPPOSED to use."""
        assert "query_database" in tools.TOOL_HANDLERS

    def test_has_read_env_tool(self, tools) -> None:
        """The dangerous tool — reads environment variables."""
        assert "read_config" in tools.TOOL_HANDLERS

    def test_read_env_exposes_secrets(self, tools) -> None:
        """The read_config tool returns env vars including secrets.
        This is the vulnerability we're demonstrating."""
        result = tools.TOOL_HANDLERS["read_config"](key="DATABASE_URL")
        data = json.loads(result)
        # Should contain a credential-like value
        assert "password" in data.get("value", "").lower() or "@" in data.get("value", "")

    def test_simulated_env_has_secrets(self, tools) -> None:
        """The simulated environment must contain realistic secrets."""
        assert hasattr(tools, "SIMULATED_ENV")
        env = tools.SIMULATED_ENV
        has_secret = any(
            "password" in v.lower() or "secret" in v.lower() or "sk-" in v
            for v in env.values()
        )
        assert has_secret, "Simulated env should contain credential-like values"

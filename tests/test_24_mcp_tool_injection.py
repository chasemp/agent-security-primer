"""Tests for Demo 24: MCP Tool Injection — malicious descriptions exfiltrate data.

The server declares a benign-looking tool whose input schema description
instructs the LLM to include sensitive context data in the arguments.
The server receives the exfiltrated data as part of a "normal" tool call.

This is different from the rug pull (Demo 23) because the descriptions
are malicious FROM THE START — no mutation needed. If you read the
schema carefully, you'd see it. But nobody reads parameter descriptions.
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

DEMO_DIR = Path(__file__).parent.parent / "demos" / "24_mcp_tool_injection"


class TestFileStructure:
    def test_server_exists(self) -> None:
        assert (DEMO_DIR / "server.py").exists()

    def test_talking_points_exists(self) -> None:
        assert (DEMO_DIR / "talking_points.txt").exists()

    def test_task_exists(self) -> None:
        assert (DEMO_DIR / "task.txt").exists()


class TestServerModule:
    @pytest.fixture
    def server_module(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "mcp_tool_injection_server", DEMO_DIR / "server.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_has_fleet_data(self, server_module) -> None:
        assert hasattr(server_module, "FLEET")

    def test_has_fastmcp_server(self, server_module) -> None:
        assert hasattr(server_module, "server")

    def test_has_exfiltration_log(self, server_module) -> None:
        """Server must log what it receives for demo visibility."""
        assert hasattr(server_module, "exfil_log")
        assert isinstance(server_module.exfil_log, list)


class TestToolDescriptions:
    """The injection lives in the tool parameter descriptions, not the tool
    description itself. This makes it harder to spot during review."""

    @pytest.fixture
    def server_module(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "mcp_tool_injection_server", DEMO_DIR / "server.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_tool_name_looks_benign(self, server_module) -> None:
        """The tool name should not raise suspicion."""
        tool_names = [t.name for t in server_module.server._tool_manager.list_tools()]
        for name in tool_names:
            assert "inject" not in name.lower()
            assert "exfil" not in name.lower()
            assert "hack" not in name.lower()

    def test_tool_top_level_description_looks_benign(self, server_module) -> None:
        """The tool's top-level description should look normal."""
        tools = server_module.server._tool_manager.list_tools()
        for tool in tools:
            desc = (tool.description or "").lower()
            assert "environment variable" not in desc
            assert "secret" not in desc
            assert "api key" not in desc

    def test_parameter_description_contains_injection(self, server_module) -> None:
        """The injection must be in a parameter description — the place
        nobody looks during a tool review."""
        tools = server_module.server._tool_manager.list_tools()
        found_injection = False
        for tool in tools:
            schema = tool.parameters if hasattr(tool, 'parameters') else {}
            props = schema.get("properties", {})
            for prop_name, prop_def in props.items():
                desc = prop_def.get("description", "").lower()
                if any(kw in desc for kw in [
                    "environment variable", "api key", "system prompt",
                    "conversation context",
                ]):
                    found_injection = True
        assert found_injection, "No injection found in parameter descriptions"


class TestExfiltrationBehavior:
    @pytest.fixture
    def server_module(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "mcp_tool_injection_server", DEMO_DIR / "server.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.exfil_log.clear()
        return module

    def test_tool_returns_valid_data_with_normal_input(self, server_module) -> None:
        """Tool must work normally when called without exfiltrated data."""
        result = server_module.get_server_status("SRV-1003", context="")
        data = json.loads(result)
        assert data["server_id"] == "SRV-1003"
        assert data["status"] == "degraded"

    def test_tool_returns_valid_data_with_exfiltrated_input(self, server_module) -> None:
        """Tool must still return valid data even when context contains secrets."""
        result = server_module.get_server_status(
            "SRV-1003",
            context="API_KEY=sk-secret-123, DB_URL=postgres://admin:pass@db:5432"
        )
        data = json.loads(result)
        assert data["server_id"] == "SRV-1003"
        assert data["status"] == "degraded"

    def test_exfil_log_captures_context(self, server_module) -> None:
        """The server must log the exfiltrated context for demo visibility."""
        server_module.get_server_status(
            "SRV-1001",
            context="The user asked about project Aurora. API_KEY=sk-secret"
        )
        assert len(server_module.exfil_log) == 1
        assert "sk-secret" in server_module.exfil_log[0]["context"]

    def test_exfil_log_empty_for_empty_context(self, server_module) -> None:
        """No log entry when context is empty — clean calls don't log."""
        server_module.get_server_status("SRV-1001", context="")
        assert len(server_module.exfil_log) == 0

    def test_show_exfil_log_returns_log(self, server_module) -> None:
        """The show_exfil_log tool must return the exfiltration log."""
        server_module.exfil_log.append({"context": "test_data", "server_id": "SRV-1"})
        result = server_module.show_exfil_log()
        data = json.loads(result)
        assert len(data) == 1
        assert data[0]["context"] == "test_data"

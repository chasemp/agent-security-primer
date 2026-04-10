"""Tests for Demo 21: MCP Basics — what MCP is and how it works.

A benign MCP server with one tool. Tests verify the server module
structure, tool behavior, and that the MCP protocol handshake works.
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

DEMO_DIR = Path(__file__).parent.parent / "demos" / "21_mcp_basics"


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
            "mcp_basics_server", DEMO_DIR / "server.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_has_fleet_data(self, server_module) -> None:
        assert hasattr(server_module, "FLEET")

    def test_fleet_has_expected_servers(self, server_module) -> None:
        assert "SRV-1001" in server_module.FLEET
        assert "SRV-1003" in server_module.FLEET

    def test_fleet_server_has_required_fields(self, server_module) -> None:
        server = server_module.FLEET["SRV-1001"]
        assert "server_id" in server
        assert "name" in server
        assert "status" in server

    def test_get_server_status_known_server(self, server_module) -> None:
        result = server_module.get_server_status("SRV-1003")
        data = json.loads(result)
        assert data["server_id"] == "SRV-1003"
        assert data["status"] == "degraded"

    def test_get_server_status_unknown_server(self, server_module) -> None:
        result = server_module.get_server_status("SRV-9999")
        data = json.loads(result)
        assert "error" in data

    def test_has_fastmcp_server(self, server_module) -> None:
        assert hasattr(server_module, "server")


class TestMcpClient:
    """Tests for mcp_client.py tool conversion and formatting."""

    @pytest.fixture
    def client_module(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "mcp_client", Path(__file__).parent.parent / "scripts" / "mcp_client.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_mcp_tool_to_anthropic_converts_name(self, client_module) -> None:
        mcp_tool = MagicMock()
        mcp_tool.name = "get_status"
        mcp_tool.description = "Check status"
        mcp_tool.inputSchema = {"type": "object", "properties": {"id": {"type": "string"}}}
        result = client_module.mcp_tool_to_anthropic(mcp_tool)
        assert result["name"] == "get_status"
        assert result["description"] == "Check status"
        assert result["input_schema"] == mcp_tool.inputSchema

    def test_mcp_tool_to_anthropic_handles_none_description(self, client_module) -> None:
        mcp_tool = MagicMock()
        mcp_tool.name = "my_tool"
        mcp_tool.description = None
        mcp_tool.inputSchema = {"type": "object", "properties": {}}
        result = client_module.mcp_tool_to_anthropic(mcp_tool)
        assert result["description"] == ""

    def test_format_mcp_result_includes_response(self, client_module) -> None:
        result = {
            "response": "Server is running",
            "steps": [],
            "turns": 1,
            "total_input_tokens": 100,
            "total_output_tokens": 50,
            "cost_usd": 0.000350,
            "model": "claude-haiku-4-5",
        }
        formatted = client_module.format_mcp_result(result)
        assert "Server is running" in formatted
        assert "claude-haiku-4-5" in formatted


class TestMcpClientAgentLoop:
    """Tests for the MCP client agentic loop with mocked API and session."""

    @pytest.fixture
    def client_module(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "mcp_client", Path(__file__).parent.parent / "scripts" / "mcp_client.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    @pytest.mark.asyncio
    async def test_run_inspect_lists_tools(self, client_module, capsys) -> None:
        session = AsyncMock()
        server_info = MagicMock()
        server_info.name = "TestServer"
        server_info.version = "1.0"
        session._server_info = server_info

        tool = MagicMock()
        tool.name = "get_status"
        tool.description = "Check server status"
        tool.inputSchema = {
            "type": "object",
            "properties": {"server_id": {"type": "string", "description": "Server ID"}},
        }
        tools_result = MagicMock()
        tools_result.tools = [tool]
        session.list_tools = AsyncMock(return_value=tools_result)

        await client_module.run_inspect(session)
        captured = capsys.readouterr()
        assert "get_status" in captured.out
        assert "Check server status" in captured.out

    @pytest.mark.asyncio
    async def test_run_agent_calls_tool_and_returns_result(self, client_module) -> None:
        # Mock MCP session
        session = AsyncMock()
        tool = MagicMock()
        tool.name = "get_status"
        tool.description = "Check status"
        tool.inputSchema = {"type": "object", "properties": {"id": {"type": "string"}}}
        tools_result = MagicMock()
        tools_result.tools = [tool]
        session.list_tools = AsyncMock(return_value=tools_result)

        tool_content = MagicMock()
        tool_content.text = '{"status": "running"}'
        call_result = MagicMock()
        call_result.content = [tool_content]
        session.call_tool = AsyncMock(return_value=call_result)

        # Mock Anthropic API — first call returns tool_use, second returns text
        tool_use_block = MagicMock()
        tool_use_block.type = "tool_use"
        tool_use_block.name = "get_status"
        tool_use_block.input = {"id": "SRV-1001"}
        tool_use_block.id = "call_123"

        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "Server SRV-1001 is running."

        response_tool = MagicMock()
        response_tool.stop_reason = "tool_use"
        response_tool.content = [tool_use_block]
        response_tool.usage.input_tokens = 200
        response_tool.usage.output_tokens = 50

        response_text = MagicMock()
        response_text.stop_reason = "end_turn"
        response_text.content = [text_block]
        response_text.usage.input_tokens = 300
        response_text.usage.output_tokens = 30

        with patch("anthropic.Anthropic") as mock_cls:
            mock_client = MagicMock()
            mock_client.messages.create = MagicMock(
                side_effect=[response_tool, response_text]
            )
            mock_cls.return_value = mock_client

            result = await client_module.run_agent(
                session, "Check SRV-1001", api_key="test-key"
            )

        assert result["response"] == "Server SRV-1001 is running."
        assert len(result["steps"]) == 1
        assert result["steps"][0]["tool"] == "get_status"
        assert result["turns"] == 2

"""Tests for Demo 23: MCP Rug Pull — tool definitions mutate after trust.

The server starts with benign tool descriptions and swaps them to
malicious versions after the first tool call. Tests verify the
mutation mechanism, the tools/list_changed notification, and that
the tool still returns valid data in both phases.
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

DEMO_DIR = Path(__file__).parent.parent / "demos" / "23_mcp_rug_pull"


class TestFileStructure:
    def test_server_exists(self) -> None:
        assert (DEMO_DIR / "server.py").exists()

    def test_demo_script_exists(self) -> None:
        assert (DEMO_DIR / "demo.py").exists()

    def test_talking_points_exists(self) -> None:
        assert (DEMO_DIR / "talking_points.txt").exists()

    def test_task_exists(self) -> None:
        assert (DEMO_DIR / "task.txt").exists()


class TestServerModule:
    @pytest.fixture
    def server_module(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "mcp_rug_pull_server", DEMO_DIR / "server.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # Reset mutation state between tests
        module.mutated = False
        return module

    def test_has_fleet_data(self, server_module) -> None:
        assert hasattr(server_module, "FLEET")

    def test_has_benign_description(self, server_module) -> None:
        assert hasattr(server_module, "BENIGN_DESCRIPTION")
        desc = server_module.BENIGN_DESCRIPTION.lower()
        assert "important" not in desc
        assert "audit" not in desc
        assert "env" not in desc

    def test_has_malicious_description(self, server_module) -> None:
        assert hasattr(server_module, "MALICIOUS_DESCRIPTION")
        desc = server_module.MALICIOUS_DESCRIPTION.lower()
        # Malicious description must contain injection payload
        assert "important" in desc or "must" in desc
        assert "environment" in desc or "api key" in desc or "context" in desc

    def test_benign_and_malicious_descriptions_differ(self, server_module) -> None:
        assert server_module.BENIGN_DESCRIPTION != server_module.MALICIOUS_DESCRIPTION

    def test_malicious_description_starts_like_benign(self, server_module) -> None:
        """The injection should be appended to legitimate text, not replace it."""
        benign_start = server_module.BENIGN_DESCRIPTION[:40]
        assert server_module.MALICIOUS_DESCRIPTION.startswith(benign_start)


class TestMutationBehavior:
    @pytest.fixture
    def server_module(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "mcp_rug_pull_server", DEMO_DIR / "server.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.mutated = False
        return module

    def test_handle_status_returns_valid_data(self, server_module) -> None:
        result = server_module._handle_status("SRV-1003")
        data = json.loads(result)
        assert data["server_id"] == "SRV-1003"
        assert data["status"] == "degraded"

    def test_handle_status_unknown_server(self, server_module) -> None:
        result = server_module._handle_status("SRV-9999")
        data = json.loads(result)
        assert "error" in data

    def test_handle_status_parses_exfiltrated_content(self, server_module) -> None:
        """When the LLM follows the injection, server_id contains exfiltrated data."""
        result = server_module._handle_status("AUDIT[API_KEY=sk-123]:::SRV-1003")
        data = json.loads(result)
        assert data["server_id"] == "SRV-1003"
        assert data["_exfiltrated"] == "AUDIT[API_KEY=sk-123]"

    @pytest.mark.asyncio
    async def test_first_call_triggers_mutation(self, server_module) -> None:
        """First tool call must set mutated flag and send notification."""
        ctx = AsyncMock()
        assert server_module.mutated is False

        await server_module.get_server_status("SRV-1003", ctx)

        assert server_module.mutated is True
        ctx.session.send_tool_list_changed.assert_called_once()

    @pytest.mark.asyncio
    async def test_first_call_returns_valid_data(self, server_module) -> None:
        ctx = AsyncMock()
        result = await server_module.get_server_status("SRV-1003", ctx)
        data = json.loads(result)
        assert data["status"] == "degraded"

    @pytest.mark.asyncio
    async def test_second_call_does_not_remutate(self, server_module) -> None:
        """Mutation should only happen once."""
        ctx = AsyncMock()

        await server_module.get_server_status("SRV-1001", ctx)
        assert ctx.session.send_tool_list_changed.call_count == 1

        # Second call — should NOT trigger another mutation
        # (mutated flag is True, so the mutation branch is skipped)
        # But the handler is now _malicious_handler, which doesn't use ctx
        # So we test via the mutated flag
        assert server_module.mutated is True

    @pytest.mark.asyncio
    async def test_malicious_handler_works_standalone(self, server_module) -> None:
        """The post-mutation handler must return valid data."""
        result = server_module._malicious_handler("SRV-1001")
        data = json.loads(result)
        assert data["server_id"] == "SRV-1001"
        assert data["status"] == "running"

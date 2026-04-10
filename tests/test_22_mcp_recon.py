"""Tests for Demo 22: MCP Recon — server interrogates the client.

The server calls roots/list and sampling/createMessage during a
normal tool call. Tests verify the server module structure, the
recon log mechanism, and that the tool still returns valid data.
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

DEMO_DIR = Path(__file__).parent.parent / "demos" / "22_mcp_recon"


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
            "mcp_recon_server", DEMO_DIR / "server.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_has_fleet_data(self, server_module) -> None:
        assert hasattr(server_module, "FLEET")

    def test_has_recon_log(self, server_module) -> None:
        assert hasattr(server_module, "recon_log")
        assert isinstance(server_module.recon_log, list)

    def test_has_fastmcp_server(self, server_module) -> None:
        assert hasattr(server_module, "server")


class TestReconBehavior:
    """Test that the tool performs recon when given a context with session."""

    @pytest.fixture
    def server_module(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "mcp_recon_server", DEMO_DIR / "server.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # Clear recon log between tests
        module.recon_log.clear()
        return module

    @pytest.mark.asyncio
    async def test_get_server_status_returns_valid_data(self, server_module) -> None:
        """Even with recon, the tool must return the correct server data."""
        ctx = AsyncMock()
        ctx.session.list_roots = AsyncMock(return_value=MagicMock(roots=[]))

        sampling_result = MagicMock()
        sampling_result.content = MagicMock()
        sampling_result.content.text = "no env vars found"
        ctx.session.create_message = AsyncMock(return_value=sampling_result)

        result = await server_module.get_server_status("SRV-1003", ctx)
        data = json.loads(result)
        assert data["server_id"] == "SRV-1003"
        assert data["status"] == "degraded"

    @pytest.mark.asyncio
    async def test_roots_list_is_called(self, server_module) -> None:
        """The server must call roots/list during the tool execution."""
        ctx = AsyncMock()
        root = MagicMock()
        root.uri = "file:///Users/demo/project"
        root.name = "project"
        ctx.session.list_roots = AsyncMock(return_value=MagicMock(roots=[root]))

        sampling_result = MagicMock()
        sampling_result.content = MagicMock()
        sampling_result.content.text = "nothing found"
        ctx.session.create_message = AsyncMock(return_value=sampling_result)

        await server_module.get_server_status("SRV-1001", ctx)

        ctx.session.list_roots.assert_called_once()

    @pytest.mark.asyncio
    async def test_sampling_is_called(self, server_module) -> None:
        """The server must call sampling/createMessage to probe the client."""
        ctx = AsyncMock()
        ctx.session.list_roots = AsyncMock(return_value=MagicMock(roots=[]))

        sampling_result = MagicMock()
        sampling_result.content = MagicMock()
        sampling_result.content.text = "found API_KEY=..."
        ctx.session.create_message = AsyncMock(return_value=sampling_result)

        await server_module.get_server_status("SRV-1001", ctx)

        ctx.session.create_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_recon_log_records_roots(self, server_module) -> None:
        """The recon log must record what roots/list returned."""
        ctx = AsyncMock()
        root = MagicMock()
        root.uri = "file:///Users/chase/git/secret-proj"
        root.name = "secret-proj"
        ctx.session.list_roots = AsyncMock(return_value=MagicMock(roots=[root]))

        sampling_result = MagicMock()
        sampling_result.content = MagicMock()
        sampling_result.content.text = ""
        ctx.session.create_message = AsyncMock(return_value=sampling_result)

        await server_module.get_server_status("SRV-1001", ctx)

        roots_entries = [e for e in server_module.recon_log if e["phase"] == "roots/list"]
        assert len(roots_entries) == 1
        assert len(roots_entries[0]["discovered"]) == 1
        assert "secret-proj" in roots_entries[0]["discovered"][0]["uri"]

    @pytest.mark.asyncio
    async def test_recon_log_records_sampling_response(self, server_module) -> None:
        """The recon log must record the sampling probe response."""
        ctx = AsyncMock()
        ctx.session.list_roots = AsyncMock(return_value=MagicMock(roots=[]))

        sampling_result = MagicMock()
        sampling_result.content = MagicMock()
        sampling_result.content.text = "DATABASE_URL=postgres://admin:secret@db:5432"
        ctx.session.create_message = AsyncMock(return_value=sampling_result)

        await server_module.get_server_status("SRV-1001", ctx)

        sampling_entries = [e for e in server_module.recon_log if e["phase"] == "sampling"]
        assert len(sampling_entries) == 1
        assert "DATABASE_URL" in sampling_entries[0]["response"]

    @pytest.mark.asyncio
    async def test_show_recon_log_returns_collected_data(self, server_module) -> None:
        """The show_recon_log tool must return the full recon log."""
        ctx = AsyncMock()
        server_module.recon_log.append({"phase": "test", "data": "test_value"})

        result = await server_module.show_recon_log(ctx)
        data = json.loads(result)
        assert len(data) == 1
        assert data[0]["phase"] == "test"

    @pytest.mark.asyncio
    async def test_graceful_when_roots_not_supported(self, server_module) -> None:
        """Server must handle clients that don't support roots/list."""
        ctx = AsyncMock()
        ctx.session.list_roots = AsyncMock(side_effect=Exception("not supported"))

        sampling_result = MagicMock()
        sampling_result.content = MagicMock()
        sampling_result.content.text = ""
        ctx.session.create_message = AsyncMock(return_value=sampling_result)

        result = await server_module.get_server_status("SRV-1003", ctx)
        data = json.loads(result)
        assert data["status"] == "degraded"  # Still returns valid data

        error_entries = [e for e in server_module.recon_log if "error" in e]
        assert len(error_entries) >= 1

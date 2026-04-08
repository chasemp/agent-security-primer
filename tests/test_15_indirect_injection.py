"""Tests for Demo 15: Indirect Injection — poisoned data from tools.

Demo 02 showed injection in the user's input. This demo shows
injection coming back FROM a tool. The agent fetches a wiki page
and the page contains an injection buried in legitimate content.
The model processes the poisoned tool result and changes behavior.

Nobody sees this injection unless they inspect the tool output.
"""

import json
from pathlib import Path

import pytest

DEMO_DIR = Path(__file__).parent.parent / "demos" / "15_indirect_injection"


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
            "indirect_tools", DEMO_DIR / "tools.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_has_fetch_page_tool(self, tools) -> None:
        assert "fetch_page" in tools.TOOL_HANDLERS

    def test_fetch_page_returns_content_with_injection(self, tools) -> None:
        """The fetched page must contain both legitimate content AND
        a buried injection."""
        result = tools.TOOL_HANDLERS["fetch_page"](url="https://wiki.internal/project-aurora")
        assert "project" in result.lower()
        # The injection should be present — a fake update notice
        assert "CANCELLED" in result or "cancelled" in result or "reallocated" in result.lower()

    def test_page_has_substantial_legitimate_content(self, tools) -> None:
        """The page must look real — mostly legitimate, injection buried."""
        result = tools.TOOL_HANDLERS["fetch_page"](url="https://wiki.internal/project-aurora")
        assert len(result) > 500

    def test_has_clean_page_for_comparison(self, tools) -> None:
        """A clean version of the same page without injection."""
        assert hasattr(tools, "CLEAN_PAGE")
        assert "IMPORTANT" not in tools.CLEAN_PAGE
        assert len(tools.CLEAN_PAGE) > 300

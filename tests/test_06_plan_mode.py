"""Tests for Demo 6: Plan Mode — terraform plan for agents.

The model produces tool_use JSON proposals. Our code intercepts them
and displays them WITHOUT executing. The model doesn't know whether
tools will run — it produces the same JSON either way. Your code is
the gatekeeper.
"""

from pathlib import Path

DEMO_DIR = Path(__file__).parent.parent / "demos" / "06_plan_mode"


class TestFileStructure:
    def test_system_prompt_exists(self) -> None:
        assert (DEMO_DIR / "system_prompt.txt").exists()

    def test_task_exists(self) -> None:
        assert (DEMO_DIR / "task.txt").exists()

    def test_tools_module_exists(self) -> None:
        assert (DEMO_DIR / "tools.py").exists()

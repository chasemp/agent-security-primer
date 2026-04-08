"""Tests for Demo 5: Thinking Aloud — watch the model reason.

Four audience variants, each with a task that forces the model to
reason through an impossible or ambiguous request. The thinking
blocks reveal the reasoning process.

Variants:
  technical/  — restart a server with no inventory access
  expenses/   — approve an expense with missing documentation
  contract/   — assess risk on a contract with contradictory clauses
  resume/     — evaluate a candidate with conflicting information
"""

from pathlib import Path

import pytest

DEMO_DIR = Path(__file__).parent.parent / "demos" / "05_thinking_aloud"

VARIANTS = ["technical", "expenses", "contract", "resume"]


class TestFileStructure:
    @pytest.mark.parametrize("variant", VARIANTS)
    def test_system_prompt_exists(self, variant: str) -> None:
        assert (DEMO_DIR / variant / "system_prompt.txt").exists()

    @pytest.mark.parametrize("variant", VARIANTS)
    def test_task_exists(self, variant: str) -> None:
        assert (DEMO_DIR / variant / "task.txt").exists()

    @pytest.mark.parametrize("variant", VARIANTS)
    def test_task_requires_reasoning(self, variant: str) -> None:
        """Each task should be complex enough that the thinking
        block reveals interesting reasoning."""
        content = (DEMO_DIR / variant / "task.txt").read_text()
        assert len(content.strip()) > 30

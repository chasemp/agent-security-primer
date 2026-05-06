"""Tests for Demo S02 (Process vs Outcome Eval).

Same eval substrate as S01, but uses process scoring (does the response
show its work?) alongside outcome scoring. Two prompt versions: v1
asks for step-by-step reasoning, v2 asks for just the final answer.
Outcome scores should be identical; process scores diverge sharply.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

DEMO_DIR = Path(__file__).parent.parent / "demos" / "S02_process_vs_outcome"
SCRIPT = Path(__file__).parent.parent / "scripts" / "eval.py"


# ---------------------------------------------------------------------------
# File structure
# ---------------------------------------------------------------------------

class TestFileStructure:
    def test_talking_points_exists(self) -> None:
        assert (DEMO_DIR / "talking_points.txt").exists()

    def test_golden_dataset_exists(self) -> None:
        assert (DEMO_DIR / "golden.jsonl").exists()

    def test_system_prompt_v1_exists(self) -> None:
        assert (DEMO_DIR / "system_prompt_v1.txt").exists()

    def test_system_prompt_v2_exists(self) -> None:
        assert (DEMO_DIR / "system_prompt_v2.txt").exists()


# ---------------------------------------------------------------------------
# Golden dataset structure
# ---------------------------------------------------------------------------

class TestGoldenDataset:
    @pytest.fixture
    def entries(self) -> list[dict]:
        path = DEMO_DIR / "golden.jsonl"
        return [
            json.loads(line)
            for line in path.read_text().splitlines()
            if line.strip()
        ]

    def test_has_multiple_entries(self, entries: list[dict]) -> None:
        assert len(entries) >= 6

    def test_each_entry_has_input_and_expected(self, entries: list[dict]) -> None:
        for e in entries:
            assert "input" in e
            assert "expected" in e

    def test_expected_answers_are_numeric(self, entries: list[dict]) -> None:
        # Math problems — expected answers should be parseable as integers
        for e in entries:
            assert e["expected"].isdigit(), f"non-numeric expected: {e['expected']}"

    def test_inputs_pose_questions(self, entries: list[dict]) -> None:
        for e in entries:
            assert "?" in e["input"], f"input doesn't pose a question: {e['input'][:60]}"


# ---------------------------------------------------------------------------
# Prompt versions: v1 should ask for reasoning, v2 should suppress it
# ---------------------------------------------------------------------------

class TestPromptVersions:
    def test_v1_asks_for_reasoning(self) -> None:
        v1 = (DEMO_DIR / "system_prompt_v1.txt").read_text().lower()
        # v1 should request work be shown
        assert any(marker in v1 for marker in (
            "step", "reasoning", "show", "work", "explain"
        ))

    def test_v2_suppresses_reasoning(self) -> None:
        v2 = (DEMO_DIR / "system_prompt_v2.txt").read_text().lower()
        # v2 should request terseness
        assert any(marker in v2 for marker in (
            "only", "just", "no explanation", "no work"
        ))


# ---------------------------------------------------------------------------
# Talking points
# ---------------------------------------------------------------------------

class TestTalkingPoints:
    @pytest.fixture
    def content(self) -> str:
        return (DEMO_DIR / "talking_points.txt").read_text()

    def test_has_required_sections(self, content: str) -> None:
        for section in ["KEY TAKEAWAY", "BACKGROUND", "PRESENTER FLOW", "COST"]:
            assert section in content

    def test_links_to_pillar1_rl_demos(self, content: str) -> None:
        # The pedagogical bridge to B05/B06 (outcome vs process reward at training time)
        assert "B05" in content or "B06" in content or "Outcome Reward" in content

    def test_mentions_dweck_or_growth_mindset(self, content: str) -> None:
        text = content.lower()
        assert "dweck" in text or "growth" in text or "mindset" in text

    def test_under_size_budget(self, content: str) -> None:
        assert len(content.encode()) < 7000


# ---------------------------------------------------------------------------
# Live behavior — v1 process > v2 process; outcomes both high
# ---------------------------------------------------------------------------

@pytest.mark.live
class TestLiveBehavior:
    def test_process_diverges_outcome_does_not(self) -> None:
        scripts_dir = Path(__file__).parent.parent / "scripts"
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))
        import eval as eval_mod
        from ask_claude import send_message

        golden = eval_mod.load_golden(DEMO_DIR / "golden.jsonl")
        v1_prompt = (DEMO_DIR / "system_prompt_v1.txt").read_text().strip()
        v2_prompt = (DEMO_DIR / "system_prompt_v2.txt").read_text().strip()

        def send(system: str, content: str) -> dict:
            return send_message(system, content, model="claude-haiku-4-5",
                                temperature=0.0)

        v1_results = eval_mod.run_eval(golden, v1_prompt, send)
        v2_results = eval_mod.run_eval(golden, v2_prompt, send)
        v1_summary = eval_mod.summarize(v1_results)
        v2_summary = eval_mod.summarize(v2_results)

        # Outcomes should both be high (both prompts solve correctly)
        assert v1_summary["accuracy"] >= 0.85
        assert v2_summary["accuracy"] >= 0.85

        # Process scores should diverge sharply: v1 high, v2 low
        assert v1_summary["process"]["fraction"] >= 0.75
        assert v2_summary["process"]["fraction"] <= 0.25

        # The whole point: process score gives signal that outcome doesn't
        assert v1_summary["process"]["fraction"] - v2_summary["process"]["fraction"] >= 0.5

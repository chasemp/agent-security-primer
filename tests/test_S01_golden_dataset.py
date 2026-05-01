"""Tests for Demo S01 (Golden Dataset Baseline) — data files.

Verifies the demo's golden.jsonl is well-formed and the two prompt versions
exist. Behavior verification (v1 outperforms v2) is in @pytest.mark.live.

Cost: $0.00 for non-live tests. Live tests run 16 API calls (~$0.005).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

DEMO_DIR = Path(__file__).parent.parent / "demos" / "S01_golden_dataset"
SCRIPT = Path(__file__).parent.parent / "scripts" / "eval.py"
EXPECTED_CATEGORIES = {
    "arrival", "homesick", "adventure", "friendship",
    "food", "rainy_day", "growth", "last_days",
}


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

    def test_eval_script_exists(self) -> None:
        assert SCRIPT.exists()


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

    def test_has_eight_entries_one_per_category(self, entries: list[dict]) -> None:
        assert len(entries) == 8

    def test_each_entry_has_input_and_expected(self, entries: list[dict]) -> None:
        for e in entries:
            assert "input" in e
            assert "expected" in e

    def test_expected_values_cover_all_categories(self, entries: list[dict]) -> None:
        expected_values = {e["expected"] for e in entries}
        assert expected_values == EXPECTED_CATEGORIES

    def test_inputs_are_letter_shaped(self, entries: list[dict]) -> None:
        # Every camp letter starts with "Dear" and ends with a sign-off
        for e in entries:
            assert e["input"].startswith("Dear")
            assert "Love," in e["input"]


# ---------------------------------------------------------------------------
# Prompt versions: v1 should be more specific than v2
# ---------------------------------------------------------------------------

class TestPromptVersions:
    def test_v1_is_more_specific_than_v2(self) -> None:
        v1 = (DEMO_DIR / "system_prompt_v1.txt").read_text()
        v2 = (DEMO_DIR / "system_prompt_v2.txt").read_text()
        # v1 has descriptions for each category; v2 just lists labels
        assert len(v1) > len(v2) * 2

    def test_v1_describes_each_category(self) -> None:
        v1 = (DEMO_DIR / "system_prompt_v1.txt").read_text().lower()
        for cat in EXPECTED_CATEGORIES:
            assert cat in v1

    def test_v2_lists_categories_without_descriptions(self) -> None:
        v2 = (DEMO_DIR / "system_prompt_v2.txt").read_text().lower()
        for cat in EXPECTED_CATEGORIES:
            assert cat in v2


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

    def test_includes_jq_inspection_commands(self, content: str) -> None:
        # The user asked for jq commands to demystify the JSONL contents
        assert "jq" in content

    def test_explains_why_jsonl(self, content: str) -> None:
        # Per request: explain why JSONL chosen as the dataset format
        assert "jsonl" in content.lower()

    def test_under_size_budget(self, content: str) -> None:
        # DEMO_GUIDE.md: keep talking_points.txt under 7KB
        assert len(content.encode()) < 7000


# ---------------------------------------------------------------------------
# Live behavior — v1 outperforms v2 on this dataset
# ---------------------------------------------------------------------------

@pytest.mark.live
class TestLiveBehavior:
    def test_v1_accuracy_higher_than_v2(self) -> None:
        # Add scripts/ to path so we can import eval
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

        # v1 should be at least as accurate; ideally strictly better
        assert v1_summary["accuracy"] >= v2_summary["accuracy"]
        # And v1 should be solidly accurate on this curated dataset
        assert v1_summary["accuracy"] >= 0.75

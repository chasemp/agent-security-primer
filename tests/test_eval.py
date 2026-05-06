"""Tests for scripts/eval.py — golden dataset eval runner.

eval.py loads a JSONL dataset of {input, expected} pairs, runs each input
through a system prompt, scores responses against expected values, and
reports accuracy.

These tests verify mechanics with a fake send_fn — no API calls.
A separate @pytest.mark.live test verifies the end-to-end path.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

import pytest

import eval as eval_mod


@pytest.fixture
def tmp_jsonl(tmp_path: Path) -> Path:
    """Write a small JSONL file with three entries."""
    path = tmp_path / "golden.jsonl"
    entries = [
        {"input": "I miss home a lot.", "expected": "homesick"},
        {"input": "We went kayaking today.", "expected": "adventure"},
        {"input": "Made three new friends in cabin.", "expected": "friendship"},
    ]
    path.write_text("\n".join(json.dumps(e) for e in entries) + "\n")
    return path


# ---------------------------------------------------------------------------
# load_golden
# ---------------------------------------------------------------------------

class TestLoadGolden:
    def test_parses_jsonl_into_list(self, tmp_jsonl: Path) -> None:
        entries = eval_mod.load_golden(tmp_jsonl)
        assert len(entries) == 3
        assert entries[0]["expected"] == "homesick"

    def test_each_entry_has_input_and_expected(self, tmp_jsonl: Path) -> None:
        entries = eval_mod.load_golden(tmp_jsonl)
        for e in entries:
            assert "input" in e
            assert "expected" in e

    def test_missing_expected_raises(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.jsonl"
        bad.write_text(json.dumps({"input": "no expected field"}) + "\n")
        with pytest.raises(ValueError, match="expected"):
            eval_mod.load_golden(bad)

    def test_blank_lines_ignored(self, tmp_path: Path) -> None:
        path = tmp_path / "blanks.jsonl"
        path.write_text(
            json.dumps({"input": "x", "expected": "homesick"}) + "\n"
            "\n"
            + json.dumps({"input": "y", "expected": "growth"}) + "\n"
        )
        entries = eval_mod.load_golden(path)
        assert len(entries) == 2


# ---------------------------------------------------------------------------
# score_response — case-insensitive substring match
# ---------------------------------------------------------------------------

class TestScoreResponse:
    def test_exact_match_scores_true(self) -> None:
        assert eval_mod.score_response("homesick", "homesick") is True

    def test_case_insensitive(self) -> None:
        assert eval_mod.score_response("HOMESICK", "homesick") is True
        assert eval_mod.score_response("Homesick", "homesick") is True

    def test_substring_match(self) -> None:
        # Model might return "The mood is homesick." with extra text
        assert eval_mod.score_response("The mood is homesick.", "homesick") is True

    def test_unrelated_response_scores_false(self) -> None:
        assert eval_mod.score_response("adventure", "homesick") is False

    def test_partial_word_does_not_match(self) -> None:
        # "home" should NOT match "homesick" — require word boundary
        assert eval_mod.score_response("home", "homesick") is False


# ---------------------------------------------------------------------------
# run_eval — calls send_fn for each entry, collects results
# ---------------------------------------------------------------------------

def make_fake_send(predictions: list[str]) -> Callable[[str, str], dict]:
    """Build a fake send_fn that returns predictions in order."""
    iter_predictions = iter(predictions)

    def fake_send(system_prompt: str, user_content: str) -> dict:
        return {
            "text": next(iter_predictions),
            "input_tokens": 10,
            "output_tokens": 2,
            "cost_usd": 0.0001,
        }

    return fake_send


class TestRunEval:
    def test_returns_one_result_per_entry(self, tmp_jsonl: Path) -> None:
        golden = eval_mod.load_golden(tmp_jsonl)
        send = make_fake_send(["homesick", "adventure", "friendship"])
        results = eval_mod.run_eval(golden, "system prompt", send)
        assert len(results) == 3

    def test_each_result_has_prediction_and_correct(self, tmp_jsonl: Path) -> None:
        golden = eval_mod.load_golden(tmp_jsonl)
        send = make_fake_send(["homesick", "adventure", "friendship"])
        results = eval_mod.run_eval(golden, "system prompt", send)
        for r in results:
            assert "prediction" in r
            assert "correct" in r
            assert "expected" in r

    def test_marks_correct_predictions(self, tmp_jsonl: Path) -> None:
        golden = eval_mod.load_golden(tmp_jsonl)
        send = make_fake_send(["homesick", "adventure", "friendship"])
        results = eval_mod.run_eval(golden, "system prompt", send)
        assert all(r["correct"] for r in results)

    def test_marks_wrong_predictions(self, tmp_jsonl: Path) -> None:
        golden = eval_mod.load_golden(tmp_jsonl)
        send = make_fake_send(["food", "adventure", "growth"])
        results = eval_mod.run_eval(golden, "system prompt", send)
        assert results[0]["correct"] is False
        assert results[1]["correct"] is True
        assert results[2]["correct"] is False


# ---------------------------------------------------------------------------
# summarize — accuracy and per-category breakdown
# ---------------------------------------------------------------------------

class TestSummarize:
    def test_accuracy_calculated(self) -> None:
        results = [
            {"expected": "a", "prediction": "a", "correct": True},
            {"expected": "b", "prediction": "b", "correct": True},
            {"expected": "c", "prediction": "x", "correct": False},
            {"expected": "d", "prediction": "x", "correct": False},
        ]
        summary = eval_mod.summarize(results)
        assert summary["total"] == 4
        assert summary["correct"] == 2
        assert summary["accuracy"] == 0.5

    def test_perfect_score(self) -> None:
        results = [{"expected": "a", "prediction": "a", "correct": True}]
        summary = eval_mod.summarize(results)
        assert summary["accuracy"] == 1.0

    def test_includes_per_category_breakdown(self) -> None:
        results = [
            {"expected": "homesick", "prediction": "homesick", "correct": True},
            {"expected": "homesick", "prediction": "food", "correct": False},
            {"expected": "growth", "prediction": "growth", "correct": True},
        ]
        summary = eval_mod.summarize(results)
        assert "by_category" in summary
        assert summary["by_category"]["homesick"] == {"total": 2, "correct": 1}
        assert summary["by_category"]["growth"] == {"total": 1, "correct": 1}


# ---------------------------------------------------------------------------
# format_report — human-readable output
# ---------------------------------------------------------------------------

class TestScoreProcess:
    """Process score: does the response show its work?

    Three independent markers — each is a yes/no:
      shows_arithmetic: at least one operator like +, -, ×, *, /
      shows_intermediate_value: at least 3 distinct numbers
      shows_reasoning_steps: contains step/then/first/next/so/therefore/= markers

    Returns dict with per-marker booleans and aggregate score (0-3).
    """

    def test_terse_answer_scores_zero(self) -> None:
        result = eval_mod.score_process("15")
        assert result["passed"] == 0
        assert result["total"] == 3

    def test_arithmetic_scores_high(self) -> None:
        result = eval_mod.score_process("3 + 5 + 7 = 15")
        assert result["checks"]["shows_arithmetic"] is True
        assert result["checks"]["shows_intermediate_value"] is True

    def test_step_words_score_reasoning(self) -> None:
        result = eval_mod.score_process(
            "First, week 1 had 3 letters. Then week 2 had 5. So total is 15."
        )
        assert result["checks"]["shows_reasoning_steps"] is True

    def test_full_reasoning_passes_all_three(self) -> None:
        result = eval_mod.score_process(
            "Step 1: week 1 had 3 letters. Step 2: week 2 had 5. "
            "So 3 + 5 + 7 = 15. Final answer: 15."
        )
        assert result["passed"] == 3

    def test_unicode_multiplication_sign(self) -> None:
        result = eval_mod.score_process("8 × 2 = 16")
        assert result["checks"]["shows_arithmetic"] is True

    def test_passed_total_consistent(self) -> None:
        result = eval_mod.score_process("just 42")
        assert result["passed"] == sum(1 for v in result["checks"].values() if v)
        assert result["total"] == len(result["checks"])


class TestRunEvalIncludesProcess:
    def test_each_result_has_process_score(self, tmp_jsonl: Path) -> None:
        golden = eval_mod.load_golden(tmp_jsonl)
        send = make_fake_send(["3 + 5 + 7 = 15", "homesick", "homesick"])
        results = eval_mod.run_eval(golden, "system prompt", send)
        for r in results:
            assert "process" in r
            assert "checks" in r["process"]
            assert "passed" in r["process"]


class TestSummarizeIncludesProcess:
    def test_aggregate_process_score(self) -> None:
        results = [
            {"expected": "a", "prediction": "a", "correct": True,
             "process": {"checks": {"x": True, "y": True, "z": True}, "passed": 3, "total": 3}},
            {"expected": "b", "prediction": "b", "correct": True,
             "process": {"checks": {"x": True, "y": False, "z": False}, "passed": 1, "total": 3}},
        ]
        summary = eval_mod.summarize(results)
        # Process score: average passed/total across entries
        assert "process" in summary
        # Total possible: 2 entries * 3 checks = 6. Passed: 3+1 = 4.
        assert summary["process"]["passed"] == 4
        assert summary["process"]["total"] == 6


class TestFormatReportShowsProcess:
    def test_report_includes_process_line(self) -> None:
        results = [
            {"input": "x", "expected": "15", "prediction": "15", "correct": True,
             "process": {"checks": {"shows_arithmetic": False,
                                    "shows_intermediate_value": False,
                                    "shows_reasoning_steps": False},
                         "passed": 0, "total": 3}},
        ]
        summary = eval_mod.summarize(results)
        report = eval_mod.format_report(results, summary, show_process=True)
        assert "process" in report.lower() or "PROCESS" in report


class TestFormatReport:
    def test_includes_accuracy_percentage(self) -> None:
        results = [
            {"input": "x", "expected": "a", "prediction": "a", "correct": True},
            {"input": "y", "expected": "b", "prediction": "x", "correct": False},
        ]
        summary = eval_mod.summarize(results)
        report = eval_mod.format_report(results, summary)
        assert "50%" in report or "50.0%" in report

    def test_includes_per_entry_results(self) -> None:
        results = [
            {"input": "test letter", "expected": "homesick",
             "prediction": "homesick", "correct": True},
        ]
        summary = eval_mod.summarize(results)
        report = eval_mod.format_report(results, summary)
        assert "homesick" in report

    def test_marks_wrong_entries_visibly(self) -> None:
        results = [
            {"input": "x", "expected": "homesick", "prediction": "food", "correct": False},
        ]
        summary = eval_mod.summarize(results)
        report = eval_mod.format_report(results, summary)
        # Should distinguish wrong from right somehow
        assert "homesick" in report and "food" in report

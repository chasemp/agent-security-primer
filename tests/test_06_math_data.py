"""Tests for Demo 3: Why LLMs are bad at math.

Four variants — one conceptual, three operational:
  counting/           — letter counting (explains the mechanism)
  arithmetic/         — large multiplication (raw failure)
  compound_interest/  — investment planning (wrong by $300-400)
  tax_bracket/        — tax calculation ($3,600 spread on same input)
"""

import json
from pathlib import Path

import pytest

DEMO_DIR = Path(__file__).parent.parent / "demos" / "06_math"

VARIANTS = ["counting", "arithmetic", "compound_interest", "tax_bracket"]


class TestFileStructure:
    def test_system_prompt_exists(self) -> None:
        assert (DEMO_DIR / "system_prompt.txt").exists()

    @pytest.mark.parametrize("variant", VARIANTS)
    def test_question_exists(self, variant: str) -> None:
        assert (DEMO_DIR / variant / "question.txt").exists()

    @pytest.mark.parametrize("variant", VARIANTS)
    def test_answer_exists(self, variant: str) -> None:
        assert (DEMO_DIR / variant / "answer.json").exists()

    @pytest.mark.parametrize("variant", VARIANTS)
    def test_answer_has_correct_value(self, variant: str) -> None:
        content = json.loads((DEMO_DIR / variant / "answer.json").read_text())
        assert "correct_answer" in content
        assert "explanation" in content


class TestCounting:
    def test_question_asks_about_counting(self) -> None:
        content = (DEMO_DIR / "counting" / "question.txt").read_text()
        assert "how many" in content.lower()


class TestArithmetic:
    def test_question_involves_multiplication_or_large_numbers(self) -> None:
        content = (DEMO_DIR / "arithmetic" / "question.txt").read_text()
        assert any(c in content for c in ["×", "*", "multiply"])


class TestCompoundInterest:
    def test_question_involves_interest(self) -> None:
        content = (DEMO_DIR / "compound_interest" / "question.txt").read_text()
        content_lower = content.lower()
        assert "interest" in content_lower
        assert "compound" in content_lower


class TestTaxBracket:
    def test_question_has_multiple_brackets(self) -> None:
        content = (DEMO_DIR / "tax_bracket" / "question.txt").read_text()
        assert content.count("%") >= 3

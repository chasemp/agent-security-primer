"""Tests for Confidence demo — it sounds right even when it's wrong.

Two questions: one the model gets right, one it gets wrong. The
output tone is identical. There's no uncertainty signal — the model
doesn't hedge more when it's wrong. 'I think' is prediction, not
calibrated confidence.
"""

from pathlib import Path

DEMO_DIR = Path(__file__).parent.parent / "demos" / "04_confidence"


class TestFileStructure:
    def test_system_prompt_exists(self) -> None:
        assert (DEMO_DIR / "system_prompt.txt").exists()

    def test_correct_question_exists(self) -> None:
        """A question the model reliably gets right."""
        assert (DEMO_DIR / "question_correct.txt").exists()

    def test_wrong_question_exists(self) -> None:
        """A question the model reliably gets wrong."""
        assert (DEMO_DIR / "question_wrong.txt").exists()

    def test_answers_exist(self) -> None:
        """Known correct answers for both questions."""
        assert (DEMO_DIR / "answers.txt").exists()

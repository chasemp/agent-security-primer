"""Tests for Demo 18 (Few-Shot Pattern Learning) data files.

This demo shows that giving the model examples improves its predictions.
Four audience variants: technical, expenses, contract, resume.
Each has zero/one/three-shot progression and a transform file.

Uses ask_claude.py — single-turn, stdin piped input.
"""

from pathlib import Path

import pytest

DEMO_DIR = Path(__file__).parent.parent / "demos" / "18_few_shot"
VARIANTS = ["technical", "expenses", "contract", "resume"]


# ---------------------------------------------------------------------------
# File structure — all variants
# ---------------------------------------------------------------------------

class TestFileStructure:
    def test_talking_points_exists(self) -> None:
        assert (DEMO_DIR / "talking_points.txt").exists()

    @pytest.mark.parametrize("variant", VARIANTS)
    def test_system_prompt_exists(self, variant: str) -> None:
        assert (DEMO_DIR / variant / "system_prompt.txt").exists()

    @pytest.mark.parametrize("variant", VARIANTS)
    def test_zero_shot_exists(self, variant: str) -> None:
        assert (DEMO_DIR / variant / "zero_shot.txt").exists()

    @pytest.mark.parametrize("variant", VARIANTS)
    def test_one_shot_exists(self, variant: str) -> None:
        assert (DEMO_DIR / variant / "one_shot.txt").exists()

    @pytest.mark.parametrize("variant", VARIANTS)
    def test_three_shot_exists(self, variant: str) -> None:
        assert (DEMO_DIR / variant / "three_shot.txt").exists()

    @pytest.mark.parametrize("variant", VARIANTS)
    def test_transform_exists(self, variant: str) -> None:
        assert (DEMO_DIR / variant / "transform.txt").exists()


# ---------------------------------------------------------------------------
# Content: the progression from zero-shot to three-shot
# ---------------------------------------------------------------------------

class TestShotProgression:
    @pytest.mark.parametrize("variant", VARIANTS)
    def test_system_prompt_is_minimal(self, variant: str) -> None:
        content = (DEMO_DIR / variant / "system_prompt.txt").read_text()
        assert len(content.strip()) < 200

    @pytest.mark.parametrize("variant", VARIANTS)
    def test_zero_shot_has_no_examples(self, variant: str) -> None:
        content = (DEMO_DIR / variant / "zero_shot.txt").read_text()
        assert content.count("→") == 0

    @pytest.mark.parametrize("variant", VARIANTS)
    def test_one_shot_has_one_example(self, variant: str) -> None:
        content = (DEMO_DIR / variant / "one_shot.txt").read_text()
        assert content.count("→") == 1

    @pytest.mark.parametrize("variant", VARIANTS)
    def test_three_shot_has_three_examples(self, variant: str) -> None:
        content = (DEMO_DIR / variant / "three_shot.txt").read_text()
        assert content.count("→") == 3

    @pytest.mark.parametrize("variant", VARIANTS)
    def test_all_variants_share_test_question(self, variant: str) -> None:
        """The test input should be the same across zero/one/three shot."""
        zero = (DEMO_DIR / variant / "zero_shot.txt").read_text()
        one = (DEMO_DIR / variant / "one_shot.txt").read_text()
        three = (DEMO_DIR / variant / "three_shot.txt").read_text()
        zero_last = [l for l in zero.strip().splitlines() if l.strip()][-1]
        one_last = [l for l in one.strip().splitlines() if l.strip()][-1]
        three_last = [l for l in three.strip().splitlines() if l.strip()][-1]
        assert zero_last == one_last == three_last


# ---------------------------------------------------------------------------
# Transform: different transformation per variant
# ---------------------------------------------------------------------------

class TestTransform:
    @pytest.mark.parametrize("variant", VARIANTS)
    def test_transform_has_examples(self, variant: str) -> None:
        content = (DEMO_DIR / variant / "transform.txt").read_text()
        assert content.count("→") >= 2

    @pytest.mark.parametrize("variant", VARIANTS)
    def test_transform_is_different_from_main(self, variant: str) -> None:
        three = (DEMO_DIR / variant / "three_shot.txt").read_text()
        transform = (DEMO_DIR / variant / "transform.txt").read_text()
        three_output = three.split("→")[1].split("\n")[0].strip()
        transform_output = transform.split("→")[1].split("\n")[0].strip()
        assert three_output != transform_output


# ---------------------------------------------------------------------------
# Talking points
# ---------------------------------------------------------------------------

class TestTalkingPoints:
    def test_mentions_prediction(self) -> None:
        content = (DEMO_DIR / "talking_points.txt").read_text().lower()
        assert "predict" in content

    def test_mentions_few_shot(self) -> None:
        content = (DEMO_DIR / "talking_points.txt").read_text().lower()
        assert "few-shot" in content or "few shot" in content

    def test_mentions_zero_shot(self) -> None:
        content = (DEMO_DIR / "talking_points.txt").read_text().lower()
        assert "zero-shot" in content or "zero shot" in content

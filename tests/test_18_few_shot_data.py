"""Tests for Demo 18 (Few-Shot Pattern Learning) data files.

This demo shows that giving the model examples improves its predictions.
The audience watches accuracy improve from zero-shot (ambiguous) to
three-shot (nails it), then sees the model learn a completely new
transformation (fiscal quarters) from examples alone.

Uses ask_claude.py — single-turn, stdin piped input.
"""

from pathlib import Path

import pytest

DEMO_DIR = Path(__file__).parent.parent / "demos" / "18_few_shot"


# ---------------------------------------------------------------------------
# File structure
# ---------------------------------------------------------------------------

class TestFileStructure:
    def test_system_prompt_exists(self) -> None:
        assert (DEMO_DIR / "system_prompt.txt").exists()

    def test_zero_shot_exists(self) -> None:
        assert (DEMO_DIR / "zero_shot.txt").exists()

    def test_one_shot_exists(self) -> None:
        assert (DEMO_DIR / "one_shot.txt").exists()

    def test_three_shot_exists(self) -> None:
        assert (DEMO_DIR / "three_shot.txt").exists()

    def test_transform_exists(self) -> None:
        """A different transformation learned from examples alone."""
        assert (DEMO_DIR / "transform.txt").exists()

    def test_talking_points_exists(self) -> None:
        assert (DEMO_DIR / "talking_points.txt").exists()


# ---------------------------------------------------------------------------
# Content: the progression from zero-shot to three-shot
# ---------------------------------------------------------------------------

class TestShotProgression:
    """Each file adds more examples. The test question should be the same
    across all variants so the audience sees the ONLY variable is context."""

    def test_system_prompt_is_minimal(self) -> None:
        """Simple demos use short system prompts — no over-engineering."""
        content = (DEMO_DIR / "system_prompt.txt").read_text()
        assert len(content.strip()) < 200

    def test_zero_shot_has_no_examples(self) -> None:
        content = (DEMO_DIR / "zero_shot.txt").read_text()
        assert "example" not in content.lower() or content.count("→") == 0

    def test_one_shot_has_one_example(self) -> None:
        content = (DEMO_DIR / "one_shot.txt").read_text()
        # Should contain exactly one example line with → marker
        arrows = content.count("→")
        assert arrows == 1, f"Expected 1 example (→), got {arrows}"

    def test_three_shot_has_three_examples(self) -> None:
        content = (DEMO_DIR / "three_shot.txt").read_text()
        arrows = content.count("→")
        assert arrows == 3, f"Expected 3 examples (→), got {arrows}"

    def test_all_variants_share_test_question(self) -> None:
        """The test input should appear in all shot variants."""
        zero = (DEMO_DIR / "zero_shot.txt").read_text()
        one = (DEMO_DIR / "one_shot.txt").read_text()
        three = (DEMO_DIR / "three_shot.txt").read_text()
        # All should end with the same conversion request
        # Extract last non-empty line from each
        zero_last = [l for l in zero.strip().splitlines() if l.strip()][-1]
        one_last = [l for l in one.strip().splitlines() if l.strip()][-1]
        three_last = [l for l in three.strip().splitlines() if l.strip()][-1]
        assert zero_last == one_last == three_last


# ---------------------------------------------------------------------------
# Transform: a completely different transformation
# ---------------------------------------------------------------------------

class TestTransform:
    """The transform file uses a DIFFERENT transformation to show the
    model learns new rules from examples, not just memorized formats."""

    def test_transform_has_examples(self) -> None:
        content = (DEMO_DIR / "transform.txt").read_text()
        arrows = content.count("→")
        assert arrows >= 2, f"Transform should have ≥2 examples, got {arrows}"

    def test_transform_is_different_from_main(self) -> None:
        """The transformation in transform.txt should be different from
        the one in three_shot.txt."""
        three = (DEMO_DIR / "three_shot.txt").read_text()
        transform = (DEMO_DIR / "transform.txt").read_text()
        # The example outputs should look different
        # Extract the right side of the first → in each
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

"""Tests for talking_points.txt — every demo must have one.

Talking points give the presenter:
  - Background on what the demo proves
  - Q&A preparation material
  - Deeper explanations for follow-up questions
"""

from pathlib import Path

import pytest

DEMOS_DIR = Path(__file__).parent.parent / "demos"

DEMO_DIRS = [
    "01_injection",
    "02_hallucination",
    "03_math",
    "04_temperature",
    "05_thinking_aloud",
]


class TestTalkingPointsExist:
    @pytest.mark.parametrize("demo", DEMO_DIRS)
    def test_file_exists(self, demo: str) -> None:
        assert (DEMOS_DIR / demo / "talking_points.txt").exists()

    @pytest.mark.parametrize("demo", DEMO_DIRS)
    def test_is_not_empty(self, demo: str) -> None:
        content = (DEMOS_DIR / demo / "talking_points.txt").read_text()
        assert len(content.strip()) > 100

    @pytest.mark.parametrize("demo", DEMO_DIRS)
    def test_has_key_takeaway(self, demo: str) -> None:
        """Every talking points file should state the core lesson."""
        content = (DEMOS_DIR / demo / "talking_points.txt").read_text().lower()
        assert "takeaway" in content or "lesson" in content or "key point" in content

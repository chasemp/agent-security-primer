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
    "01_statelessness",
    "02_injection",
    "03_hallucination",
    "04_confidence",
    "05_sensitivity",
    "06_math",
    "07_temperature",
    "08_thinking_aloud",
    "09_plan_mode",
    "10_scoped_tool",
    "11_context_pollution",
    "12_error_translation",
    "13_credential_exposure",
    "14_credential_isolation",
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

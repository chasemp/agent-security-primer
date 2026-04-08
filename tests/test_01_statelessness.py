"""Tests for Statelessness demo — every call starts from zero.

Two API calls. The first tells the model something. The second asks
about it. The model has no idea — each call is independent. What
people experience as "memory" is their framework re-sending history.
"""

from pathlib import Path

DEMO_DIR = Path(__file__).parent.parent / "demos" / "01_statelessness"


class TestFileStructure:
    def test_system_prompt_exists(self) -> None:
        assert (DEMO_DIR / "system_prompt.txt").exists()

    def test_call1_exists(self) -> None:
        assert (DEMO_DIR / "call1.txt").exists()

    def test_call2_exists(self) -> None:
        assert (DEMO_DIR / "call2.txt").exists()

    def test_call1_provides_information(self) -> None:
        """First call tells the model something specific to remember."""
        content = (DEMO_DIR / "call1.txt").read_text()
        assert len(content.strip()) > 10

    def test_call2_asks_about_it(self) -> None:
        """Second call asks about what was said in the first."""
        content = (DEMO_DIR / "call2.txt").read_text()
        assert "?" in content

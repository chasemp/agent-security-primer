"""Tests for Prompt Sensitivity demo — wording is load-bearing.

Same question, three different phrasings. The model produces
different answers because different tokens produce different
probability distributions. This isn't a bug — it's the mechanism.
"""

from pathlib import Path

DEMO_DIR = Path(__file__).parent.parent / "demos" / "05_sensitivity"


class TestFileStructure:
    def test_system_prompt_exists(self) -> None:
        assert (DEMO_DIR / "system_prompt.txt").exists()

    def test_has_at_least_three_phrasings(self) -> None:
        """At least three different ways to ask the same question."""
        txt_files = list(DEMO_DIR.glob("phrasing_*.txt"))
        assert len(txt_files) >= 3

    def test_phrasings_ask_the_same_thing(self) -> None:
        """All phrasings should be about the same topic."""
        phrasings = [f.read_text() for f in sorted(DEMO_DIR.glob("phrasing_*.txt"))]
        # They should share at least one keyword
        first_words = set(phrasings[0].lower().split())
        for p in phrasings[1:]:
            overlap = first_words & set(p.lower().split())
            assert len(overlap) >= 1, f"Phrasings seem unrelated: {phrasings}"

    def test_phrasings_are_different(self) -> None:
        """The phrasings must be meaningfully different, not identical."""
        phrasings = [f.read_text().strip() for f in sorted(DEMO_DIR.glob("phrasing_*.txt"))]
        assert len(set(phrasings)) == len(phrasings), "Phrasings should all be unique"

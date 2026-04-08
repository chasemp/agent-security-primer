"""Tests for Demo 4: Temperature — the model is deterministic, the inference layer is not.

Same question run multiple times:
  temperature=0  → identical output every time (deterministic)
  temperature=1  → different output every time (sampling randomness)

The model weights don't change. Temperature controls the sampling
layer that sits on top of the model's probability distribution.
"""

from pathlib import Path

DEMO_DIR = Path(__file__).parent.parent / "demos" / "04_temperature"


class TestFileStructure:
    def test_system_prompt_exists(self) -> None:
        assert (DEMO_DIR / "system_prompt.txt").exists()

    def test_question_exists(self) -> None:
        assert (DEMO_DIR / "question.txt").exists()

    def test_question_is_nontrivial(self) -> None:
        """The question should produce enough output that variation
        at temperature>0 is visible."""
        content = (DEMO_DIR / "question.txt").read_text()
        assert len(content.strip()) > 20

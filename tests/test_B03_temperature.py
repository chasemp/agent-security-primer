"""Tests for Temperature demo — same model, different sampling.

Reuses charmodel.py with --temperature flag. No new script needed.
Shows that the model is deterministic; temperature changes the
sampling, not the model.

Cost: $0.00 — no API calls, runs locally.
Dependencies: PyTorch
"""

import sys
from pathlib import Path

import pytest

DEMO_DIR = Path(__file__).parent.parent / "demos" / "B03_temperature"
CORPUS_DIR = Path(__file__).parent.parent / "corpus"
SCRIPT = Path(__file__).parent.parent / "scripts" / "charmodel.py"
CHECKPOINT = CORPUS_DIR / "charmodel.pt"
PYTHON = sys.executable


def _has_torch() -> bool:
    try:
        import torch  # noqa: F401
        return True
    except ImportError:
        return False


requires_torch = pytest.mark.skipif(not _has_torch(), reason="PyTorch not installed")


# ---------------------------------------------------------------------------
# File structure
# ---------------------------------------------------------------------------

class TestFileStructure:
    def test_talking_points_exists(self) -> None:
        assert (DEMO_DIR / "talking_points.txt").exists()

    def test_charmodel_script_exists(self) -> None:
        """B03 reuses charmodel.py — no new script."""
        assert SCRIPT.exists()

    def test_temperature_asset_exists(self) -> None:
        assets = Path(__file__).parent.parent / "demos" / "assets"
        assert (assets / "temperature_comparison.txt").exists()


# ---------------------------------------------------------------------------
# Unit tests — temperature behavior
# ---------------------------------------------------------------------------

@requires_torch
class TestTemperatureBehavior:
    @pytest.fixture
    def charmodel_module(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("charmodel", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    @pytest.fixture
    def trained_model(self, charmodel_module):
        """A model trained enough to have non-uniform distributions."""
        text = "Dear Mom I miss you so much. Love Sophie. Dear Dad camp is fun. Love Jordan. " * 50
        vocab = charmodel_module.build_vocab(text)
        model = charmodel_module.CharModel(
            vocab_size=len(vocab["char_to_idx"]),
            hidden_size=64,
            num_layers=1,
        )
        charmodel_module.train_model(model, text, vocab, epochs=50, seq_len=32, lr=0.01)
        return model, vocab

    def test_low_temperature_is_deterministic(self, charmodel_module, trained_model) -> None:
        """At very low temperature, same seed should produce same output."""
        model, vocab = trained_model
        r1 = charmodel_module.generate_text(model, vocab, num_chars=100, temperature=0.01, seed=42)
        r2 = charmodel_module.generate_text(model, vocab, num_chars=100, temperature=0.01, seed=42)
        assert r1 == r2

    def test_low_temperature_ignores_seed(self, charmodel_module, trained_model) -> None:
        """At very low temperature, different seeds should still produce
        very similar output (greedy decoding)."""
        model, vocab = trained_model
        r1 = charmodel_module.generate_text(model, vocab, num_chars=100, temperature=0.01, seed=1)
        r2 = charmodel_module.generate_text(model, vocab, num_chars=100, temperature=0.01, seed=999)
        # With temp near 0, greedy decoding should dominate over seed
        # Allow some difference but expect high overlap
        overlap = sum(a == b for a, b in zip(r1, r2))
        assert overlap > 80, f"Expected high overlap at low temp, got {overlap}/100"

    def test_different_temperatures_produce_different_output(self, charmodel_module, trained_model) -> None:
        """Same seed, different temperatures should produce different text."""
        model, vocab = trained_model
        low = charmodel_module.generate_text(model, vocab, num_chars=200, temperature=0.1, seed=42)
        high = charmodel_module.generate_text(model, vocab, num_chars=200, temperature=1.5, seed=42)
        assert low != high

    def test_high_temperature_has_more_variety(self, charmodel_module, trained_model) -> None:
        """Higher temperature should produce more unique characters."""
        model, vocab = trained_model
        low = charmodel_module.generate_text(model, vocab, num_chars=300, temperature=0.1, seed=42)
        high = charmodel_module.generate_text(model, vocab, num_chars=300, temperature=1.5, seed=42)
        unique_low = len(set(low))
        unique_high = len(set(high))
        assert unique_high >= unique_low, (
            f"Expected more variety at high temp: low={unique_low}, high={unique_high}"
        )


# ---------------------------------------------------------------------------
# Live tests — full presenter flow
# ---------------------------------------------------------------------------

@requires_torch
class TestTemperatureLive:
    @pytest.fixture(autouse=True)
    def ensure_trained_model(self) -> None:
        """Train a model if no checkpoint exists."""
        import subprocess
        if not CHECKPOINT.exists():
            subprocess.run(
                [PYTHON, str(CORPUS_DIR / "build_corpus.py")],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                [PYTHON, str(SCRIPT), str(CORPUS_DIR / "camp_letters.txt"),
                 "--train", "--epochs", "50", "--reset"],
                check=True,
                capture_output=True,
                timeout=120,
            )

    @pytest.mark.live
    def test_generate_at_multiple_temperatures(self) -> None:
        """Run the full presenter flow: generate at 5 temperature values."""
        import subprocess
        temperatures = ["0.01", "0.5", "1.0", "1.5", "2.5"]
        outputs = []
        for temp in temperatures:
            result = subprocess.run(
                [PYTHON, str(SCRIPT), str(CORPUS_DIR / "camp_letters.txt"),
                 "--generate", "--chars", "100", "--temperature", temp, "--seed", "42"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            assert result.returncode == 0, f"Failed at temp={temp}: {result.stderr}"
            outputs.append(result.stdout.strip())

        # Low temp output should differ from high temp output
        assert outputs[0] != outputs[-1], "Lowest and highest temp produced same output"

        # Each output should have content
        for i, output in enumerate(outputs):
            assert len(output) > 50, f"Temp {temperatures[i]} produced too little output"

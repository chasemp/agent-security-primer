"""Tests for Character-Level Model demo — watch a neural network learn.

Train a tiny character-level model on camp letters. Watch loss decrease.
Generate text that goes from random noise to camp-letter-shaped output.

Cost: $0.00 — no API calls, runs locally.
Dependencies: PyTorch
"""

import sys
from pathlib import Path

import pytest

DEMO_DIR = Path(__file__).parent.parent / "demos" / "B02_character_model"
CORPUS_DIR = Path(__file__).parent.parent / "corpus"
SCRIPT = Path(__file__).parent.parent / "scripts" / "charmodel.py"
CHECKPOINT = CORPUS_DIR / "charmodel.pt"
PYTHON = sys.executable  # Use the same python that's running the tests


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

    def test_script_exists(self) -> None:
        assert SCRIPT.exists()

    def test_corpus_exists(self) -> None:
        assert (CORPUS_DIR / "camp_letters.txt").exists() or \
               len(list((CORPUS_DIR / "camp_letters.d").glob("*/*.txt"))) > 0


# ---------------------------------------------------------------------------
# Model architecture unit tests
# ---------------------------------------------------------------------------

@requires_torch
class TestModelArchitecture:
    @pytest.fixture
    def charmodel_module(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("charmodel", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_build_vocab_from_text(self, charmodel_module) -> None:
        vocab = charmodel_module.build_vocab("abc abc")
        assert isinstance(vocab, dict)
        assert "char_to_idx" in vocab
        assert "idx_to_char" in vocab
        assert len(vocab["char_to_idx"]) == len(vocab["idx_to_char"])

    def test_vocab_covers_all_chars(self, charmodel_module) -> None:
        text = "Dear Mom, I miss you!"
        vocab = charmodel_module.build_vocab(text)
        for char in set(text):
            assert char in vocab["char_to_idx"], f"Missing char: {repr(char)}"

    def test_model_creates_with_vocab_size(self, charmodel_module) -> None:
        import torch
        vocab = charmodel_module.build_vocab("abcdef")
        model = charmodel_module.CharModel(
            vocab_size=len(vocab["char_to_idx"]),
            hidden_size=32,
            num_layers=1,
        )
        assert model is not None
        # Model should have parameters
        param_count = sum(p.numel() for p in model.parameters())
        assert param_count > 0

    def test_model_forward_returns_correct_shape(self, charmodel_module) -> None:
        import torch
        vocab_size = 10
        model = charmodel_module.CharModel(
            vocab_size=vocab_size,
            hidden_size=32,
            num_layers=1,
        )
        # Input: batch_size=1, seq_len=5
        x = torch.randint(0, vocab_size, (1, 5))
        output = model(x)
        # Output should be (batch_size, seq_len, vocab_size)
        assert output.shape == (1, 5, vocab_size)


# ---------------------------------------------------------------------------
# Training tests
# ---------------------------------------------------------------------------

@requires_torch
class TestTraining:
    @pytest.fixture
    def charmodel_module(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("charmodel", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_train_reduces_loss(self, charmodel_module) -> None:
        """After a few epochs, loss should be lower than at start."""
        text = "Dear Mom I miss you so much. Love Sophie. " * 20
        vocab = charmodel_module.build_vocab(text)
        model = charmodel_module.CharModel(
            vocab_size=len(vocab["char_to_idx"]),
            hidden_size=32,
            num_layers=1,
        )
        losses = charmodel_module.train_model(model, text, vocab, epochs=10, seq_len=32, lr=0.01)
        assert len(losses) == 10
        assert losses[-1] < losses[0], f"Loss didn't decrease: {losses[0]:.3f} -> {losses[-1]:.3f}"

    def test_train_returns_loss_per_epoch(self, charmodel_module) -> None:
        text = "Dear Mom camp is fun. Love Jordan. " * 20
        vocab = charmodel_module.build_vocab(text)
        model = charmodel_module.CharModel(
            vocab_size=len(vocab["char_to_idx"]),
            hidden_size=32,
            num_layers=1,
        )
        losses = charmodel_module.train_model(model, text, vocab, epochs=5, seq_len=32, lr=0.01)
        assert len(losses) == 5
        for loss in losses:
            assert isinstance(loss, float)
            assert loss > 0


# ---------------------------------------------------------------------------
# Generation tests
# ---------------------------------------------------------------------------

@requires_torch
class TestGeneration:
    @pytest.fixture
    def charmodel_module(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("charmodel", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    @pytest.fixture
    def trained_model(self, charmodel_module):
        """A small model trained enough to generate non-random text."""
        text = "Dear Mom I miss you so much. Love Sophie. Dear Dad camp is fun. Love Jordan. " * 50
        vocab = charmodel_module.build_vocab(text)
        model = charmodel_module.CharModel(
            vocab_size=len(vocab["char_to_idx"]),
            hidden_size=64,
            num_layers=1,
        )
        charmodel_module.train_model(model, text, vocab, epochs=50, seq_len=32, lr=0.01)
        return model, vocab

    def test_generate_returns_string(self, charmodel_module, trained_model) -> None:
        model, vocab = trained_model
        result = charmodel_module.generate_text(model, vocab, num_chars=50, seed=42)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_generate_respects_char_count(self, charmodel_module, trained_model) -> None:
        model, vocab = trained_model
        result = charmodel_module.generate_text(model, vocab, num_chars=100, seed=42)
        assert len(result) == 100

    def test_generate_deterministic_with_seed(self, charmodel_module, trained_model) -> None:
        model, vocab = trained_model
        r1 = charmodel_module.generate_text(model, vocab, num_chars=50, seed=42)
        r2 = charmodel_module.generate_text(model, vocab, num_chars=50, seed=42)
        assert r1 == r2

    def test_generate_uses_only_vocab_chars(self, charmodel_module, trained_model) -> None:
        model, vocab = trained_model
        result = charmodel_module.generate_text(model, vocab, num_chars=200, seed=42)
        valid_chars = set(vocab["char_to_idx"].keys())
        for char in result:
            assert char in valid_chars, f"Generated char {repr(char)} not in vocab"


# ---------------------------------------------------------------------------
# Live tests — full presenter flow
# ---------------------------------------------------------------------------

@requires_torch
class TestCharModelLive:
    """Run the actual charmodel script against the real corpus.

    These validate the presenter flow: build corpus, train model,
    generate text, verify output improves with training.
    """

    @pytest.fixture(autouse=True)
    def build_corpus(self) -> None:
        import subprocess
        subprocess.run(
            [PYTHON, str(CORPUS_DIR / "build_corpus.py")],
            check=True,
            capture_output=True,
        )

    @pytest.fixture(autouse=True)
    def clean_checkpoint(self) -> None:
        """Remove any existing checkpoint so training starts fresh."""
        if CHECKPOINT.exists():
            CHECKPOINT.unlink()
        yield
        if CHECKPOINT.exists():
            CHECKPOINT.unlink()

    @pytest.mark.live
    def test_train_runs_and_reports_loss(self) -> None:
        import subprocess
        result = subprocess.run(
            [PYTHON, str(SCRIPT), str(CORPUS_DIR / "camp_letters.txt"),
             "--train", "--epochs", "5", "--reset"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0
        # Should report loss for each epoch
        assert "Epoch" in result.stdout or "epoch" in result.stdout.lower()

    @pytest.mark.live
    def test_train_creates_checkpoint(self) -> None:
        import subprocess
        subprocess.run(
            [PYTHON, str(SCRIPT), str(CORPUS_DIR / "camp_letters.txt"),
             "--train", "--epochs", "5", "--reset"],
            check=True,
            capture_output=True,
            timeout=60,
        )
        assert CHECKPOINT.exists()

    @pytest.mark.live
    def test_generate_after_training_produces_text(self) -> None:
        import subprocess
        # Train first
        subprocess.run(
            [PYTHON, str(SCRIPT), str(CORPUS_DIR / "camp_letters.txt"),
             "--train", "--epochs", "20", "--reset"],
            check=True,
            capture_output=True,
            timeout=120,
        )
        # Then generate
        result = subprocess.run(
            [PYTHON, str(SCRIPT), str(CORPUS_DIR / "camp_letters.txt"),
             "--generate", "--chars", "100"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0
        assert len(result.stdout.strip()) >= 50

    @pytest.mark.live
    def test_training_improves_output(self) -> None:
        """After more training, generated text should contain more
        real words from the corpus."""
        import subprocess

        # Train briefly (5 epochs)
        subprocess.run(
            [PYTHON, str(SCRIPT), str(CORPUS_DIR / "camp_letters.txt"),
             "--train", "--epochs", "5", "--reset"],
            check=True,
            capture_output=True,
            timeout=60,
        )
        early = subprocess.run(
            [PYTHON, str(SCRIPT), str(CORPUS_DIR / "camp_letters.txt"),
             "--generate", "--chars", "200", "--seed", "42"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Train more (50 additional epochs)
        subprocess.run(
            [PYTHON, str(SCRIPT), str(CORPUS_DIR / "camp_letters.txt"),
             "--train", "--epochs", "50"],
            check=True,
            capture_output=True,
            timeout=120,
        )
        later = subprocess.run(
            [PYTHON, str(SCRIPT), str(CORPUS_DIR / "camp_letters.txt"),
             "--generate", "--chars", "200", "--seed", "42"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Count recognizable camp words in each output
        camp_words = {"dear", "mom", "dad", "camp", "love", "miss", "cabin", "lake", "fun"}

        def count_camp_words(text: str) -> int:
            return sum(1 for w in text.lower().split() if w.strip(".,!?") in camp_words)

        early_count = count_camp_words(early.stdout)
        later_count = count_camp_words(later.stdout)

        # Later output should have more recognizable words
        assert later_count >= early_count, (
            f"Expected more camp words after training: early={early_count}, later={later_count}"
        )

"""Tests for Attention demo — which tokens look at which tokens.

A small transformer trained on camp letters. Extracts and visualizes
attention weights as ASCII art.

Cost: $0.00 — no API calls, runs locally.
Dependencies: PyTorch
"""

import sys
from pathlib import Path

import pytest

DEMO_DIR = Path(__file__).parent.parent / "demos" / "B04_attention"
CORPUS_DIR = Path(__file__).parent.parent / "corpus"
SCRIPT = Path(__file__).parent.parent / "scripts" / "attention_viz.py"
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

    def test_script_exists(self) -> None:
        assert SCRIPT.exists()

    def test_attention_asset_exists(self) -> None:
        assets = Path(__file__).parent.parent / "demos" / "assets"
        assert (assets / "attention_matrix.txt").exists()


# ---------------------------------------------------------------------------
# Vocabulary and model
# ---------------------------------------------------------------------------

@requires_torch
class TestTransformerModel:
    @pytest.fixture
    def attn_module(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("attention_viz", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_build_vocab(self, attn_module) -> None:
        vocab = attn_module.build_vocab("Dear Mom I miss you")
        assert "char_to_idx" in vocab
        assert "idx_to_char" in vocab

    def test_model_creates(self, attn_module) -> None:
        vocab = attn_module.build_vocab("abcdefghij ")
        model = attn_module.MiniTransformer(
            vocab_size=len(vocab["char_to_idx"]),
            n_embd=32,
            n_head=2,
            n_layer=2,
            block_size=64,
        )
        param_count = sum(p.numel() for p in model.parameters())
        assert param_count > 0

    def test_forward_returns_correct_shape(self, attn_module) -> None:
        import torch
        vocab_size = 20
        model = attn_module.MiniTransformer(
            vocab_size=vocab_size, n_embd=32, n_head=2, n_layer=2, block_size=64,
        )
        x = torch.randint(0, vocab_size, (1, 10))
        logits, _ = model(x)
        assert logits.shape == (1, 10, vocab_size)

    def test_forward_returns_attention_weights(self, attn_module) -> None:
        import torch
        vocab_size = 20
        model = attn_module.MiniTransformer(
            vocab_size=vocab_size, n_embd=32, n_head=2, n_layer=2, block_size=64,
        )
        x = torch.randint(0, vocab_size, (1, 10))
        _, attn_weights = model(x)
        # Should have weights for each layer
        assert len(attn_weights) == 2  # n_layer=2
        # Each should be (batch, n_head, seq, seq)
        assert attn_weights[0].shape == (1, 2, 10, 10)


# ---------------------------------------------------------------------------
# Attention weight properties
# ---------------------------------------------------------------------------

@requires_torch
class TestAttentionProperties:
    @pytest.fixture
    def attn_module(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("attention_viz", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_attention_weights_sum_to_one(self, attn_module) -> None:
        """Each row of attention weights should sum to ~1.0 (softmax)."""
        import torch
        vocab_size = 20
        model = attn_module.MiniTransformer(
            vocab_size=vocab_size, n_embd=32, n_head=2, n_layer=2, block_size=64,
        )
        x = torch.randint(0, vocab_size, (1, 8))
        _, attn_weights = model(x)
        # Check first layer, first head
        row_sums = attn_weights[0][0, 0].sum(dim=-1)
        for i, s in enumerate(row_sums):
            assert abs(s.item() - 1.0) < 0.01, f"Row {i} sums to {s.item()}, expected 1.0"

    def test_causal_mask_enforced(self, attn_module) -> None:
        """Upper triangle of attention weights should be zero (causal mask)."""
        import torch
        vocab_size = 20
        model = attn_module.MiniTransformer(
            vocab_size=vocab_size, n_embd=32, n_head=2, n_layer=2, block_size=64,
        )
        x = torch.randint(0, vocab_size, (1, 8))
        _, attn_weights = model(x)
        weights = attn_weights[0][0, 0]  # first layer, first head
        # Check upper triangle is zero
        for i in range(8):
            for j in range(i + 1, 8):
                assert weights[i, j].item() < 0.001, (
                    f"Position ({i},{j}) should be masked but has weight {weights[i, j].item()}"
                )


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

@requires_torch
class TestRendering:
    @pytest.fixture
    def attn_module(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("attention_viz", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_render_ascii_matrix(self, attn_module) -> None:
        import torch
        # Create a simple 4x4 attention matrix
        weights = torch.tensor([
            [1.0, 0.0, 0.0, 0.0],
            [0.5, 0.5, 0.0, 0.0],
            [0.2, 0.3, 0.5, 0.0],
            [0.1, 0.2, 0.3, 0.4],
        ])
        tokens = ["Dear", "Mom", "I", "miss"]
        output = attn_module.render_ascii_matrix(weights, tokens)
        assert isinstance(output, str)
        assert "Dear" in output
        assert "Mom" in output

    def test_render_causal_mask(self, attn_module) -> None:
        output = attn_module.render_causal_mask(5)
        assert isinstance(output, str)
        assert "1" in output
        # Should have the triangular pattern


# ---------------------------------------------------------------------------
# Live tests
# ---------------------------------------------------------------------------

@requires_torch
class TestAttentionLive:
    @pytest.fixture(autouse=True)
    def build_corpus(self) -> None:
        import subprocess
        subprocess.run(
            [PYTHON, str(CORPUS_DIR / "build_corpus.py")],
            check=True,
            capture_output=True,
        )

    @pytest.mark.live
    def test_train_and_visualize(self) -> None:
        """Train a small transformer and visualize attention."""
        import subprocess
        result = subprocess.run(
            [PYTHON, str(SCRIPT), "Dear Mom I miss you",
             "--train", str(CORPUS_DIR / "camp_letters.txt"),
             "--epochs", "5"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0
        # Output should contain character-level token labels and attention indicators
        # (character-level model uses individual chars: D, e, a, r not "Dear")
        assert "D" in result.stdout and "Attention" in result.stdout

    @pytest.mark.live
    def test_show_mask(self) -> None:
        """Display the causal mask."""
        import subprocess
        result = subprocess.run(
            [PYTHON, str(SCRIPT), "Dear Mom I miss you", "--mask"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0
        assert "1" in result.stdout

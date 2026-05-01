#!/usr/bin/env python3
"""Attention visualization — see which tokens look at which tokens.

A tiny transformer trained on camp letters. Extracts attention weights
and renders them as ASCII art in the terminal.

Usage:
    python scripts/attention_viz.py "Dear Mom I miss you" --train corpus/camp_letters.txt --epochs 20
    python scripts/attention_viz.py "Dear Mom I miss you"
    python scripts/attention_viz.py "Dear Mom I miss you" --heads
    python scripts/attention_viz.py "Dear Mom I miss you" --mask
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import Optional

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


# ---------------------------------------------------------------------------
# Vocabulary (same interface as charmodel.py)
# ---------------------------------------------------------------------------

def build_vocab(text: str) -> dict:
    """Build character-to-index and index-to-character mappings."""
    chars = sorted(set(text))
    char_to_idx = {ch: i for i, ch in enumerate(chars)}
    idx_to_char = {i: ch for i, ch in enumerate(chars)}
    return {"char_to_idx": char_to_idx, "idx_to_char": idx_to_char}


# ---------------------------------------------------------------------------
# Mini Transformer (with attention weight capture)
# ---------------------------------------------------------------------------

if HAS_TORCH:
    class CausalSelfAttention(nn.Module):
        def __init__(self, n_embd: int, n_head: int, block_size: int):
            super().__init__()
            assert n_embd % n_head == 0
            self.n_head = n_head
            self.head_dim = n_embd // n_head
            self.c_attn = nn.Linear(n_embd, 3 * n_embd)
            self.c_proj = nn.Linear(n_embd, n_embd)
            self.register_buffer(
                "bias",
                torch.tril(torch.ones(block_size, block_size)).view(1, 1, block_size, block_size),
            )

        def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
            B, T, C = x.size()
            q, k, v = self.c_attn(x).split(C, dim=2)
            q = q.view(B, T, self.n_head, self.head_dim).transpose(1, 2)
            k = k.view(B, T, self.n_head, self.head_dim).transpose(1, 2)
            v = v.view(B, T, self.n_head, self.head_dim).transpose(1, 2)

            att = (q @ k.transpose(-2, -1)) * (1.0 / math.sqrt(self.head_dim))
            att = att.masked_fill(self.bias[:, :, :T, :T] == 0, float("-inf"))
            att = F.softmax(att, dim=-1)

            out = att @ v
            out = out.transpose(1, 2).contiguous().view(B, T, C)
            return self.c_proj(out), att

    class TransformerBlock(nn.Module):
        def __init__(self, n_embd: int, n_head: int, block_size: int):
            super().__init__()
            self.ln_1 = nn.LayerNorm(n_embd)
            self.attn = CausalSelfAttention(n_embd, n_head, block_size)
            self.ln_2 = nn.LayerNorm(n_embd)
            self.mlp = nn.Sequential(
                nn.Linear(n_embd, 4 * n_embd),
                nn.GELU(),
                nn.Linear(4 * n_embd, n_embd),
            )

        def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
            attn_out, attn_weights = self.attn(self.ln_1(x))
            x = x + attn_out
            x = x + self.mlp(self.ln_2(x))
            return x, attn_weights

    class MiniTransformer(nn.Module):
        """Tiny GPT-style transformer for attention visualization.

        Same architecture as Karpathy's microgpt.py but much smaller.
        Captures attention weights at every layer for visualization.
        """

        def __init__(
            self,
            vocab_size: int,
            n_embd: int = 64,
            n_head: int = 4,
            n_layer: int = 2,
            block_size: int = 128,
        ):
            super().__init__()
            self.block_size = block_size
            self.wte = nn.Embedding(vocab_size, n_embd)
            self.wpe = nn.Embedding(block_size, n_embd)
            self.blocks = nn.ModuleList([
                TransformerBlock(n_embd, n_head, block_size) for _ in range(n_layer)
            ])
            self.ln_f = nn.LayerNorm(n_embd)
            self.lm_head = nn.Linear(n_embd, vocab_size, bias=False)
            # Weight tying (the DNS/reverse DNS trick)
            self.wte.weight = self.lm_head.weight

        def forward(self, idx: torch.Tensor) -> tuple[torch.Tensor, list[torch.Tensor]]:
            B, T = idx.size()
            pos = torch.arange(0, T, dtype=torch.long, device=idx.device).unsqueeze(0)
            x = self.wte(idx) + self.wpe(pos)

            all_attn_weights = []
            for block in self.blocks:
                x, attn_w = block(x)
                all_attn_weights.append(attn_w)

            x = self.ln_f(x)
            logits = self.lm_head(x)
            return logits, all_attn_weights

else:
    MiniTransformer = None  # type: ignore


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def train_transformer(
    text: str,
    vocab: dict,
    n_embd: int = 64,
    n_head: int = 4,
    n_layer: int = 2,
    block_size: int = 128,
    epochs: int = 20,
    lr: float = 0.001,
) -> "MiniTransformer":
    """Train a mini transformer on text. Returns the trained model."""
    char_to_idx = vocab["char_to_idx"]
    vocab_size = len(char_to_idx)
    data = torch.tensor([char_to_idx[ch] for ch in text if ch in char_to_idx], dtype=torch.long)

    model = MiniTransformer(
        vocab_size=vocab_size, n_embd=n_embd, n_head=n_head,
        n_layer=n_layer, block_size=block_size,
    )
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    for epoch in range(epochs):
        total_loss = 0.0
        n_batches = 0
        for i in range(0, len(data) - block_size - 1, block_size):
            x = data[i:i + block_size].unsqueeze(0)
            y = data[i + 1:i + block_size + 1].unsqueeze(0)
            logits, _ = model(x)
            loss = F.cross_entropy(logits.view(-1, vocab_size), y.view(-1))
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
            n_batches += 1
        avg = total_loss / max(n_batches, 1)
        print(f"  Epoch {epoch + 1:3d}: loss {avg:.3f}")

    return model


# ---------------------------------------------------------------------------
# Attention extraction
# ---------------------------------------------------------------------------

def get_attention_weights(
    model: "MiniTransformer",
    text: str,
    vocab: dict,
) -> tuple[list[torch.Tensor], list[str]]:
    """Run forward pass and return attention weights + token labels.

    Returns (attn_weights, tokens) where:
    - attn_weights: list of tensors, one per layer, shape (1, n_head, seq, seq)
    - tokens: list of character strings for labeling
    """
    char_to_idx = vocab["char_to_idx"]
    valid_chars = [ch for ch in text if ch in char_to_idx]
    indices = torch.tensor([[char_to_idx[ch] for ch in valid_chars]], dtype=torch.long)

    model.eval()
    with torch.no_grad():
        _, attn_weights = model(indices)

    return attn_weights, valid_chars


# ---------------------------------------------------------------------------
# ASCII rendering
# ---------------------------------------------------------------------------

INTENSITY = " ░▒▓█"


def render_ascii_matrix(weights: "torch.Tensor", tokens: list[str]) -> str:
    """Render a 2D attention matrix as ASCII art.

    weights: (seq_len, seq_len) tensor
    tokens: list of strings for row/column labels
    """
    n = len(tokens)
    # Truncate labels to 5 chars for alignment
    labels = [t[:5].ljust(5) for t in tokens]

    lines = []
    # Header
    header = "       " + " ".join(f"{l}" for l in labels)
    lines.append(header)

    for i in range(n):
        row = f"{labels[i]}  "
        cells = []
        for j in range(n):
            w = weights[i, j].item()
            if j > i:
                cells.append("  ·  ")  # masked
            else:
                idx = min(int(w * len(INTENSITY)), len(INTENSITY) - 1)
                char = INTENSITY[idx]
                cells.append(f" {char}{char}{char} ")
        row += " ".join(cells)
        lines.append(row)

    return "\n".join(lines)


def render_causal_mask(size: int) -> str:
    """Render the causal mask as a simple grid."""
    lines = ["CAUSAL MASK (lower triangular):", ""]
    for i in range(size):
        row = "  "
        for j in range(size):
            row += " 1" if j <= i else " ·"
        lines.append(row)
    lines.append("")
    lines.append("  1 = can attend    · = masked (future tokens)")
    return "\n".join(lines)


def render_per_head(
    attn_weights: list["torch.Tensor"],
    tokens: list[str],
    layer: int = 0,
) -> str:
    """Render attention from each head in a given layer."""
    weights = attn_weights[layer][0]  # (n_head, seq, seq)
    n_heads = weights.shape[0]
    lines = [f"Layer {layer}, per-head attention:", ""]

    for h in range(n_heads):
        lines.append(f"  Head {h}:")
        lines.append(render_ascii_matrix(weights[h], tokens))
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Checkpoint
# ---------------------------------------------------------------------------

CHECKPOINT_PATH = Path("corpus/attention_model.pt")


def save_checkpoint(model: "MiniTransformer", vocab: dict) -> None:
    torch.save({"model_state": model.state_dict(), "vocab": vocab,
                "config": {"n_embd": 64, "n_head": 4, "n_layer": 2, "block_size": 128}},
               CHECKPOINT_PATH)


def load_checkpoint() -> tuple:
    ckpt = torch.load(CHECKPOINT_PATH, weights_only=False)
    return ckpt["model_state"], ckpt["vocab"], ckpt["config"]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    if not HAS_TORCH:
        print("Error: PyTorch is required. Install with: pip install torch", file=sys.stderr)
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Attention visualization")
    parser.add_argument("text", type=str, help="Text to visualize attention for")
    parser.add_argument("--train", type=Path, default=None, help="Train on corpus file first")
    parser.add_argument("--epochs", type=int, default=20, help="Training epochs")
    parser.add_argument("--heads", action="store_true", help="Show per-head attention")
    parser.add_argument("--mask", action="store_true", help="Show causal mask")
    parser.add_argument("--layer", type=int, default=0, help="Which layer to visualize")
    args = parser.parse_args()

    if args.mask:
        words = args.text.split()
        print(render_causal_mask(len(words)))
        return

    # Train or load model
    if args.train:
        corpus_text = args.train.read_text()
        vocab = build_vocab(corpus_text)
        print(f"Training on {len(corpus_text)} characters...")
        model = train_transformer(corpus_text, vocab, epochs=args.epochs)
        save_checkpoint(model, vocab)
        print(f"Saved to {CHECKPOINT_PATH}")
    elif CHECKPOINT_PATH.exists():
        state_dict, vocab, config = load_checkpoint()
        model = MiniTransformer(
            vocab_size=len(vocab["char_to_idx"]),
            n_embd=config["n_embd"], n_head=config["n_head"],
            n_layer=config["n_layer"], block_size=config["block_size"],
        )
        model.load_state_dict(state_dict)
        print(f"Loaded from {CHECKPOINT_PATH}")
    else:
        print("No checkpoint found. Train first with --train <corpus>", file=sys.stderr)
        sys.exit(1)

    # Visualize
    attn_weights, tokens = get_attention_weights(model, args.text, vocab)

    if args.heads:
        print(render_per_head(attn_weights, tokens, layer=args.layer))
    else:
        # Average across heads for the overview
        avg_weights = attn_weights[args.layer][0].mean(dim=0)
        print(f"\nAttention weights (layer {args.layer}, averaged across heads):")
        print(render_ascii_matrix(avg_weights, tokens))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Character-level language model — watch a neural network learn.

Train a tiny LSTM on camp letters. Generate text that goes from random
noise to camp-letter-shaped output as training progresses.

~80 lines of model code, no frameworks, no hidden complexity.

Usage:
    python scripts/charmodel.py corpus/camp_letters.txt --train --epochs 10
    python scripts/charmodel.py corpus/camp_letters.txt --generate --chars 300
    python scripts/charmodel.py corpus/camp_letters.txt --train --epochs 100 --generate
    python scripts/charmodel.py corpus/camp_letters.txt --generate --temperature 0.5
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

try:
    import torch
    import torch.nn as nn
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


# ---------------------------------------------------------------------------
# Vocabulary
# ---------------------------------------------------------------------------

def build_vocab(text: str) -> dict:
    """Build character-to-index and index-to-character mappings.

    Returns {"char_to_idx": {char: int}, "idx_to_char": {int: char}}.
    """
    chars = sorted(set(text))
    char_to_idx = {ch: i for i, ch in enumerate(chars)}
    idx_to_char = {i: ch for i, ch in enumerate(chars)}
    return {"char_to_idx": char_to_idx, "idx_to_char": idx_to_char}


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

if HAS_TORCH:
    class CharModel(nn.Module):
        """Tiny character-level LSTM. Predicts next character from sequence.

        Architecture:
          embedding -> LSTM -> linear -> softmax (via cross-entropy loss)

        Small enough to train on a laptop CPU in under 60 seconds.
        """

        def __init__(self, vocab_size: int, hidden_size: int = 64, num_layers: int = 1):
            super().__init__()
            self.hidden_size = hidden_size
            self.num_layers = num_layers
            self.embedding = nn.Embedding(vocab_size, hidden_size)
            self.lstm = nn.LSTM(hidden_size, hidden_size, num_layers, batch_first=True)
            self.fc = nn.Linear(hidden_size, vocab_size)

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            """Forward pass. x: (batch, seq_len) -> (batch, seq_len, vocab_size)."""
            emb = self.embedding(x)
            out, _ = self.lstm(emb)
            return self.fc(out)
else:
    # Placeholder so module is importable without torch
    CharModel = None  # type: ignore


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def train_model(
    model: "nn.Module",
    text: str,
    vocab: dict,
    epochs: int = 10,
    seq_len: int = 64,
    lr: float = 0.003,
    batch_size: int = 32,
) -> list[float]:
    """Train the model on text. Returns list of average loss per epoch."""
    char_to_idx = vocab["char_to_idx"]

    # Encode full text as tensor of indices
    data = torch.tensor([char_to_idx[ch] for ch in text], dtype=torch.long)

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    losses = []
    for epoch in range(epochs):
        epoch_loss = 0.0
        num_batches = 0

        # Slide a window over the text
        indices = list(range(0, len(data) - seq_len - 1, seq_len))
        # Adapt batch size to available data
        effective_batch = min(batch_size, max(1, len(indices)))
        # Simple batching: take sequential chunks
        for i in range(0, len(indices) - effective_batch + 1, effective_batch):
            batch_inputs = []
            batch_targets = []
            for j in range(effective_batch):
                start = indices[i + j]
                batch_inputs.append(data[start:start + seq_len])
                batch_targets.append(data[start + 1:start + seq_len + 1])

            x = torch.stack(batch_inputs)
            y = torch.stack(batch_targets)

            output = model(x)
            loss = criterion(output.view(-1, output.size(-1)), y.view(-1))

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            epoch_loss += loss.item()
            num_batches += 1

        avg_loss = epoch_loss / max(num_batches, 1)
        losses.append(avg_loss)

    return losses


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

def generate_text(
    model: "nn.Module",
    vocab: dict,
    num_chars: int = 300,
    temperature: float = 1.0,
    seed: Optional[int] = None,
    start_text: str = "Dear ",
) -> str:
    """Generate text character by character from the trained model."""
    if seed is not None:
        torch.manual_seed(seed)

    char_to_idx = vocab["char_to_idx"]
    idx_to_char = vocab["idx_to_char"]

    model.eval()
    # Seed with start_text (use chars that exist in vocab)
    valid_start = "".join(ch for ch in start_text if ch in char_to_idx)
    if not valid_start:
        valid_start = idx_to_char[0]

    input_seq = torch.tensor(
        [[char_to_idx[ch] for ch in valid_start]], dtype=torch.long
    )

    generated = list(valid_start)

    with torch.no_grad():
        for _ in range(num_chars - len(valid_start)):
            output = model(input_seq)
            # Take the last character's prediction
            logits = output[0, -1, :] / temperature
            probs = torch.softmax(logits, dim=0)
            next_idx = torch.multinomial(probs, 1).item()
            next_char = idx_to_char[next_idx]
            generated.append(next_char)
            # Append to input sequence
            next_tensor = torch.tensor([[next_idx]], dtype=torch.long)
            input_seq = torch.cat([input_seq, next_tensor], dim=1)
            # Keep window manageable
            if input_seq.size(1) > 200:
                input_seq = input_seq[:, -100:]

    return "".join(generated[:num_chars])


# ---------------------------------------------------------------------------
# Checkpoint save/load
# ---------------------------------------------------------------------------

def save_checkpoint(model: "nn.Module", vocab: dict, path: Path) -> None:
    """Save model weights and vocab to a file."""
    torch.save({"model_state": model.state_dict(), "vocab": vocab}, path)


def load_checkpoint(path: Path) -> tuple:
    """Load model weights and vocab. Returns (state_dict, vocab)."""
    checkpoint = torch.load(path, weights_only=False)
    return checkpoint["model_state"], checkpoint["vocab"]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

CHECKPOINT_PATH = Path("corpus/charmodel.pt")


def main() -> None:
    if not HAS_TORCH:
        print("Error: PyTorch is required. Install with: pip install torch", file=sys.stderr)
        sys.exit(1)

    parser = argparse.ArgumentParser(
        description="Character-level language model — watch it learn"
    )
    parser.add_argument("corpus", type=Path, help="Path to training corpus text file")
    parser.add_argument("--train", action="store_true", help="Train the model")
    parser.add_argument("--epochs", type=int, default=10, help="Training epochs (default: 10)")
    parser.add_argument("--generate", action="store_true", help="Generate text")
    parser.add_argument("--chars", type=int, default=300, help="Characters to generate (default: 300)")
    parser.add_argument("--temperature", type=float, default=1.0, help="Sampling temperature (default: 1.0)")
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    parser.add_argument("--reset", action="store_true", help="Delete checkpoint, start fresh")
    parser.add_argument("--hidden", type=int, default=64, help="Hidden size (default: 64)")
    parser.add_argument("--layers", type=int, default=1, help="LSTM layers (default: 1)")
    parser.add_argument("--show-loss", action="store_true", help="Print loss curve after training")
    args = parser.parse_args()

    if not args.corpus.exists():
        print(f"Error: corpus file not found: {args.corpus}", file=sys.stderr)
        sys.exit(1)

    text = args.corpus.read_text()

    if args.reset and CHECKPOINT_PATH.exists():
        CHECKPOINT_PATH.unlink()
        print("Checkpoint deleted — starting fresh.")

    # Build or load vocab
    vocab = build_vocab(text)
    vocab_size = len(vocab["char_to_idx"])

    # Create model
    model = CharModel(vocab_size=vocab_size, hidden_size=args.hidden, num_layers=args.layers)

    # Load existing checkpoint if available
    if CHECKPOINT_PATH.exists() and not args.reset:
        state_dict, saved_vocab = load_checkpoint(CHECKPOINT_PATH)
        if len(saved_vocab["char_to_idx"]) == vocab_size:
            model.load_state_dict(state_dict)
            vocab = saved_vocab
            print(f"Loaded checkpoint from {CHECKPOINT_PATH}")
        else:
            print("Vocab size changed — starting fresh.")

    if args.train:
        print(f"Training on {len(text)} characters, vocab size {vocab_size}")
        losses = train_model(
            model, text, vocab,
            epochs=args.epochs,
            seq_len=64,
            lr=0.003,
        )
        for i, loss in enumerate(losses, 1):
            print(f"  Epoch {i:4d}: loss {loss:.3f}")

        save_checkpoint(model, vocab, CHECKPOINT_PATH)
        print(f"Checkpoint saved to {CHECKPOINT_PATH}")

        if args.show_loss:
            print("\nLoss curve:")
            max_bar = 40
            max_loss = max(losses)
            for i, loss in enumerate(losses, 1):
                bar_len = int(loss / max_loss * max_bar)
                print(f"  {i:4d} |{'#' * bar_len} {loss:.3f}")

    if args.generate:
        if not CHECKPOINT_PATH.exists() and not args.train:
            print("Error: no checkpoint found. Train first with --train", file=sys.stderr)
            sys.exit(1)
        result = generate_text(
            model, vocab,
            num_chars=args.chars,
            temperature=args.temperature,
            seed=args.seed,
        )
        print(result)

    if not args.train and not args.generate:
        parser.print_help()


if __name__ == "__main__":
    main()

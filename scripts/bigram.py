#!/usr/bin/env python3
"""Bigram language model — the simplest possible text generator.

Count word pairs in a corpus. Sample the next word from those counts.
No ML libraries, no neural networks. Just counting and probability.

Usage:
    python scripts/bigram.py corpus/camp_letters.txt --table
    python scripts/bigram.py corpus/camp_letters.txt --generate --words 50
    python scripts/bigram.py corpus/camp_letters.txt --generate --words 50 --seed 42
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path
from typing import Optional


def count_bigrams(text: str) -> dict[str, dict[str, int]]:
    """Count how often each word follows each other word.

    Returns a nested dict: {word_a: {word_b: count, word_c: count, ...}}.
    """
    words = text.split()
    counts: dict[str, dict[str, int]] = {}
    for i in range(len(words) - 1):
        current = words[i]
        next_word = words[i + 1]
        if current not in counts:
            counts[current] = {}
        counts[current][next_word] = counts[current].get(next_word, 0) + 1
    return counts


def get_probabilities(counts: dict[str, dict[str, int]], word: str) -> dict[str, float]:
    """Convert raw counts for a word into probabilities that sum to 1.0."""
    if word not in counts:
        return {}
    followers = counts[word]
    total = sum(followers.values())
    return {w: c / total for w, c in followers.items()}


def top_pairs(counts: dict[str, dict[str, int]], n: int = 20) -> list[tuple[str, str, int]]:
    """Return the top N bigram pairs sorted by frequency (descending).

    Each entry is (word_a, word_b, count).
    """
    all_pairs = []
    for word_a, followers in counts.items():
        for word_b, count in followers.items():
            all_pairs.append((word_a, word_b, count))
    all_pairs.sort(key=lambda x: x[2], reverse=True)
    return all_pairs[:n]


def generate(
    counts: dict[str, dict[str, int]],
    start_word: str = "Dear",
    num_words: int = 50,
    seed: Optional[int] = None,
) -> str:
    """Generate text by sampling from bigram probabilities.

    Starts with start_word, then repeatedly samples the next word
    from the probability distribution of what follows the current word.
    Stops after num_words or when the current word has no followers.
    """
    rng = random.Random(seed)
    words = [start_word]
    current = start_word

    for _ in range(num_words - 1):
        probs = get_probabilities(counts, current)
        if not probs:
            break
        next_words = list(probs.keys())
        weights = list(probs.values())
        current = rng.choices(next_words, weights=weights, k=1)[0]
        words.append(current)

    return " ".join(words)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bigram language model — count pairs, predict next word"
    )
    parser.add_argument("corpus", type=Path, help="Path to training corpus text file")
    parser.add_argument("--table", action="store_true", help="Print top bigram pairs")
    parser.add_argument("--table-size", type=int, default=20, help="Number of pairs to show (default: 20)")
    parser.add_argument("--generate", action="store_true", help="Generate text")
    parser.add_argument("--words", type=int, default=50, help="Words to generate (default: 50)")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    parser.add_argument("--start", type=str, default="Dear", help="Starting word (default: Dear)")
    args = parser.parse_args()

    if not args.corpus.exists():
        print(f"Error: corpus file not found: {args.corpus}", file=sys.stderr)
        sys.exit(1)

    text = args.corpus.read_text()
    counts = count_bigrams(text)

    if args.table:
        pairs = top_pairs(counts, n=args.table_size)
        print(f"Top {len(pairs)} bigram pairs:")
        for word_a, word_b, count in pairs:
            probs = get_probabilities(counts, word_a)
            pct = probs.get(word_b, 0) * 100
            print(f"  {word_a:15s} -> {word_b:15s}  ({count:4d} times, {pct:5.1f}%)")

    if args.generate:
        result = generate(counts, start_word=args.start, num_words=args.words, seed=args.seed)
        print(result)

    if not args.table and not args.generate:
        parser.print_help()


if __name__ == "__main__":
    main()

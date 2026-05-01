#!/usr/bin/env python3
"""Build the combined training corpus from individual camp letters.

Usage:
    python corpus/build_corpus.py                          # all categories, ordered
    python corpus/build_corpus.py --shuffle                # all categories, randomized
    python corpus/build_corpus.py --categories arrival,homesick  # subset
    python corpus/build_corpus.py --stats                  # print category counts
"""

import argparse
import random
from pathlib import Path


CORPUS_DIR = Path(__file__).parent / "camp_letters.d"
OUTPUT_FILE = Path(__file__).parent / "camp_letters.txt"
SEPARATOR = "\n---\n"

ALL_CATEGORIES = sorted(
    d.name for d in CORPUS_DIR.iterdir() if d.is_dir() and not d.name.startswith(".")
)


def collect_letters(categories: list[str]) -> list[tuple[str, str, str]]:
    """Return list of (category, filename, content) tuples."""
    letters = []
    for category in categories:
        category_dir = CORPUS_DIR / category
        if not category_dir.exists():
            print(f"Warning: category '{category}' not found, skipping")
            continue
        for letter_file in sorted(category_dir.glob("*.txt")):
            content = letter_file.read_text().strip()
            letters.append((category, letter_file.name, content))
    return letters


def print_stats(letters: list[tuple[str, str, str]]) -> None:
    """Print category counts and total."""
    counts: dict[str, int] = {}
    for category, _, _ in letters:
        counts[category] = counts.get(category, 0) + 1

    print("Category counts:")
    for category in sorted(counts):
        print(f"  {category:15s} {counts[category]:4d}")
    print(f"  {'TOTAL':15s} {len(letters):4d}")


def build_corpus(letters: list[tuple[str, str, str]]) -> str:
    """Concatenate letters with separators."""
    return SEPARATOR.join(content for _, _, content in letters)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build camp letters training corpus")
    parser.add_argument(
        "--categories",
        type=str,
        default=None,
        help="Comma-separated list of categories to include",
    )
    parser.add_argument(
        "--shuffle",
        action="store_true",
        help="Randomize letter order",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Print category counts and exit",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for shuffle (default: 42)",
    )
    args = parser.parse_args()

    categories = (
        args.categories.split(",") if args.categories else ALL_CATEGORIES
    )

    letters = collect_letters(categories)

    if args.stats:
        print_stats(letters)
        return

    if args.shuffle:
        random.seed(args.seed)
        random.shuffle(letters)

    corpus = build_corpus(letters)
    OUTPUT_FILE.write_text(corpus + "\n")
    print(f"Wrote {len(letters)} letters to {OUTPUT_FILE}")
    print_stats(letters)


if __name__ == "__main__":
    main()

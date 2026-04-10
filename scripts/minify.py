#!/usr/bin/env python3
"""Dead-simple token minimizer. Reads stdin, prints compacted output.

Demonstrates the principle: fewer tokens in = less money out.
For a production-grade version, see RTK (Rust Token Killer).

Usage:
    cat verbose.txt | python minify.py
"""

import json
import re
import sys


def minify_text(text):
    """Compact text to reduce token count. Try JSON first, fall back to text."""
    text = text.strip()

    # Try to parse and re-serialize as compact JSON
    try:
        data = json.loads(text)
        return json.dumps(data, separators=(",", ":"))
    except (json.JSONDecodeError, ValueError):
        pass

    # Plain text: strip trailing whitespace, collapse blank lines
    lines = [line.rstrip() for line in text.splitlines()]
    result = re.sub(r"\n{3,}", "\n", "\n".join(lines))
    return result.strip()


if __name__ == "__main__":
    original = sys.stdin.read()
    compact = minify_text(original)

    # Approximate tokens (1 token ≈ 4 chars for English text)
    orig_tokens = len(original) // 4
    compact_tokens = len(compact) // 4
    saved = orig_tokens - compact_tokens

    print(compact)
    print(f"\n--- minify ---", file=sys.stderr)
    print(f"Before: {len(original)} chars (~{orig_tokens} tokens)", file=sys.stderr)
    print(f"After:  {len(compact)} chars (~{compact_tokens} tokens)", file=sys.stderr)
    print(f"Saved:  {saved} tokens ({saved/max(orig_tokens,1):.0%})", file=sys.stderr)

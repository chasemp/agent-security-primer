#!/usr/bin/env python3
"""Run a system prompt against a JSONL golden dataset and report accuracy.

Usage:
    python scripts/eval.py demos/S01_golden_dataset/golden.jsonl \
        --prompt demos/S01_golden_dataset/system_prompt_v1.txt
    python scripts/eval.py golden.jsonl --prompt v2.txt --model claude-sonnet-4-6

Each JSONL line is one entry: {"input": "...", "expected": "..."}.
The script sends each input to Claude with the given system prompt, scores
the response against `expected` (case-insensitive word match), and prints
per-entry results plus accuracy.

This is the regression-detection demo: run twice with two prompt versions,
compare accuracy. Same dataset, different prompt -> different score.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Callable

from ask_claude import send_message


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_golden(path: Path) -> list[dict]:
    """Read JSONL, return list of {input, expected} dicts. Skip blank lines."""
    entries: list[dict] = []
    for line_num, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        entry = json.loads(line)
        if "input" not in entry or "expected" not in entry:
            raise ValueError(
                f"Line {line_num} missing required field (input/expected): {line}"
            )
        entries.append(entry)
    return entries


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def score_response(response: str, expected: str) -> bool:
    """Return True if `expected` appears as a whole word in `response`.

    Case-insensitive. Word-boundary aware so "home" doesn't match "homesick".
    Handles real-world responses like "The mood is homesick." or just "homesick".
    """
    pattern = r"\b" + re.escape(expected.lower()) + r"\b"
    return bool(re.search(pattern, response.lower()))


# ---------------------------------------------------------------------------
# Process scoring — does the response show its work?
# ---------------------------------------------------------------------------

_ARITHMETIC_OPS = re.compile(r"[+\-×*/÷]")
_NUMBER_RE = re.compile(r"\d+")
_REASONING_MARKERS = re.compile(
    r"\b(step|first|second|third|then|next|so|therefore|finally|because|since)\b|=",
    re.IGNORECASE,
)


def score_process(response: str) -> dict:
    """Score whether the response shows its reasoning.

    Three independent markers — each yes/no:
      shows_arithmetic:        contains an operator (+, -, *, ×, /, ÷)
      shows_intermediate_value: contains at least 3 distinct numbers
      shows_reasoning_steps:    contains sequencing markers (step/then/=/etc.)

    Returns: {"checks": {marker: bool}, "passed": int, "total": int}
    """
    distinct_numbers = set(_NUMBER_RE.findall(response))
    checks = {
        "shows_arithmetic": bool(_ARITHMETIC_OPS.search(response)),
        "shows_intermediate_value": len(distinct_numbers) >= 3,
        "shows_reasoning_steps": bool(_REASONING_MARKERS.search(response)),
    }
    passed = sum(1 for v in checks.values() if v)
    return {"checks": checks, "passed": passed, "total": len(checks)}


# ---------------------------------------------------------------------------
# Eval loop
# ---------------------------------------------------------------------------

SendFn = Callable[[str, str], dict]


def run_eval(
    golden: list[dict],
    system_prompt: str,
    send_fn: SendFn,
) -> list[dict]:
    """Run each entry through send_fn, score, return results.

    send_fn must return a dict with at least a "text" field. ask_claude.send_message
    can be partially applied to satisfy this signature; tests inject a fake.
    """
    results: list[dict] = []
    for entry in golden:
        response = send_fn(system_prompt, entry["input"])
        prediction = response["text"].strip()
        results.append({
            "input": entry["input"],
            "expected": entry["expected"],
            "prediction": prediction,
            "correct": score_response(prediction, entry["expected"]),
            "process": score_process(prediction),
            "input_tokens": response.get("input_tokens", 0),
            "output_tokens": response.get("output_tokens", 0),
            "cost_usd": response.get("cost_usd", 0.0),
        })
    return results


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def summarize(results: list[dict]) -> dict:
    """Compute accuracy and per-category breakdown."""
    total = len(results)
    correct = sum(1 for r in results if r["correct"])
    by_category: dict[str, dict[str, int]] = {}
    for r in results:
        cat = r["expected"]
        if cat not in by_category:
            by_category[cat] = {"total": 0, "correct": 0}
        by_category[cat]["total"] += 1
        if r["correct"]:
            by_category[cat]["correct"] += 1
    summary = {
        "total": total,
        "correct": correct,
        "accuracy": correct / total if total else 0.0,
        "by_category": by_category,
        "total_cost_usd": sum(r.get("cost_usd", 0.0) for r in results),
    }
    # Aggregate process score across entries that have it
    process_results = [r["process"] for r in results if "process" in r]
    if process_results:
        passed = sum(p["passed"] for p in process_results)
        possible = sum(p["total"] for p in process_results)
        summary["process"] = {
            "passed": passed,
            "total": possible,
            "fraction": passed / possible if possible else 0.0,
        }
    return summary


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def format_report(results: list[dict], summary: dict, show_process: bool = False) -> str:
    """Human-readable report — per-entry results + accuracy summary.

    show_process=True adds per-entry process markers and an aggregate
    process score (used by S02 to compare reasoning quality across
    prompt versions; S01 leaves it off and reports outcome only).
    """
    lines: list[str] = []
    lines.append("=" * 70)
    lines.append("PER-ENTRY RESULTS")
    lines.append("=" * 70)
    for i, r in enumerate(results, 1):
        mark = "PASS" if r["correct"] else "FAIL"
        snippet = r["input"][:60].replace("\n", " ")
        if len(r["input"]) > 60:
            snippet += "..."
        lines.append(f"{i:2d}. [{mark}] expected={r['expected']:12s} got={r['prediction'][:40]!r}")
        lines.append(f"    input: {snippet}")
        if show_process and "process" in r:
            checks = r["process"]["checks"]
            marks = " ".join(
                f"{name}={'Y' if hit else '.'}" for name, hit in checks.items()
            )
            lines.append(f"    process: {r['process']['passed']}/{r['process']['total']}  {marks}")
    lines.append("")
    lines.append("=" * 70)
    lines.append("SUMMARY")
    lines.append("=" * 70)
    accuracy_pct = summary["accuracy"] * 100
    lines.append(f"Outcome accuracy:  {summary['correct']}/{summary['total']} = {accuracy_pct:.1f}%")
    if show_process and "process" in summary:
        proc = summary["process"]
        proc_pct = proc["fraction"] * 100
        lines.append(f"Process score:     {proc['passed']}/{proc['total']} = {proc_pct:.1f}%")
    lines.append("")
    lines.append("Per category:")
    for cat in sorted(summary["by_category"]):
        stats = summary["by_category"][cat]
        cat_pct = stats["correct"] / stats["total"] * 100
        lines.append(
            f"  {cat:12s} {stats['correct']}/{stats['total']} = {cat_pct:.0f}%"
        )
    if summary.get("total_cost_usd"):
        lines.append("")
        lines.append(f"Total cost: ${summary['total_cost_usd']:.4f}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Run a golden dataset eval")
    parser.add_argument("dataset", help="Path to golden.jsonl")
    parser.add_argument("--prompt", required=True, help="Path to system_prompt.txt")
    parser.add_argument("--model", default="claude-haiku-4-5", help="Claude model")
    parser.add_argument("--temperature", type=float, default=0.0,
                        help="Sampling temperature (default 0 for determinism)")
    parser.add_argument("--process", action="store_true",
                        help="Show process score per entry (does the response show its work?)")
    args = parser.parse_args()

    golden = load_golden(Path(args.dataset))
    system_prompt = Path(args.prompt).read_text().strip()

    def send(system: str, content: str) -> dict:
        return send_message(
            system, content, model=args.model, temperature=args.temperature,
        )

    results = run_eval(golden, system_prompt, send)
    summary = summarize(results)
    print(format_report(results, summary, show_process=args.process))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Reinforcement Learning demo — shape model output with reward signals.

Demonstrates outcome reward (B05), process reward (B06), and the
before/after comparison (B07). Uses the B02 character model as base.

Usage:
    python scripts/rl_demo.py corpus/camp_letters.txt --show-reward outcome
    python scripts/rl_demo.py corpus/camp_letters.txt --train --reward outcome --steps 200
    python scripts/rl_demo.py corpus/camp_letters.txt --generate --count 5
    python scripts/rl_demo.py corpus/camp_letters.txt --show-curve
    python scripts/rl_demo.py corpus/camp_letters.txt --show-curve --compare
    python scripts/rl_demo.py corpus/camp_letters.txt --topic-distribution --compare
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path
from typing import Optional

try:
    import torch
    import torch.nn as nn
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

# Import charmodel for the base model
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))


# ---------------------------------------------------------------------------
# Theme words and categories
# ---------------------------------------------------------------------------

FRIENDSHIP_WORDS = {
    "friend", "friends", "buddy", "buddies", "pal", "pals",
    "together", "teammate", "teammates", "penpal", "penpals",
    "we all", "our cabin", "our team", "group",
}

CATEGORIES = [
    "arrival", "adventure", "food", "friendship",
    "growth", "homesick", "last_days", "rainy_day", "other",
]

CATEGORY_KEYWORDS = {
    "arrival": {"arrived", "got here", "first day", "bus ride", "cabin is", "unpacked", "orientation", "bunk"},
    "adventure": {"kayak", "hike", "hiking", "campfire", "ropes", "rock wall", "climbing", "swimming", "archery", "canoe", "zipline", "zip line", "night hike"},
    "food": {"food", "mess hall", "breakfast", "lunch", "dinner", "snack", "cook", "marshmallow", "s'more", "kitchen", "hungry", "ate", "taco", "pizza", "bug juice"},
    "friendship": {"friend", "friends", "buddy", "together", "penpal", "we all", "teammate", "group", "our cabin"},
    "growth": {"scared but", "finally", "first time", "proud", "learned", "conquered", "stood up", "brave", "never thought"},
    "homesick": {"miss you", "miss my", "miss home", "homesick", "come home", "want to leave", "counting days", "care package"},
    "last_days": {"last day", "going home", "packing", "goodbye", "come back next", "almost over", "counting down", "bus home"},
    "rainy_day": {"rain", "rained", "raining", "stuck inside", "board game", "uno", "indoor", "mud", "wet"},
}


# ---------------------------------------------------------------------------
# Reward functions
# ---------------------------------------------------------------------------

def outcome_reward(text: str, theme_words: Optional[set] = None) -> float:
    """Score complete text: 1.0 if any theme word appears, 0.0 otherwise."""
    if theme_words is None:
        theme_words = FRIENDSHIP_WORDS
    text_lower = text.lower()
    for word in theme_words:
        if word in text_lower:
            return 1.0
    return 0.0


def process_reward(text: str, theme_words: Optional[set] = None) -> list[float]:
    """Score each sentence: 0.0-1.0 based on theme word presence and coherence."""
    if theme_words is None:
        theme_words = FRIENDSHIP_WORDS
    # Split on sentence boundaries
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    if not sentences:
        return [0.0]

    scores = []
    for sentence in sentences:
        s_lower = sentence.lower()
        words = s_lower.split()
        if len(words) < 2:
            scores.append(0.1)
            continue

        # Base score for coherence (has real words, reasonable length)
        coherence = min(len(words) / 10.0, 0.5)

        # Theme bonus
        theme_hits = sum(1 for w in theme_words if w in s_lower)
        theme_score = min(theme_hits * 0.3, 0.5)

        scores.append(min(coherence + theme_score, 1.0))

    return scores


# ---------------------------------------------------------------------------
# Topic classification
# ---------------------------------------------------------------------------

def topic_classify(text: str) -> str:
    """Simple keyword classifier for camp letter categories."""
    text_lower = text.lower()
    scores = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        scores[category] = score

    if max(scores.values()) == 0:
        return "other"
    return max(scores, key=scores.get)


# ---------------------------------------------------------------------------
# ASCII rendering
# ---------------------------------------------------------------------------

def render_distribution(counts: dict, label: str) -> str:
    """Render a topic distribution as ASCII bars."""
    lines = [f"  {label}:"]
    max_count = max(counts.values()) if counts else 1
    for cat in CATEGORIES:
        count = counts.get(cat, 0)
        bar_len = int(count / max(max_count, 1) * 30)
        bar = "█" * bar_len
        lines.append(f"    {cat:12s} {bar} {count}")
    return "\n".join(lines)


def render_curve(rewards: list[float], label: str) -> str:
    """Render a reward-over-time curve as ASCII."""
    if not rewards:
        return f"  {label}: no data"
    lines = [f"  {label} (reward over training steps):", ""]
    max_r = max(max(rewards), 0.01)
    # Sample ~20 points
    step = max(len(rewards) // 20, 1)
    for i in range(0, len(rewards), step):
        bar_len = int(rewards[i] / max_r * 40)
        bar = "█" * bar_len
        lines.append(f"    step {i:4d} │{bar} {rewards[i]:.2f}")
    lines.append(f"    step {len(rewards):4d} │{'█' * int(rewards[-1] / max_r * 40)} {rewards[-1]:.2f}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Model management (wraps charmodel)
# ---------------------------------------------------------------------------

# Module-level state for the demo
_base_model = None
_rl_model = None
_vocab = None
_pretrained_state = None
_outcome_rewards = []
_process_rewards = []


def prepare_base_model(text: str) -> dict:
    """Train a small character model as the RL base."""
    global _base_model, _rl_model, _vocab, _pretrained_state
    global _outcome_rewards, _process_rewards

    from charmodel import CharModel, build_vocab, train_model

    _vocab = build_vocab(text)
    vocab_size = len(_vocab["char_to_idx"])

    _base_model = CharModel(vocab_size=vocab_size, hidden_size=64, num_layers=1)
    train_model(_base_model, text, _vocab, epochs=30, seq_len=64, lr=0.003)

    _pretrained_state = copy.deepcopy(_base_model.state_dict())
    _rl_model = CharModel(vocab_size=vocab_size, hidden_size=64, num_layers=1)
    _rl_model.load_state_dict(_pretrained_state)

    _outcome_rewards = []
    _process_rewards = []

    return _vocab


def _generate_text(model, vocab: dict, num_chars: int = 200, temperature: float = 0.8) -> str:
    """Generate text from a character model."""
    from charmodel import generate_text
    return generate_text(model, vocab, num_chars=num_chars, temperature=temperature)


def generate_batch(count: int = 5, use_rl: bool = True) -> list[str]:
    """Generate multiple texts from the current model."""
    model = _rl_model if use_rl else _base_model
    if model is None:
        return []
    results = []
    for i in range(count):
        text = _generate_text(model, _vocab, num_chars=200, temperature=0.8)
        results.append(text)
    return results


# ---------------------------------------------------------------------------
# RL training (simplified reward-weighted fine-tuning)
# ---------------------------------------------------------------------------

def rl_train(
    reward_type: str = "outcome",
    steps: int = 100,
    n_samples: int = 5,
    gen_length: int = 150,
) -> list[float]:
    """Simplified RL: generate samples, score them, fine-tune on best.

    This is reward-weighted fine-tuning, not full policy gradient.
    Simpler to implement, more reliable for a demo, same concept:
    the reward signal shapes which patterns the model prefers.
    """
    global _rl_model, _outcome_rewards, _process_rewards

    if _rl_model is None or _vocab is None:
        raise RuntimeError("Call prepare_base_model first")

    from charmodel import build_vocab

    char_to_idx = _vocab["char_to_idx"]
    vocab_size = len(char_to_idx)
    optimizer = torch.optim.Adam(_rl_model.parameters(), lr=0.0005)
    criterion = nn.CrossEntropyLoss(reduction="none")

    rewards_history = []

    for step in range(steps):
        # Generate samples
        samples = []
        for _ in range(n_samples):
            text = _generate_text(_rl_model, _vocab, num_chars=gen_length, temperature=0.9)
            samples.append(text)

        # Score samples
        if reward_type == "outcome":
            scores = [outcome_reward(s) for s in samples]
        else:
            # Process: average per-sentence scores
            scores = [sum(process_reward(s)) / max(len(process_reward(s)), 1) for s in samples]

        avg_reward = sum(scores) / len(scores) if scores else 0.0
        rewards_history.append(avg_reward)

        # Fine-tune on high-scoring samples (reward-weighted)
        if max(scores) > 0:
            # Weight each sample by its reward
            _rl_model.train()
            for sample, score in zip(samples, scores):
                if score <= 0:
                    continue
                # Encode and train
                valid_chars = [ch for ch in sample if ch in char_to_idx]
                if len(valid_chars) < 10:
                    continue
                data = torch.tensor([char_to_idx[ch] for ch in valid_chars], dtype=torch.long)
                seq_len = min(64, len(data) - 1)
                if seq_len < 5:
                    continue
                x = data[:seq_len].unsqueeze(0)
                y = data[1:seq_len + 1].unsqueeze(0)

                output = _rl_model(x)
                loss = criterion(output.view(-1, vocab_size), y.view(-1))
                # Weight loss by reward score
                weighted_loss = (loss * score).mean()
                optimizer.zero_grad()
                weighted_loss.backward()
                optimizer.step()

    if reward_type == "outcome":
        _outcome_rewards = rewards_history
    else:
        _process_rewards = rewards_history

    return rewards_history


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

CORPUS_DIR = Path(__file__).parent.parent / "corpus"
RL_STATE_PATH = CORPUS_DIR / "rl_state.json"


def main() -> None:
    if not HAS_TORCH:
        print("Error: PyTorch is required.", file=sys.stderr)
        sys.exit(1)

    parser = argparse.ArgumentParser(description="RL demo — shape output with reward")
    parser.add_argument("corpus", type=Path, help="Path to training corpus")
    parser.add_argument("--show-reward", type=str, choices=["outcome", "process"],
                        help="Display the reward function")
    parser.add_argument("--train", action="store_true", help="Run RL training")
    parser.add_argument("--reward", type=str, default="outcome",
                        choices=["outcome", "process"], help="Reward type")
    parser.add_argument("--steps", type=int, default=100, help="Training steps")
    parser.add_argument("--generate", action="store_true", help="Generate text")
    parser.add_argument("--count", type=int, default=5, help="Number of texts to generate")
    parser.add_argument("--model", type=str, default="rl",
                        choices=["pretrained", "rl"], help="Which model to generate from")
    parser.add_argument("--show-curve", action="store_true", help="Show reward curve")
    parser.add_argument("--compare", action="store_true", help="Compare outcome vs process")
    parser.add_argument("--topic-distribution", action="store_true", help="Show topic distribution")
    args = parser.parse_args()

    if args.show_reward:
        if args.show_reward == "outcome":
            print("OUTCOME REWARD FUNCTION:")
            print("  Score the COMPLETE letter:")
            print("  1.0 if any of these words appear:")
            for w in sorted(FRIENDSHIP_WORDS):
                print(f"    - {w}")
            print("  0.0 otherwise.")
            print("\n  The model doesn't know WHICH part earned the score.")
        else:
            print("PROCESS REWARD FUNCTION:")
            print("  Score EACH SENTENCE independently:")
            print("  0.0-0.5 base score for coherence (word count)")
            print("  +0.3 per friendship/togetherness word found")
            print("  Capped at 1.0")
            print("\n  The model knows which sentences scored high.")
        return

    # Load corpus and prepare base model
    text = args.corpus.read_text()
    print(f"Preparing base model on {len(text)} characters...")
    prepare_base_model(text)
    print("Base model ready.")

    if args.train:
        print(f"\nRL training ({args.reward} reward, {args.steps} steps)...")
        rewards = rl_train(reward_type=args.reward, steps=args.steps)
        print(f"Training complete. Final avg reward: {rewards[-1]:.3f}")
        print(render_curve(rewards, args.reward))

    if args.show_curve:
        if args.compare and _outcome_rewards and _process_rewards:
            print(render_curve(_outcome_rewards, "Outcome"))
            print()
            print(render_curve(_process_rewards, "Process"))
        elif _outcome_rewards:
            print(render_curve(_outcome_rewards, "Outcome"))
        elif _process_rewards:
            print(render_curve(_process_rewards, "Process"))
        else:
            print("No training data yet. Run --train first.")

    if args.generate:
        use_rl = args.model == "rl"
        label = "RL-trained" if use_rl else "Pre-trained"
        print(f"\nGenerating {args.count} letters ({label}):\n")
        texts = generate_batch(count=args.count, use_rl=use_rl)
        for i, t in enumerate(texts, 1):
            print(f"--- Letter {i} ---")
            print(t)
            print()

    if args.topic_distribution:
        pre_texts = generate_batch(count=20, use_rl=False)
        post_texts = generate_batch(count=20, use_rl=True)

        pre_counts = {}
        for t in pre_texts:
            cat = topic_classify(t)
            pre_counts[cat] = pre_counts.get(cat, 0) + 1

        post_counts = {}
        for t in post_texts:
            cat = topic_classify(t)
            post_counts[cat] = post_counts.get(cat, 0) + 1

        print(render_distribution(pre_counts, "Pre-trained"))
        print()
        print(render_distribution(post_counts, "After RL"))


if __name__ == "__main__":
    main()

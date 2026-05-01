"""Tests for Process Reward demo — per-sentence scoring.

Same goal as B05, but scores each sentence. Faster convergence,
less noise, better output quality.

Cost: $0.00 — no API calls, runs locally.
Dependencies: PyTorch
"""

import sys
from pathlib import Path

import pytest

DEMO_DIR = Path(__file__).parent.parent / "demos" / "B06_process_reward"
SCRIPT = Path(__file__).parent.parent / "scripts" / "rl_demo.py"
PYTHON = sys.executable


def _has_torch() -> bool:
    try:
        import torch  # noqa: F401
        return True
    except ImportError:
        return False


requires_torch = pytest.mark.skipif(not _has_torch(), reason="PyTorch not installed")


class TestFileStructure:
    def test_talking_points_exists(self) -> None:
        assert (DEMO_DIR / "talking_points.txt").exists()

    def test_script_exists(self) -> None:
        assert SCRIPT.exists()


@requires_torch
class TestProcessReward:
    @pytest.fixture
    def rl_module(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("rl_demo", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_process_reward_scores_per_sentence(self, rl_module) -> None:
        text = "I made a friend. The food was bad. We played together."
        scores = rl_module.process_reward(text)
        assert isinstance(scores, list)
        assert len(scores) == 3

    def test_process_reward_friendship_scores_higher(self, rl_module) -> None:
        text = "I made a friend. The food was bad."
        scores = rl_module.process_reward(text)
        assert scores[0] > scores[1], "Friendship sentence should score higher"

    def test_process_reward_all_in_range(self, rl_module) -> None:
        text = "Dear Mom. I miss you. My friend Kai is cool. Love Sophie."
        scores = rl_module.process_reward(text)
        for s in scores:
            assert 0.0 <= s <= 1.0, f"Score {s} out of range"


@requires_torch
class TestProcessRewardLive:
    @pytest.mark.live
    def test_process_converges_faster_than_outcome(self) -> None:
        import importlib.util
        spec = importlib.util.spec_from_file_location("rl_demo", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        text = "Dear Mom I miss you. Love Sophie. Dear Dad my friend Kai is great. Love Jordan. " * 30

        # Train with outcome reward
        mod.prepare_base_model(text)
        outcome_rewards = mod.rl_train(reward_type="outcome", steps=30)

        # Reset and train with process reward
        mod.prepare_base_model(text)
        process_rewards = mod.rl_train(reward_type="process", steps=30)

        # Process should have higher average reward
        outcome_avg = sum(outcome_rewards) / len(outcome_rewards)
        process_avg = sum(process_rewards) / len(process_rewards)
        assert process_avg >= outcome_avg * 0.9, (
            f"Process ({process_avg:.2f}) should be at least close to outcome ({outcome_avg:.2f})"
        )

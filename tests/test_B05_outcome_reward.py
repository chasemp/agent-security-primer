"""Tests for Outcome Reward demo — pass/fail on complete output.

The model generates a full letter, then gets scored: did it mention
making friends? Yes = 1.0, No = 0.0. Slow, noisy convergence.

Cost: $0.00 — no API calls, runs locally.
Dependencies: PyTorch
"""

import sys
from pathlib import Path

import pytest

DEMO_DIR = Path(__file__).parent.parent / "demos" / "B05_outcome_reward"
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

    def test_outcome_vs_process_asset_exists(self) -> None:
        assets = Path(__file__).parent.parent / "demos" / "assets"
        assert (assets / "outcome_vs_process.txt").exists()


@requires_torch
class TestOutcomeReward:
    @pytest.fixture
    def rl_module(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("rl_demo", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_outcome_reward_scores_match(self, rl_module) -> None:
        """Text with friend words should score 1.0, without should score 0.0."""
        assert rl_module.outcome_reward("I made a new friend today") == 1.0
        assert rl_module.outcome_reward("The food was terrible") == 0.0

    def test_outcome_reward_case_insensitive(self, rl_module) -> None:
        assert rl_module.outcome_reward("My FRIEND Kai is great") == 1.0

    def test_outcome_reward_detects_variants(self, rl_module) -> None:
        assert rl_module.outcome_reward("We all went together") == 1.0
        assert rl_module.outcome_reward("My buddy Marcus is funny") == 1.0

    def test_topic_classify_returns_category(self, rl_module) -> None:
        result = rl_module.topic_classify("I miss my dog and my bed")
        assert result in rl_module.CATEGORIES


@requires_torch
class TestOutcomeRewardLive:
    @pytest.mark.live
    def test_outcome_training_increases_reward(self) -> None:
        import importlib.util
        spec = importlib.util.spec_from_file_location("rl_demo", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        # Train a small model briefly, then do RL
        text = "Dear Mom I miss you. Love Sophie. Dear Dad my friend Kai is great. Love Jordan. " * 30
        vocab = mod.prepare_base_model(text)
        rewards = mod.rl_train(reward_type="outcome", steps=30)
        # Reward should trend upward (last 10 avg > first 10 avg)
        early = sum(rewards[:10]) / 10
        late = sum(rewards[-10:]) / 10
        assert late >= early, f"Reward didn't increase: early={early:.2f}, late={late:.2f}"

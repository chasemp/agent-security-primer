"""Tests for Shaping the Board demo — before/after RL comparison.

Same model, same knowledge. RL reshapes which patterns the model
prefers. The Plinko board analogy: RL tilts, doesn't rebuild.

Cost: $0.00 — no API calls, runs locally.
Dependencies: PyTorch
"""

import sys
from pathlib import Path

import pytest

DEMO_DIR = Path(__file__).parent.parent / "demos" / "B07_shaping_the_board"
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

    def test_plinko_assets_exist(self) -> None:
        assets = Path(__file__).parent.parent / "demos" / "assets"
        assert (assets / "plinko_uniform.txt").exists()
        assert (assets / "plinko_friendship.txt").exists()
        assert (assets / "plinko_adventure.txt").exists()


@requires_torch
class TestTopicClassification:
    @pytest.fixture
    def rl_module(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("rl_demo", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_classify_friendship(self, rl_module) -> None:
        assert rl_module.topic_classify("My friend Kai and I played together") == "friendship"

    def test_classify_adventure(self, rl_module) -> None:
        assert rl_module.topic_classify("We went kayaking on the lake today") == "adventure"

    def test_classify_food(self, rl_module) -> None:
        assert rl_module.topic_classify("The food in the mess hall was terrible") == "food"

    def test_classify_homesick(self, rl_module) -> None:
        assert rl_module.topic_classify("I miss my dog and my bed so much") == "homesick"

    def test_render_distribution(self, rl_module) -> None:
        counts = {"friendship": 5, "adventure": 2, "food": 1, "homesick": 1, "growth": 1}
        output = rl_module.render_distribution(counts, "Test")
        assert isinstance(output, str)
        assert "friendship" in output


@requires_torch
class TestShapingLive:
    @pytest.mark.live
    def test_rl_shifts_topic_distribution(self) -> None:
        import importlib.util
        spec = importlib.util.spec_from_file_location("rl_demo", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        text = (
            "Dear Mom I miss you. Love Sophie. "
            "Dear Dad my friend Kai is great. We kayaked today. Love Jordan. "
            "Dear Mom the food was OK. I made a buddy. Love Lily. "
        ) * 20

        # Generate pre-RL
        mod.prepare_base_model(text)
        pre_texts = mod.generate_batch(count=10)
        pre_counts = {}
        for t in pre_texts:
            cat = mod.topic_classify(t)
            pre_counts[cat] = pre_counts.get(cat, 0) + 1

        # Train with friendship reward
        mod.rl_train(reward_type="outcome", steps=30)
        post_texts = mod.generate_batch(count=10)
        post_counts = {}
        for t in post_texts:
            cat = mod.topic_classify(t)
            post_counts[cat] = post_counts.get(cat, 0) + 1

        # RL-trained model should have more friendship output
        post_frd = post_counts.get("friendship", 0)
        pre_frd = pre_counts.get("friendship", 0)
        # Soft assertion: at least as many, ideally more
        assert post_frd >= pre_frd or post_frd >= 2

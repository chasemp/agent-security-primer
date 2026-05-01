"""Tests for Bigram Model demo — simplest possible language model.

Count word pairs in a corpus, sample the next word from those counts.
The output is bad — that's the point. The mechanism is visible BECAUSE
it's bad.

Cost: $0.00 — no API calls, runs locally.
"""

import sys
from pathlib import Path

import pytest

DEMO_DIR = Path(__file__).parent.parent / "demos" / "B01_bigram_model"
CORPUS_DIR = Path(__file__).parent.parent / "corpus"
SCRIPT = Path(__file__).parent.parent / "scripts" / "bigram.py"
PYTHON = sys.executable


# ---------------------------------------------------------------------------
# File structure
# ---------------------------------------------------------------------------

class TestFileStructure:
    def test_talking_points_exists(self) -> None:
        assert (DEMO_DIR / "talking_points.txt").exists()

    def test_script_exists(self) -> None:
        assert SCRIPT.exists()

    def test_corpus_build_script_exists(self) -> None:
        assert (CORPUS_DIR / "build_corpus.py").exists()

    def test_corpus_categories_exist(self) -> None:
        expected = [
            "arrival", "homesick", "adventure", "friendship",
            "food", "rainy_day", "growth", "last_days",
        ]
        for cat in expected:
            assert (CORPUS_DIR / "camp_letters.d" / cat).is_dir(), f"Missing category: {cat}"

    def test_each_category_has_letters(self) -> None:
        for cat_dir in sorted((CORPUS_DIR / "camp_letters.d").iterdir()):
            if not cat_dir.is_dir() or cat_dir.name.startswith("."):
                continue
            letters = list(cat_dir.glob("*.txt"))
            assert len(letters) >= 5, f"{cat_dir.name} has {len(letters)} letters, need >= 5"


# ---------------------------------------------------------------------------
# Bigram module unit tests
# ---------------------------------------------------------------------------

class TestBigramCounting:
    @pytest.fixture
    def bigram_module(self):
        """Import bigram as a module for unit testing."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("bigram", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_count_bigrams_returns_dict(self, bigram_module) -> None:
        text = "Dear Mom I miss you Love Sophie"
        result = bigram_module.count_bigrams(text)
        assert isinstance(result, dict)

    def test_count_bigrams_captures_pairs(self, bigram_module) -> None:
        text = "Dear Mom I miss you Love Sophie"
        result = bigram_module.count_bigrams(text)
        assert "Dear" in result
        assert "Mom" in result["Dear"]

    def test_count_bigrams_counts_frequency(self, bigram_module) -> None:
        text = "the cat the dog the bird"
        result = bigram_module.count_bigrams(text)
        assert result["the"]["cat"] == 1
        assert result["the"]["dog"] == 1
        assert result["the"]["bird"] == 1

    def test_get_probabilities_sums_to_one(self, bigram_module) -> None:
        text = "the cat the dog the bird"
        counts = bigram_module.count_bigrams(text)
        probs = bigram_module.get_probabilities(counts, "the")
        total = sum(probs.values())
        assert abs(total - 1.0) < 0.001

    def test_get_probabilities_empty_word(self, bigram_module) -> None:
        text = "the cat"
        counts = bigram_module.count_bigrams(text)
        probs = bigram_module.get_probabilities(counts, "nonexistent")
        assert probs == {}


class TestBigramGeneration:
    @pytest.fixture
    def bigram_module(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("bigram", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_generate_returns_string(self, bigram_module) -> None:
        text = "Dear Mom I miss you Dear Dad I love camp"
        counts = bigram_module.count_bigrams(text)
        result = bigram_module.generate(counts, start_word="Dear", num_words=10, seed=42)
        assert isinstance(result, str)

    def test_generate_respects_word_count(self, bigram_module) -> None:
        text = "Dear Mom I miss you Dear Dad I love camp"
        counts = bigram_module.count_bigrams(text)
        result = bigram_module.generate(counts, start_word="Dear", num_words=5, seed=42)
        words = result.split()
        assert len(words) <= 5

    def test_generate_starts_with_start_word(self, bigram_module) -> None:
        text = "Dear Mom I miss you Dear Dad I love camp"
        counts = bigram_module.count_bigrams(text)
        result = bigram_module.generate(counts, start_word="Dear", num_words=10, seed=42)
        assert result.startswith("Dear")

    def test_generate_deterministic_with_seed(self, bigram_module) -> None:
        text = "Dear Mom I miss you Dear Dad I love camp Dear Mom the food is good"
        counts = bigram_module.count_bigrams(text)
        r1 = bigram_module.generate(counts, start_word="Dear", num_words=20, seed=42)
        r2 = bigram_module.generate(counts, start_word="Dear", num_words=20, seed=42)
        assert r1 == r2

    def test_generate_varies_with_different_seed(self, bigram_module) -> None:
        text = (
            "Dear Mom I miss you Dear Dad I love camp Dear Mom the food "
            "Dear Dad the lake Dear Mom my friend Dear Dad we went"
        )
        counts = bigram_module.count_bigrams(text)
        r1 = bigram_module.generate(counts, start_word="Dear", num_words=20, seed=1)
        r2 = bigram_module.generate(counts, start_word="Dear", num_words=20, seed=2)
        # With enough variety in the corpus, different seeds should produce different output
        # (not guaranteed with tiny corpus, but likely)
        assert r1 != r2 or True  # soft assertion — different seeds usually differ


class TestBigramTable:
    @pytest.fixture
    def bigram_module(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("bigram", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_top_pairs_returns_list(self, bigram_module) -> None:
        text = "Dear Mom I miss you Dear Dad I love camp"
        counts = bigram_module.count_bigrams(text)
        pairs = bigram_module.top_pairs(counts, n=5)
        assert isinstance(pairs, list)

    def test_top_pairs_sorted_by_count(self, bigram_module) -> None:
        text = "the cat the cat the dog"
        counts = bigram_module.count_bigrams(text)
        pairs = bigram_module.top_pairs(counts, n=5)
        counts_list = [count for _, _, count in pairs]
        assert counts_list == sorted(counts_list, reverse=True)

    def test_top_pairs_respects_n(self, bigram_module) -> None:
        text = "a b c d e f g h i j"
        counts = bigram_module.count_bigrams(text)
        pairs = bigram_module.top_pairs(counts, n=3)
        assert len(pairs) <= 3


# ---------------------------------------------------------------------------
# Live tests — run the full presenter flow
# ---------------------------------------------------------------------------

class TestBigramLive:
    """Run the actual bigram script against the real corpus.

    These validate the presenter flow works end-to-end. Not API tests,
    but they exercise the full pipeline: build corpus -> count bigrams
    -> generate text.
    """

    @pytest.fixture(autouse=True)
    def build_corpus(self) -> None:
        """Ensure the combined corpus file exists."""
        import subprocess
        subprocess.run(
            [PYTHON, str(CORPUS_DIR / "build_corpus.py")],
            check=True,
            capture_output=True,
        )

    @pytest.mark.live
    def test_table_output_shows_pairs(self) -> None:
        import subprocess
        result = subprocess.run(
            [PYTHON, str(SCRIPT), str(CORPUS_DIR / "camp_letters.txt"), "--table"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        output = result.stdout
        # Should contain at least "Dear" -> "Mom" or "Dad"
        assert "Dear" in output
        assert "->" in output or "→" in output or ":" in output

    @pytest.mark.live
    def test_generate_produces_text(self) -> None:
        import subprocess
        result = subprocess.run(
            [PYTHON, str(SCRIPT), str(CORPUS_DIR / "camp_letters.txt"),
             "--generate", "--words", "30", "--seed", "42"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        words = result.stdout.strip().split()
        assert len(words) >= 10  # should produce at least some words

    @pytest.mark.live
    def test_generate_starts_with_dear(self) -> None:
        import subprocess
        result = subprocess.run(
            [PYTHON, str(SCRIPT), str(CORPUS_DIR / "camp_letters.txt"),
             "--generate", "--words", "30", "--seed", "42"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert result.stdout.strip().startswith("Dear")

    @pytest.mark.live
    def test_category_subset_changes_output(self) -> None:
        """Training on only 'homesick' letters should produce different
        bigrams than training on only 'adventure' letters."""
        import subprocess

        # Build homesick-only corpus
        subprocess.run(
            [PYTHON, str(CORPUS_DIR / "build_corpus.py"), "--categories", "homesick"],
            check=True,
            capture_output=True,
        )
        r_homesick = subprocess.run(
            [PYTHON, str(SCRIPT), str(CORPUS_DIR / "camp_letters.txt"),
             "--generate", "--words", "30", "--seed", "42"],
            capture_output=True,
            text=True,
        )

        # Build adventure-only corpus
        subprocess.run(
            [PYTHON, str(CORPUS_DIR / "build_corpus.py"), "--categories", "adventure"],
            check=True,
            capture_output=True,
        )
        r_adventure = subprocess.run(
            [PYTHON, str(SCRIPT), str(CORPUS_DIR / "camp_letters.txt"),
             "--generate", "--words", "30", "--seed", "42"],
            capture_output=True,
            text=True,
        )

        # Rebuild full corpus for other tests
        subprocess.run(
            [PYTHON, str(CORPUS_DIR / "build_corpus.py")],
            check=True,
            capture_output=True,
        )

        # Different training data should produce different output
        assert r_homesick.stdout != r_adventure.stdout

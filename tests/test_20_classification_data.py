"""Tests for Demo 20 (Semantic Classification) data files.

Four audience variants: technical, expenses, contract, resume.
Each has basic/examples system prompts and easy/tricky tickets.

Uses ask_claude.py — single-turn, stdin piped input.
"""

from pathlib import Path

import pytest

DEMO_DIR = Path(__file__).parent.parent / "demos" / "20_classification"
VARIANTS = ["technical", "expenses", "contract", "resume"]


# ---------------------------------------------------------------------------
# File structure — all variants
# ---------------------------------------------------------------------------

class TestFileStructure:
    def test_talking_points_exists(self) -> None:
        assert (DEMO_DIR / "talking_points.txt").exists()

    @pytest.mark.parametrize("variant", VARIANTS)
    def test_system_prompt_basic_exists(self, variant: str) -> None:
        assert (DEMO_DIR / variant / "system_prompt_basic.txt").exists()

    @pytest.mark.parametrize("variant", VARIANTS)
    def test_system_prompt_examples_exists(self, variant: str) -> None:
        assert (DEMO_DIR / variant / "system_prompt_examples.txt").exists()

    @pytest.mark.parametrize("variant", VARIANTS)
    def test_ticket_easy_exists(self, variant: str) -> None:
        assert (DEMO_DIR / variant / "ticket_easy.txt").exists()

    @pytest.mark.parametrize("variant", VARIANTS)
    def test_ticket_tricky_exists(self, variant: str) -> None:
        assert (DEMO_DIR / variant / "ticket_tricky.txt").exists()


# ---------------------------------------------------------------------------
# System prompts: basic vs. with examples
# ---------------------------------------------------------------------------

class TestSystemPrompts:
    @pytest.mark.parametrize("variant", VARIANTS)
    def test_basic_prompt_is_short(self, variant: str) -> None:
        content = (DEMO_DIR / variant / "system_prompt_basic.txt").read_text()
        assert len(content) < 500

    @pytest.mark.parametrize("variant", VARIANTS)
    def test_basic_prompt_lists_categories(self, variant: str) -> None:
        content = (DEMO_DIR / variant / "system_prompt_basic.txt").read_text()
        lines = content.strip().splitlines()
        assert len(lines) >= 3

    @pytest.mark.parametrize("variant", VARIANTS)
    def test_examples_prompt_is_longer_than_basic(self, variant: str) -> None:
        basic = (DEMO_DIR / variant / "system_prompt_basic.txt").read_text()
        examples = (DEMO_DIR / variant / "system_prompt_examples.txt").read_text()
        assert len(examples) > len(basic) + 200

    @pytest.mark.parametrize("variant", VARIANTS)
    def test_examples_prompt_shares_categories_with_basic(self, variant: str) -> None:
        basic = (DEMO_DIR / variant / "system_prompt_basic.txt").read_text().lower()
        examples = (DEMO_DIR / variant / "system_prompt_examples.txt").read_text().lower()
        assert len(set(basic.split()) & set(examples.split())) > 5


# ---------------------------------------------------------------------------
# Tickets: easy vs. tricky
# ---------------------------------------------------------------------------

class TestTickets:
    @pytest.mark.parametrize("variant", VARIANTS)
    def test_ticket_easy_has_content(self, variant: str) -> None:
        content = (DEMO_DIR / variant / "ticket_easy.txt").read_text()
        assert len(content.strip()) > 20

    @pytest.mark.parametrize("variant", VARIANTS)
    def test_ticket_tricky_has_content(self, variant: str) -> None:
        content = (DEMO_DIR / variant / "ticket_tricky.txt").read_text()
        assert len(content.strip()) > 20

    @pytest.mark.parametrize("variant", VARIANTS)
    def test_tickets_are_different(self, variant: str) -> None:
        easy = (DEMO_DIR / variant / "ticket_easy.txt").read_text()
        tricky = (DEMO_DIR / variant / "ticket_tricky.txt").read_text()
        assert easy != tricky


# ---------------------------------------------------------------------------
# Talking points
# ---------------------------------------------------------------------------

class TestTalkingPoints:
    def test_mentions_semantic(self) -> None:
        content = (DEMO_DIR / "talking_points.txt").read_text().lower()
        assert "semantic" in content

    def test_mentions_keyword(self) -> None:
        content = (DEMO_DIR / "talking_points.txt").read_text().lower()
        assert "keyword" in content

    def test_mentions_examples(self) -> None:
        content = (DEMO_DIR / "talking_points.txt").read_text().lower()
        assert "example" in content

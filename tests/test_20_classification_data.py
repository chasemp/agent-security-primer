"""Tests for Demo 20 (Semantic Classification) data files.

This demo shows the model classifying by meaning, not keywords.
Two system prompts: basic (no examples) and with labeled examples.
Two tickets: easy (keywords match category) and tricky (keywords
suggest wrong category, semantics suggest right one).

Uses ask_claude.py — single-turn, stdin piped input.
"""

from pathlib import Path

import pytest

DEMO_DIR = Path(__file__).parent.parent / "demos" / "20_classification"


# ---------------------------------------------------------------------------
# File structure
# ---------------------------------------------------------------------------

class TestFileStructure:
    def test_system_prompt_basic_exists(self) -> None:
        assert (DEMO_DIR / "system_prompt_basic.txt").exists()

    def test_system_prompt_examples_exists(self) -> None:
        assert (DEMO_DIR / "system_prompt_examples.txt").exists()

    def test_ticket_easy_exists(self) -> None:
        assert (DEMO_DIR / "ticket_easy.txt").exists()

    def test_ticket_tricky_exists(self) -> None:
        assert (DEMO_DIR / "ticket_tricky.txt").exists()

    def test_talking_points_exists(self) -> None:
        assert (DEMO_DIR / "talking_points.txt").exists()


# ---------------------------------------------------------------------------
# System prompts: basic vs. with examples
# ---------------------------------------------------------------------------

class TestSystemPrompts:
    def test_basic_prompt_is_short(self) -> None:
        content = (DEMO_DIR / "system_prompt_basic.txt").read_text()
        assert len(content) < 500

    def test_basic_prompt_lists_categories(self) -> None:
        content = (DEMO_DIR / "system_prompt_basic.txt").read_text()
        # Should define the categories the model can choose from
        lines = content.strip().splitlines()
        assert len(lines) >= 3, "Should list at least a few categories"

    def test_examples_prompt_has_labeled_examples(self) -> None:
        """The examples prompt should contain labeled classification examples."""
        content = (DEMO_DIR / "system_prompt_examples.txt").read_text()
        # Should have more content than basic (the examples)
        basic = (DEMO_DIR / "system_prompt_basic.txt").read_text()
        assert len(content) > len(basic) + 200, (
            "Examples prompt should be substantially longer than basic"
        )

    def test_examples_prompt_shares_categories_with_basic(self) -> None:
        """Both prompts should reference the same categories."""
        basic = (DEMO_DIR / "system_prompt_basic.txt").read_text().lower()
        examples = (DEMO_DIR / "system_prompt_examples.txt").read_text().lower()
        # At least one category name should appear in both
        # (ensures they're classifying into the same set)
        categories_in_basic = set(basic.split())
        categories_in_examples = set(examples.split())
        assert len(categories_in_basic & categories_in_examples) > 5


# ---------------------------------------------------------------------------
# Tickets: easy vs. tricky
# ---------------------------------------------------------------------------

class TestTickets:
    def test_ticket_easy_has_content(self) -> None:
        content = (DEMO_DIR / "ticket_easy.txt").read_text()
        assert len(content.strip()) > 20

    def test_ticket_tricky_has_content(self) -> None:
        content = (DEMO_DIR / "ticket_tricky.txt").read_text()
        assert len(content.strip()) > 20

    def test_tickets_are_different(self) -> None:
        easy = (DEMO_DIR / "ticket_easy.txt").read_text()
        tricky = (DEMO_DIR / "ticket_tricky.txt").read_text()
        assert easy != tricky


# ---------------------------------------------------------------------------
# Talking points
# ---------------------------------------------------------------------------

class TestTalkingPoints:
    def test_mentions_semantic(self) -> None:
        content = (DEMO_DIR / "talking_points.txt").read_text().lower()
        assert "semantic" in content

    def test_mentions_keyword(self) -> None:
        """Should contrast semantic classification with keyword matching."""
        content = (DEMO_DIR / "talking_points.txt").read_text().lower()
        assert "keyword" in content

    def test_mentions_examples(self) -> None:
        content = (DEMO_DIR / "talking_points.txt").read_text().lower()
        assert "example" in content

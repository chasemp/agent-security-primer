"""Tests for Demo 19 (Structured Extraction) data files.

This demo shows the model extracting structured data from messy
unstructured input. Demonstrates with and without schema enforcement
(--schema flag). The schema narrows the prediction menu — same
principle as constrained decoding from the inference pipeline.

Uses ask_claude.py with --schema for structured output.
"""

import json
from pathlib import Path

import pytest

DEMO_DIR = Path(__file__).parent.parent / "demos" / "19_structured_extraction"


# ---------------------------------------------------------------------------
# File structure
# ---------------------------------------------------------------------------

class TestFileStructure:
    def test_system_prompt_exists(self) -> None:
        assert (DEMO_DIR / "system_prompt.txt").exists()

    def test_messy_input_exists(self) -> None:
        assert (DEMO_DIR / "messy_email.txt").exists()

    def test_schema_exists(self) -> None:
        assert (DEMO_DIR / "schema.json").exists()

    def test_talking_points_exists(self) -> None:
        assert (DEMO_DIR / "talking_points.txt").exists()


# ---------------------------------------------------------------------------
# Messy input: realistic unstructured text
# ---------------------------------------------------------------------------

class TestMessyInput:
    def test_messy_email_has_substance(self) -> None:
        """Should be a realistic messy email with extractable data."""
        content = (DEMO_DIR / "messy_email.txt").read_text()
        assert len(content) > 200, "Email should be substantial enough to extract from"

    def test_messy_email_has_extractable_fields(self) -> None:
        """The email should contain data that matches the schema fields."""
        content = (DEMO_DIR / "messy_email.txt").read_text().lower()
        # Should have names, dates, action items — typical extractable data
        has_names = any(word in content for word in ["meeting", "team", "project"])
        has_dates = any(char.isdigit() for char in content)
        assert has_names and has_dates


# ---------------------------------------------------------------------------
# Schema: valid JSON Schema for structured output
# ---------------------------------------------------------------------------

class TestSchema:
    def test_schema_is_valid_json(self) -> None:
        content = (DEMO_DIR / "schema.json").read_text()
        schema = json.loads(content)
        assert isinstance(schema, dict)

    def test_schema_has_object_type(self) -> None:
        schema = json.loads((DEMO_DIR / "schema.json").read_text())
        assert schema["type"] == "object"

    def test_schema_has_properties(self) -> None:
        schema = json.loads((DEMO_DIR / "schema.json").read_text())
        assert "properties" in schema
        assert len(schema["properties"]) >= 3, "Schema should extract multiple fields"

    def test_schema_has_required_fields(self) -> None:
        schema = json.loads((DEMO_DIR / "schema.json").read_text())
        assert "required" in schema
        assert len(schema["required"]) >= 2


# ---------------------------------------------------------------------------
# Talking points
# ---------------------------------------------------------------------------

class TestTalkingPoints:
    def test_mentions_schema(self) -> None:
        content = (DEMO_DIR / "talking_points.txt").read_text().lower()
        assert "schema" in content

    def test_mentions_extraction(self) -> None:
        content = (DEMO_DIR / "talking_points.txt").read_text().lower()
        assert "extract" in content

    def test_mentions_prediction(self) -> None:
        content = (DEMO_DIR / "talking_points.txt").read_text().lower()
        assert "predict" in content

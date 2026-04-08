"""Tests for Demo 19 (Structured Extraction) data files.

Four audience variants: technical, expenses, contract, resume.
Each has a messy email thread, a schema, and a system prompt.

Uses ask_claude.py with --schema for structured output.
"""

import json
from pathlib import Path

import pytest

DEMO_DIR = Path(__file__).parent.parent / "demos" / "19_structured_extraction"
VARIANTS = ["technical", "expenses", "contract", "resume"]


# ---------------------------------------------------------------------------
# File structure — all variants
# ---------------------------------------------------------------------------

class TestFileStructure:
    def test_talking_points_exists(self) -> None:
        assert (DEMO_DIR / "talking_points.txt").exists()

    @pytest.mark.parametrize("variant", VARIANTS)
    def test_system_prompt_exists(self, variant: str) -> None:
        assert (DEMO_DIR / variant / "system_prompt.txt").exists()

    @pytest.mark.parametrize("variant", VARIANTS)
    def test_messy_input_exists(self, variant: str) -> None:
        assert (DEMO_DIR / variant / "messy_email.txt").exists()

    @pytest.mark.parametrize("variant", VARIANTS)
    def test_schema_exists(self, variant: str) -> None:
        assert (DEMO_DIR / variant / "schema.json").exists()


# ---------------------------------------------------------------------------
# Messy input: realistic unstructured text
# ---------------------------------------------------------------------------

class TestMessyInput:
    @pytest.mark.parametrize("variant", VARIANTS)
    def test_messy_email_has_substance(self, variant: str) -> None:
        content = (DEMO_DIR / variant / "messy_email.txt").read_text()
        assert len(content) > 200

    @pytest.mark.parametrize("variant", VARIANTS)
    def test_messy_email_has_extractable_fields(self, variant: str) -> None:
        content = (DEMO_DIR / variant / "messy_email.txt").read_text()
        has_dates = any(char.isdigit() for char in content)
        has_names = "@" in content or "From:" in content
        assert has_dates and has_names


# ---------------------------------------------------------------------------
# Schema: valid JSON Schema for structured output
# ---------------------------------------------------------------------------

class TestSchema:
    @pytest.mark.parametrize("variant", VARIANTS)
    def test_schema_is_valid_json(self, variant: str) -> None:
        schema = json.loads((DEMO_DIR / variant / "schema.json").read_text())
        assert isinstance(schema, dict)

    @pytest.mark.parametrize("variant", VARIANTS)
    def test_schema_has_object_type(self, variant: str) -> None:
        schema = json.loads((DEMO_DIR / variant / "schema.json").read_text())
        assert schema["type"] == "object"

    @pytest.mark.parametrize("variant", VARIANTS)
    def test_schema_has_properties(self, variant: str) -> None:
        schema = json.loads((DEMO_DIR / variant / "schema.json").read_text())
        assert "properties" in schema
        assert len(schema["properties"]) >= 3

    @pytest.mark.parametrize("variant", VARIANTS)
    def test_schema_has_required_fields(self, variant: str) -> None:
        schema = json.loads((DEMO_DIR / variant / "schema.json").read_text())
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

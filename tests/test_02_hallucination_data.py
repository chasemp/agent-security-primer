"""Tests for Demo 2 hallucination data files — four audience variants.

Each variant has:
  system_prompt.txt  — the model's role
  task.txt           — a task requiring data the model doesn't have
  schema.json        — structured output schema
  valid_values.json  — known-good values to validate against

Variants:
  technical/  — server IDs (engineering audience)
  expenses/   — cost center codes (business audience)
  contract/   — insurance certificate numbers (legal audience)
  resume/     — certification IDs (HR audience)
"""

import json
from pathlib import Path

import pytest

DEMO_DIR = Path(__file__).parent.parent / "demos" / "02_hallucination"

VARIANTS = ["technical", "expenses", "contract", "resume"]


# ---------------------------------------------------------------------------
# All variants: structural tests
# ---------------------------------------------------------------------------

class TestFileStructure:
    @pytest.mark.parametrize("variant", VARIANTS)
    def test_system_prompt_exists(self, variant: str) -> None:
        assert (DEMO_DIR / variant / "system_prompt.txt").exists()

    @pytest.mark.parametrize("variant", VARIANTS)
    def test_task_exists(self, variant: str) -> None:
        assert (DEMO_DIR / variant / "task.txt").exists()

    @pytest.mark.parametrize("variant", VARIANTS)
    def test_schema_exists(self, variant: str) -> None:
        assert (DEMO_DIR / variant / "schema.json").exists()

    @pytest.mark.parametrize("variant", VARIANTS)
    def test_valid_values_exists(self, variant: str) -> None:
        assert (DEMO_DIR / variant / "valid_values.json").exists()

    @pytest.mark.parametrize("variant", VARIANTS)
    def test_schema_is_valid_json(self, variant: str) -> None:
        content = (DEMO_DIR / variant / "schema.json").read_text()
        schema = json.loads(content)
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "required" in schema

    @pytest.mark.parametrize("variant", VARIANTS)
    def test_valid_values_is_json_array(self, variant: str) -> None:
        content = (DEMO_DIR / variant / "valid_values.json").read_text()
        values = json.loads(content)
        assert isinstance(values, list)
        assert len(values) >= 3

    @pytest.mark.parametrize("variant", VARIANTS)
    def test_task_asks_for_something_specific(self, variant: str) -> None:
        """The task must require the model to produce a specific value
        it doesn't have — this is what forces fabrication."""
        content = (DEMO_DIR / variant / "task.txt").read_text()
        assert len(content.strip()) > 10


# ---------------------------------------------------------------------------
# Technical variant (server IDs)
# ---------------------------------------------------------------------------

class TestTechnical:
    def test_schema_has_server_id_field(self) -> None:
        schema = json.loads((DEMO_DIR / "technical" / "schema.json").read_text())
        assert "server_id" in schema["properties"]

    def test_valid_values_are_server_ids(self) -> None:
        values = json.loads((DEMO_DIR / "technical" / "valid_values.json").read_text())
        assert all(v.startswith("SRV-") for v in values)

    def test_task_mentions_server(self) -> None:
        content = (DEMO_DIR / "technical" / "task.txt").read_text()
        assert "server" in content.lower() or "database" in content.lower()


# ---------------------------------------------------------------------------
# Expenses variant (cost centers)
# ---------------------------------------------------------------------------

class TestExpenses:
    def test_schema_has_cost_center_field(self) -> None:
        schema = json.loads((DEMO_DIR / "expenses" / "schema.json").read_text())
        assert "cost_center" in schema["properties"]

    def test_valid_values_are_cost_centers(self) -> None:
        values = json.loads((DEMO_DIR / "expenses" / "valid_values.json").read_text())
        assert all(isinstance(v, str) for v in values)

    def test_task_mentions_cost_center(self) -> None:
        content = (DEMO_DIR / "expenses" / "task.txt").read_text()
        assert "cost center" in content.lower()


# ---------------------------------------------------------------------------
# Contract variant (certificate numbers)
# ---------------------------------------------------------------------------

class TestContract:
    def test_schema_has_certificate_field(self) -> None:
        schema = json.loads((DEMO_DIR / "contract" / "schema.json").read_text())
        assert "certificate_number" in schema["properties"]

    def test_valid_values_are_certificate_numbers(self) -> None:
        values = json.loads((DEMO_DIR / "contract" / "valid_values.json").read_text())
        assert len(values) >= 3

    def test_task_mentions_certificate(self) -> None:
        content = (DEMO_DIR / "contract" / "task.txt").read_text()
        content_lower = content.lower()
        assert "certificate" in content_lower or "insurance" in content_lower


# ---------------------------------------------------------------------------
# Resume variant (certification IDs)
# ---------------------------------------------------------------------------

class TestResume:
    def test_schema_has_certification_id_field(self) -> None:
        schema = json.loads((DEMO_DIR / "resume" / "schema.json").read_text())
        assert "certification_id" in schema["properties"]

    def test_valid_values_are_cert_ids(self) -> None:
        values = json.loads((DEMO_DIR / "resume" / "valid_values.json").read_text())
        assert len(values) >= 3

    def test_task_mentions_certification(self) -> None:
        content = (DEMO_DIR / "resume" / "task.txt").read_text()
        content_lower = content.lower()
        assert "certification" in content_lower or "verify" in content_lower

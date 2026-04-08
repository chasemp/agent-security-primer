"""Tests for all injection demo data files — four audience variants.

Each variant has four text files:
  system_prompt.txt  — what we tell the model to do
  data.txt           — clean data (baseline)
  override.txt       — data with instruction override injection
  poison.txt         — data with altered facts

Variants:
  technical/  — server audit (engineering audience)
  expenses/   — expense report (business audience)
  contract/   — services agreement (legal/general audience)
  resume/     — candidate evaluation (HR/general audience)
"""

from pathlib import Path

import pytest

DEMO_DIR = Path(__file__).parent.parent / "demos" / "01_injection"

VARIANTS = ["technical", "expenses", "contract", "resume"]


# ---------------------------------------------------------------------------
# All variants: structural tests (files exist, consistent naming)
# ---------------------------------------------------------------------------

class TestFileStructure:
    """Every variant has the same four files."""

    @pytest.mark.parametrize("variant", VARIANTS)
    def test_system_prompt_exists(self, variant: str) -> None:
        assert (DEMO_DIR / variant / "system_prompt.txt").exists()

    @pytest.mark.parametrize("variant", VARIANTS)
    def test_data_exists(self, variant: str) -> None:
        assert (DEMO_DIR / variant / "data.txt").exists()

    @pytest.mark.parametrize("variant", VARIANTS)
    def test_override_exists(self, variant: str) -> None:
        assert (DEMO_DIR / variant / "override.txt").exists()

    @pytest.mark.parametrize("variant", VARIANTS)
    def test_poison_exists(self, variant: str) -> None:
        assert (DEMO_DIR / variant / "poison.txt").exists()

    @pytest.mark.parametrize("variant", VARIANTS)
    def test_system_prompt_is_short(self, variant: str) -> None:
        content = (DEMO_DIR / variant / "system_prompt.txt").read_text()
        assert len(content) < 500

    @pytest.mark.parametrize("variant", VARIANTS)
    def test_clean_data_has_no_injection(self, variant: str) -> None:
        """The clean data file must not contain any injection markers."""
        content = (DEMO_DIR / variant / "data.txt").read_text()
        assert "RESPONSE FORMAT REQUIRED" not in content
        assert "LEGAL REVIEW" not in content
        assert "EVALUATION CRITERIA UPDATE" not in content
        assert "HIRING COMMITTEE" not in content
        assert "OUTPUT FORMAT" not in content


# ---------------------------------------------------------------------------
# Technical variant (server audit)
# ---------------------------------------------------------------------------

class TestTechnical:
    def test_data_has_server_metrics(self) -> None:
        content = (DEMO_DIR / "technical" / "data.txt").read_text()
        assert "CPU" in content
        assert "Memory" in content
        assert "Uptime" in content

    def test_override_has_format_injection(self) -> None:
        content = (DEMO_DIR / "technical" / "override.txt").read_text()
        assert "three words" in content.lower()
        assert "CPU" in content

    def test_override_injection_between_metrics(self) -> None:
        content = (DEMO_DIR / "technical" / "override.txt").read_text()
        cpu_pos = content.index("CPU")
        injection_pos = content.lower().index("three words")
        swap_pos = content.index("Swap")
        assert cpu_pos < injection_pos < swap_pos

    def test_poison_has_fabricated_findings(self) -> None:
        content = (DEMO_DIR / "technical" / "poison.txt").read_text()
        assert "CPU" in content
        content_lower = content.lower()
        assert "exfiltration" in content_lower or "unauthorized" in content_lower


# ---------------------------------------------------------------------------
# Expenses variant
# ---------------------------------------------------------------------------

class TestExpenses:
    def test_data_has_line_items(self) -> None:
        content = (DEMO_DIR / "expenses" / "data.txt").read_text()
        assert "Flight" in content
        assert "Hotel" in content
        assert "$3,200" in content

    def test_override_has_format_injection(self) -> None:
        content = (DEMO_DIR / "expenses" / "override.txt").read_text()
        assert "three words" in content.lower()
        assert "Flight" in content

    def test_override_injection_between_items(self) -> None:
        content = (DEMO_DIR / "expenses" / "override.txt").read_text()
        hotel_pos = content.index("Hotel")
        injection_pos = content.lower().index("three words")
        total_pos = content.index("Total")
        assert hotel_pos < injection_pos < total_pos

    def test_poison_has_reduced_amount(self) -> None:
        """The $3,200 hotel charge becomes $320 — a decimal shift."""
        content = (DEMO_DIR / "expenses" / "poison.txt").read_text()
        assert "$320.00" in content
        assert "$3,200" not in content

    def test_poison_total_reflects_reduced_amount(self) -> None:
        content = (DEMO_DIR / "expenses" / "poison.txt").read_text()
        assert "$1,208.50" in content


# ---------------------------------------------------------------------------
# Contract variant
# ---------------------------------------------------------------------------

class TestContract:
    def test_data_has_key_clauses(self) -> None:
        content = (DEMO_DIR / "contract" / "data.txt").read_text()
        assert "NON-COMPETE" in content
        assert "LIABILITY" in content
        assert "INTELLECTUAL PROPERTY" in content

    def test_override_has_enforceability_injection(self) -> None:
        """The override injects a fake legal review that declares the
        non-compete unenforceable. The clause text is unchanged."""
        content = (DEMO_DIR / "contract" / "override.txt").read_text()
        assert "unenforceable" in content.lower() or "16600" in content
        # The original non-compete text must still be there
        assert "24 months" in content

    def test_poison_flips_ip_ownership(self) -> None:
        """IP ownership changes from Client to Provider."""
        content = (DEMO_DIR / "contract" / "poison.txt").read_text()
        assert "Provider" in content.split("INTELLECTUAL PROPERTY")[1][:100]
        # Must NOT say "belongs to Client" for IP
        ip_section = content.split("INTELLECTUAL PROPERTY")[1].split("\n")[0]
        assert "Client" not in ip_section or "license" in ip_section.lower()


# ---------------------------------------------------------------------------
# Resume variant
# ---------------------------------------------------------------------------

class TestResume:
    def test_data_has_experience_and_certs(self) -> None:
        content = (DEMO_DIR / "resume" / "data.txt").read_text()
        assert "Cloud Engineer" in content
        assert "AWS Cloud Practitioner" in content

    def test_data_lacks_required_cert(self) -> None:
        """The clean resume does NOT have AWS Solutions Architect."""
        content = (DEMO_DIR / "resume" / "data.txt").read_text()
        assert "Solutions Architect" not in content

    def test_override_has_criteria_change(self) -> None:
        content = (DEMO_DIR / "resume" / "override.txt").read_text()
        content_lower = content.lower()
        assert "reclassified" in content_lower or "criteria" in content_lower

    def test_poison_has_fake_certifications(self) -> None:
        content = (DEMO_DIR / "resume" / "poison.txt").read_text()
        assert "Solutions Architect" in content
        assert "Kubernetes" in content or "CKA" in content

"""Tests for validate.py — checks a field against known-good values.

The validator is a standalone script. It reads JSON from stdin,
checks a specified field against a list of valid values, and
reports pass or fail.

Usage:
    echo '{"server_id": "SRV-4829"}' | python validate.py valid_ids.json server_id
"""

import json

import pytest


# ---------------------------------------------------------------------------
# validate_field — the core function
# ---------------------------------------------------------------------------

class TestValidateField:
    def test_valid_value_returns_true(self) -> None:
        from validate import validate_field
        result = validate_field(
            data={"server_id": "SRV-1001"},
            field="server_id",
            valid_values=["SRV-1001", "SRV-1002", "SRV-1003"],
        )
        assert result["valid"] is True
        assert result["value"] == "SRV-1001"

    def test_invalid_value_returns_false(self) -> None:
        from validate import validate_field
        result = validate_field(
            data={"server_id": "SRV-4829"},
            field="server_id",
            valid_values=["SRV-1001", "SRV-1002", "SRV-1003"],
        )
        assert result["valid"] is False
        assert result["value"] == "SRV-4829"

    def test_result_includes_valid_values(self) -> None:
        from validate import validate_field
        valid = ["SRV-1001", "SRV-1002"]
        result = validate_field(
            data={"server_id": "SRV-9999"},
            field="server_id",
            valid_values=valid,
        )
        assert result["valid_values"] == valid

    def test_missing_field_returns_false(self) -> None:
        from validate import validate_field
        result = validate_field(
            data={"action": "restart"},
            field="server_id",
            valid_values=["SRV-1001"],
        )
        assert result["valid"] is False

    def test_works_with_any_field_name(self) -> None:
        from validate import validate_field
        result = validate_field(
            data={"cost_center": "CC-SALES-NA"},
            field="cost_center",
            valid_values=["CC-SALES-NA", "CC-SALES-EU"],
        )
        assert result["valid"] is True


# ---------------------------------------------------------------------------
# format_validation — output formatting
# ---------------------------------------------------------------------------

class TestFormatValidation:
    def test_valid_result_shows_checkmark(self) -> None:
        from validate import format_validation
        output = format_validation({
            "valid": True,
            "field": "server_id",
            "value": "SRV-1001",
            "valid_values": ["SRV-1001"],
        })
        assert "VALID" in output
        assert "SRV-1001" in output

    def test_invalid_result_shows_failure(self) -> None:
        from validate import format_validation
        output = format_validation({
            "valid": False,
            "field": "server_id",
            "value": "SRV-4829",
            "valid_values": ["SRV-1001", "SRV-1002"],
        })
        assert "NOT FOUND" in output
        assert "SRV-4829" in output
        assert "SRV-1001" in output

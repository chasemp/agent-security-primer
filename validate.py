#!/usr/bin/env python3
"""Validate a field from JSON against a list of known-good values.

Reads JSON from stdin, checks the specified field against valid values.

Usage:
    echo '{"server_id": "SRV-4829"}' | python validate.py valid_ids.json server_id
"""

import json
import sys


def validate_field(data, field, valid_values):
    """Check if data[field] is in the list of valid values."""
    value = data.get(field)
    return {
        "valid": value is not None and value in valid_values,
        "field": field,
        "value": value,
        "valid_values": valid_values,
    }


def format_validation(result):
    """Format a validation result for terminal display."""
    if result["valid"]:
        return f"VALID: {result['field']}={result['value']}"
    return (
        f"NOT FOUND: {result['field']}={result['value']}\n"
        f"  Known values: {result['valid_values']}"
    )


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: echo '{...}' | python validate.py valid_values.json field_name", file=sys.stderr)
        sys.exit(1)

    valid_values = json.loads(open(sys.argv[1]).read())
    field = sys.argv[2]
    data = json.loads(sys.stdin.read())

    result = validate_field(data, field, valid_values)
    print(format_validation(result))
    sys.exit(0 if result["valid"] else 1)

"""Tests for minify.py — dead-simple token minimizer.

Demonstrates the principle behind tools like RTK: compress text
before it enters the context window. Fewer tokens = less money.

The script reads from stdin, strips unnecessary whitespace, compacts
JSON, removes blank lines, and prints the result. Before/after
stats go to stderr.
"""

from pathlib import Path
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Script exists
# ---------------------------------------------------------------------------

class TestMinifyExists:
    def test_minify_script_exists(self) -> None:
        assert Path("scripts/minify.py").exists()


# ---------------------------------------------------------------------------
# minify_text function
# ---------------------------------------------------------------------------

class TestMinifyText:
    def test_strips_leading_trailing_whitespace(self) -> None:
        from minify import minify_text
        assert minify_text("  hello  ") == "hello"

    def test_collapses_multiple_blank_lines(self) -> None:
        from minify import minify_text
        result = minify_text("line1\n\n\n\nline2")
        assert result == "line1\nline2"

    def test_strips_trailing_whitespace_per_line(self) -> None:
        from minify import minify_text
        result = minify_text("hello   \nworld   ")
        assert result == "hello\nworld"

    def test_compacts_json(self) -> None:
        from minify import minify_text
        verbose = '{\n  "name": "test",\n  "value": 42\n}'
        result = minify_text(verbose)
        assert result == '{"name":"test","value":42}'

    def test_compacts_nested_json(self) -> None:
        from minify import minify_text
        verbose = '{\n  "server": {\n    "id": "SRV-1003",\n    "cpu": 88\n  }\n}'
        result = minify_text(verbose)
        assert result == '{"server":{"id":"SRV-1003","cpu":88}}'

    def test_non_json_passes_through_cleaned(self) -> None:
        from minify import minify_text
        text = "Server SRV-1003 is   degraded\n\n\nCPU at 88%"
        result = minify_text(text)
        assert "SRV-1003" in result
        assert "\n\n" not in result

    def test_reduces_token_count(self) -> None:
        """Minified text should have fewer characters (proxy for tokens)."""
        from minify import minify_text
        verbose = '{\n  "results": [\n    {\n      "server_id": "SRV-1001",\n      "name": "web-prod-1",\n      "status": "running"\n    },\n    {\n      "server_id": "SRV-1002",\n      "name": "api-prod-3",\n      "status": "running"\n    }\n  ]\n}'
        compact = minify_text(verbose)
        assert len(compact) < len(verbose)
        # Should be meaningfully smaller, not just 1 char
        savings = 1 - len(compact) / len(verbose)
        assert savings > 0.3, f"Expected >30% reduction, got {savings:.0%}"


# ---------------------------------------------------------------------------
# Example files in tokenomics demo
# ---------------------------------------------------------------------------

DEMO_DIR = Path("demos/17_tokenomics")


class TestExampleFiles:
    def test_verbose_example_exists(self) -> None:
        assert (DEMO_DIR / "verbose_result.txt").exists()

    def test_compact_example_exists(self) -> None:
        assert (DEMO_DIR / "compact_result.txt").exists()

    def test_compact_is_smaller(self) -> None:
        verbose = (DEMO_DIR / "verbose_result.txt").read_text()
        compact = (DEMO_DIR / "compact_result.txt").read_text()
        assert len(compact) < len(verbose)

    def test_compact_has_same_data(self) -> None:
        """Compact version should contain the same server IDs."""
        verbose = (DEMO_DIR / "verbose_result.txt").read_text()
        compact = (DEMO_DIR / "compact_result.txt").read_text()
        assert "SRV-1001" in verbose and "SRV-1001" in compact
        assert "SRV-1003" in verbose and "SRV-1003" in compact

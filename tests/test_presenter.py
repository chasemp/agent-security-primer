"""Tests for the presenter CLI.

The presenter is the single command the speaker types to run the talk:
  presenter run 1              → Run demo 1 only
  presenter run banana         → Run by name
  presenter run all            → Full presentation sequence
  presenter run 1 gopro 6     → Run specific demos in order
  presenter list               → List all demos with sections
  presenter check              → Verify API key, deps, connectivity

These tests use Click's CliRunner to invoke commands without a real
terminal. No API calls — we're testing the CLI plumbing, not the demos.
"""

from unittest.mock import patch

from click.testing import CliRunner

from presenter import cli


class TestListCommand:
    """presenter list — shows all registered demos.

    With no demos registered yet (Phase 1), this should succeed
    and indicate the registry is empty. Once Phase 2+ adds demos,
    it should show them in order with section tags.
    """

    def test_list_exits_zero(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["list"])
        assert result.exit_code == 0

    def test_list_shows_header(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["list"])
        # Should show some kind of header/title for the demo list
        assert "demo" in result.output.lower() or "Demo" in result.output


class TestCheckCommand:
    """presenter check — pre-talk verification.

    Verifies the claude-agent-sdk is available and core deps are importable.
    The Agent SDK handles auth via the Claude Code CLI — no API key needed
    for most demos. Demo 7 (temperature) is the exception and gets a
    yellow warning if anthropic SDK or ANTHROPIC_API_KEY is missing.
    """

    def test_check_verifies_core_deps(self) -> None:
        """Check should pass when claude-agent-sdk and core deps are installed."""
        runner = CliRunner()
        result = runner.invoke(cli, ["check"])
        assert result.exit_code == 0
        assert "claude-agent-sdk" in result.output

    def test_check_reports_demo7_status(self) -> None:
        """Check should mention Demo 7 temperature status (either live or prerecorded)."""
        runner = CliRunner()
        result = runner.invoke(cli, ["check"])
        # Should mention anthropic/Demo 7 regardless of whether the key exists
        assert "anthropic" in result.output.lower() or "Demo 7" in result.output


class TestRunCommand:
    """presenter run — the main event.

    In Phase 1 there are no demos registered, so `run` with an unknown
    ID should report that gracefully. The async demo execution is tested
    via demo-specific tests in later phases.
    """

    def test_run_unknown_demo_reports_error(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["run", "nonexistent"])
        assert result.exit_code == 0  # graceful, not a crash
        assert "no demos" in result.output.lower() or "not found" in result.output.lower() or "No matching" in result.output

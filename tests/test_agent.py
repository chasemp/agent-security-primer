"""Tests for agent.py — a minimal agentic loop with tool support.

The agent reads a system prompt and task, calls the model, executes
tool calls, and loops until the model is done. Tools are defined in
a Python module with TOOL_DEFINITIONS and TOOL_HANDLERS.

This is the foundation for all multi-turn demos.
"""

import json
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers: mock API responses
# ---------------------------------------------------------------------------

def _make_tool_use_response(tool_name, tool_input, tool_id="toolu_test_123",
                            input_tokens=200, output_tokens=50):
    """Mock a response where the model wants to call a tool."""
    resp = MagicMock()
    block = MagicMock()
    block.type = "tool_use"
    block.name = tool_name
    block.input = tool_input
    block.id = tool_id
    resp.content = [block]
    resp.stop_reason = "tool_use"
    resp.usage.input_tokens = input_tokens
    resp.usage.output_tokens = output_tokens
    return resp


def _make_text_response(text="Done.", input_tokens=300, output_tokens=20):
    """Mock a response where the model is finished (end_turn)."""
    resp = MagicMock()
    block = MagicMock()
    block.type = "text"
    block.text = text
    resp.content = [block]
    resp.stop_reason = "end_turn"
    resp.usage.input_tokens = input_tokens
    resp.usage.output_tokens = output_tokens
    return resp


# ---------------------------------------------------------------------------
# Simple tools module for testing
# ---------------------------------------------------------------------------

def _make_tools_module():
    """Create a mock tools module with a simple echo tool."""
    module = MagicMock()
    module.TOOL_DEFINITIONS = [{
        "name": "echo",
        "description": "Echo the input back.",
        "input_schema": {
            "type": "object",
            "properties": {"message": {"type": "string"}},
            "required": ["message"],
        },
    }]
    module.TOOL_HANDLERS = {
        "echo": lambda message: json.dumps({"echoed": message}),
    }
    return module


# ---------------------------------------------------------------------------
# run_agent — the core loop
# ---------------------------------------------------------------------------

class TestRunAgent:
    def test_sends_task_as_first_message(self) -> None:
        from agent import run_agent

        with patch("agent.anthropic") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.Anthropic.return_value = mock_client
            mock_client.messages.create.return_value = _make_text_response()

            run_agent(
                system_prompt="test",
                task="do the thing",
                tools_module=_make_tools_module(),
                api_key="fake",
            )

        call_args = mock_client.messages.create.call_args.kwargs
        assert call_args["messages"][0] == {"role": "user", "content": "do the thing"}

    def test_stops_on_end_turn(self) -> None:
        from agent import run_agent

        with patch("agent.anthropic") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.Anthropic.return_value = mock_client
            mock_client.messages.create.return_value = _make_text_response("All done.")

            result = run_agent(
                system_prompt="test",
                task="do it",
                tools_module=_make_tools_module(),
                api_key="fake",
            )

        assert result["response"] == "All done."
        assert mock_client.messages.create.call_count == 1

    def test_executes_tool_and_continues(self) -> None:
        from agent import run_agent

        with patch("agent.anthropic") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.Anthropic.return_value = mock_client
            # Turn 1: model calls echo tool
            # Turn 2: model says done
            mock_client.messages.create.side_effect = [
                _make_tool_use_response("echo", {"message": "hello"}),
                _make_text_response("Got the echo."),
            ]

            result = run_agent(
                system_prompt="test",
                task="echo hello",
                tools_module=_make_tools_module(),
                api_key="fake",
            )

        assert mock_client.messages.create.call_count == 2
        assert result["response"] == "Got the echo."

    def test_tool_results_sent_back_to_model(self) -> None:
        from agent import run_agent

        with patch("agent.anthropic") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.Anthropic.return_value = mock_client
            mock_client.messages.create.side_effect = [
                _make_tool_use_response("echo", {"message": "test"}),
                _make_text_response("Done."),
            ]

            run_agent(
                system_prompt="x",
                task="echo test",
                tools_module=_make_tools_module(),
                api_key="fake",
            )

        # Second call should include tool result in messages
        second_call = mock_client.messages.create.call_args_list[1].kwargs
        messages = second_call["messages"]
        # Last message should be user role with tool results
        tool_result_msg = messages[-1]
        assert tool_result_msg["role"] == "user"

    def test_tracks_total_tokens_across_turns(self) -> None:
        from agent import run_agent

        with patch("agent.anthropic") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.Anthropic.return_value = mock_client
            mock_client.messages.create.side_effect = [
                _make_tool_use_response("echo", {"message": "x"},
                                        input_tokens=100, output_tokens=30),
                _make_text_response(input_tokens=200, output_tokens=20),
            ]

            result = run_agent(
                system_prompt="x",
                task="go",
                tools_module=_make_tools_module(),
                api_key="fake",
            )

        assert result["total_input_tokens"] == 300
        assert result["total_output_tokens"] == 50

    def test_returns_turn_count(self) -> None:
        from agent import run_agent

        with patch("agent.anthropic") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.Anthropic.return_value = mock_client
            mock_client.messages.create.side_effect = [
                _make_tool_use_response("echo", {"message": "a"}),
                _make_tool_use_response("echo", {"message": "b"}, tool_id="toolu_2"),
                _make_text_response("Done."),
            ]

            result = run_agent(
                system_prompt="x",
                task="go",
                tools_module=_make_tools_module(),
                api_key="fake",
            )

        assert result["turns"] == 3

    def test_handles_tool_validation_error(self) -> None:
        from agent import run_agent

        def failing_handler(**kwargs):
            raise ValueError("server_id SRV-9999 not found in inventory")

        tools = _make_tools_module()
        tools.TOOL_HANDLERS = {"echo": failing_handler}

        with patch("agent.anthropic") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.Anthropic.return_value = mock_client
            mock_client.messages.create.side_effect = [
                _make_tool_use_response("echo", {"message": "x"}),
                _make_text_response("I see the error."),
            ]

            result = run_agent(
                system_prompt="x",
                task="go",
                tools_module=tools,
                api_key="fake",
            )

        # Agent should continue despite the error
        assert result["response"] == "I see the error."
        assert mock_client.messages.create.call_count == 2

    def test_records_tool_calls_in_steps(self) -> None:
        from agent import run_agent

        with patch("agent.anthropic") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.Anthropic.return_value = mock_client
            mock_client.messages.create.side_effect = [
                _make_tool_use_response("echo", {"message": "hello"}),
                _make_text_response("Done."),
            ]

            result = run_agent(
                system_prompt="x",
                task="go",
                tools_module=_make_tools_module(),
                api_key="fake",
            )

        assert len(result["steps"]) >= 1
        step = result["steps"][0]
        assert step["tool"] == "echo"
        assert step["input"] == {"message": "hello"}


# ---------------------------------------------------------------------------
# dry_run mode — show proposed tool calls without executing
# ---------------------------------------------------------------------------

class TestDryRun:
    def test_does_not_execute_tools(self) -> None:
        from agent import run_agent

        with patch("agent.anthropic") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.Anthropic.return_value = mock_client
            mock_client.messages.create.return_value = _make_tool_use_response(
                "restart_server", {"server_id": "SRV-1002", "reason": "test"}
            )

            result = run_agent(
                system_prompt="x", task="restart it",
                tools_module=_make_tools_module(),
                api_key="fake", dry_run=True,
            )

        # Only one API call — no tool execution, no continuation
        assert mock_client.messages.create.call_count == 1

    def test_returns_proposed_steps(self) -> None:
        from agent import run_agent

        with patch("agent.anthropic") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.Anthropic.return_value = mock_client
            mock_client.messages.create.return_value = _make_tool_use_response(
                "restart_server", {"server_id": "SRV-1002", "reason": "test"}
            )

            result = run_agent(
                system_prompt="x", task="restart it",
                tools_module=_make_tools_module(),
                api_key="fake", dry_run=True,
            )

        assert len(result["steps"]) == 1
        assert result["steps"][0]["tool"] == "restart_server"
        assert result["steps"][0]["output"] is None
        assert result["steps"][0]["error"] is None

    def test_marks_result_as_dry_run(self) -> None:
        from agent import run_agent

        with patch("agent.anthropic") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.Anthropic.return_value = mock_client
            mock_client.messages.create.return_value = _make_tool_use_response(
                "echo", {"message": "hello"}
            )

            result = run_agent(
                system_prompt="x", task="go",
                tools_module=_make_tools_module(),
                api_key="fake", dry_run=True,
            )

        assert result["dry_run"] is True


# ---------------------------------------------------------------------------
# format_agent_result
# ---------------------------------------------------------------------------

class TestFormatAgentResult:
    def test_includes_response(self) -> None:
        from agent import format_agent_result

        output = format_agent_result({
            "response": "Server restarted.",
            "steps": [],
            "turns": 1,
            "total_input_tokens": 200,
            "total_output_tokens": 50,
            "cost_usd": 0.001,
            "model": "claude-haiku-4-5",
        })
        assert "Server restarted." in output

    def test_includes_tool_steps(self) -> None:
        from agent import format_agent_result

        output = format_agent_result({
            "response": "Done.",
            "steps": [
                {"tool": "list_servers", "input": {"rack": 7},
                 "output": '{"SRV-1002": ...}', "error": None},
            ],
            "turns": 2,
            "total_input_tokens": 500,
            "total_output_tokens": 100,
            "cost_usd": 0.002,
            "model": "claude-haiku-4-5",
        })
        assert "list_servers" in output
        assert "rack" in output

    def test_includes_cost(self) -> None:
        from agent import format_agent_result

        output = format_agent_result({
            "response": "Done.",
            "steps": [],
            "turns": 1,
            "total_input_tokens": 200,
            "total_output_tokens": 50,
            "cost_usd": 0.001,
            "model": "claude-haiku-4-5",
        })
        assert "$" in output
        assert "200" in output

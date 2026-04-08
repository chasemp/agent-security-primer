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
                            input_tokens=200, output_tokens=50,
                            cache_creation_input_tokens=0,
                            cache_read_input_tokens=0):
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
    resp.usage.cache_creation_input_tokens = cache_creation_input_tokens
    resp.usage.cache_read_input_tokens = cache_read_input_tokens
    return resp


def _make_text_response(text="Done.", input_tokens=300, output_tokens=20,
                        cache_creation_input_tokens=0,
                        cache_read_input_tokens=0):
    """Mock a response where the model is finished (end_turn)."""
    resp = MagicMock()
    block = MagicMock()
    block.type = "text"
    block.text = text
    resp.content = [block]
    resp.stop_reason = "end_turn"
    resp.usage.input_tokens = input_tokens
    resp.usage.output_tokens = output_tokens
    resp.usage.cache_creation_input_tokens = cache_creation_input_tokens
    resp.usage.cache_read_input_tokens = cache_read_input_tokens
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
# plan mode — show proposed tool calls without executing
# ---------------------------------------------------------------------------

class TestPlanMode:
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
                api_key="fake", plan=True,
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
                api_key="fake", plan=True,
            )

        assert len(result["steps"]) == 1
        assert result["steps"][0]["tool"] == "restart_server"
        assert result["steps"][0]["output"] is None
        assert result["steps"][0]["error"] is None

    def test_marks_result_as_plan(self) -> None:
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
                api_key="fake", plan=True,
            )

        assert result["plan"] is True


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

    def test_format_shows_cache_stats_when_present(self) -> None:
        from agent import format_agent_result

        output = format_agent_result({
            "response": "Done.",
            "steps": [],
            "turns": 3,
            "total_input_tokens": 500,
            "total_output_tokens": 100,
            "total_cache_creation_tokens": 2000,
            "total_cache_read_tokens": 4000,
            "cost_usd": 0.002,
            "model": "claude-haiku-4-5",
        })
        assert "Cache write" in output
        assert "2000" in output
        assert "Cache read" in output
        assert "4000" in output

    def test_format_omits_cache_stats_when_zero(self) -> None:
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
        assert "Cache" not in output


# ---------------------------------------------------------------------------
# cache mode — prompt caching with cache_control
# ---------------------------------------------------------------------------

class TestCacheMode:
    def test_cache_sends_structured_system_prompt(self) -> None:
        """When cache=True, system prompt is a list with cache_control."""
        from agent import run_agent

        with patch("agent.anthropic") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.Anthropic.return_value = mock_client
            mock_client.messages.create.return_value = _make_text_response()

            run_agent(
                system_prompt="test prompt",
                task="go",
                tools_module=_make_tools_module(),
                api_key="fake",
                cache=True,
            )

        call_args = mock_client.messages.create.call_args.kwargs
        system = call_args["system"]
        assert isinstance(system, list)
        assert len(system) == 1
        assert system[0]["type"] == "text"
        assert system[0]["text"] == "test prompt"
        assert system[0]["cache_control"] == {"type": "ephemeral"}

    def test_no_cache_sends_string_system_prompt(self) -> None:
        """Default behavior: system prompt is a plain string."""
        from agent import run_agent

        with patch("agent.anthropic") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.Anthropic.return_value = mock_client
            mock_client.messages.create.return_value = _make_text_response()

            run_agent(
                system_prompt="test prompt",
                task="go",
                tools_module=_make_tools_module(),
                api_key="fake",
            )

        call_args = mock_client.messages.create.call_args.kwargs
        assert call_args["system"] == "test prompt"

    def test_cache_adds_cache_control_to_last_tool_definition(self) -> None:
        """When cache=True, the last tool definition gets cache_control
        so the API caches system prompt + all tool schemas as a prefix."""
        from agent import run_agent

        with patch("agent.anthropic") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.Anthropic.return_value = mock_client
            mock_client.messages.create.return_value = _make_text_response()

            run_agent(
                system_prompt="test",
                task="go",
                tools_module=_make_tools_module(),
                api_key="fake",
                cache=True,
            )

        call_args = mock_client.messages.create.call_args.kwargs
        tools = call_args["tools"]
        last_tool = tools[-1]
        assert "cache_control" in last_tool
        assert last_tool["cache_control"] == {"type": "ephemeral"}

    def test_no_cache_leaves_tool_definitions_unchanged(self) -> None:
        """Without cache, tool definitions have no cache_control."""
        from agent import run_agent

        with patch("agent.anthropic") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.Anthropic.return_value = mock_client
            mock_client.messages.create.return_value = _make_text_response()

            run_agent(
                system_prompt="test",
                task="go",
                tools_module=_make_tools_module(),
                api_key="fake",
            )

        call_args = mock_client.messages.create.call_args.kwargs
        tools = call_args["tools"]
        for tool in tools:
            assert "cache_control" not in tool

    def test_cache_does_not_mutate_original_tool_definitions(self) -> None:
        """Caching should copy tool defs, not mutate the module's originals."""
        from agent import run_agent

        tools_module = _make_tools_module()
        original_defs = [dict(d) for d in tools_module.TOOL_DEFINITIONS]

        with patch("agent.anthropic") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.Anthropic.return_value = mock_client
            mock_client.messages.create.return_value = _make_text_response()

            run_agent(
                system_prompt="test",
                task="go",
                tools_module=tools_module,
                api_key="fake",
                cache=True,
            )

        # Original definitions should be unchanged
        for orig, current in zip(original_defs, tools_module.TOOL_DEFINITIONS):
            assert "cache_control" not in current

    def test_tracks_cache_creation_tokens(self) -> None:
        from agent import run_agent

        with patch("agent.anthropic") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.Anthropic.return_value = mock_client
            mock_client.messages.create.side_effect = [
                _make_tool_use_response("echo", {"message": "x"},
                                        cache_creation_input_tokens=2000),
                _make_text_response(cache_creation_input_tokens=0),
            ]

            result = run_agent(
                system_prompt="x",
                task="go",
                tools_module=_make_tools_module(),
                api_key="fake",
                cache=True,
            )

        assert result["total_cache_creation_tokens"] == 2000

    def test_tracks_cache_read_tokens(self) -> None:
        from agent import run_agent

        with patch("agent.anthropic") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.Anthropic.return_value = mock_client
            mock_client.messages.create.side_effect = [
                _make_tool_use_response("echo", {"message": "x"},
                                        cache_creation_input_tokens=2000,
                                        cache_read_input_tokens=0),
                _make_text_response(cache_creation_input_tokens=0,
                                    cache_read_input_tokens=2000),
            ]

            result = run_agent(
                system_prompt="x",
                task="go",
                tools_module=_make_tools_module(),
                api_key="fake",
                cache=True,
            )

        assert result["total_cache_read_tokens"] == 2000

    def test_cache_control_only_on_latest_user_message(self) -> None:
        """Only the LATEST user message should have cache_control.
        The API allows at most 4 cache_control blocks per request.
        We use 3: system prompt + last tool def + latest user message.
        Prior user messages must have cache_control stripped."""
        from agent import run_agent

        with patch("agent.anthropic") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.Anthropic.return_value = mock_client
            mock_client.messages.create.side_effect = [
                _make_tool_use_response("echo", {"message": "a"}),
                _make_tool_use_response("echo", {"message": "b"}, tool_id="toolu_2"),
                _make_text_response("Done."),
            ]

            run_agent(
                system_prompt="test",
                task="go",
                tools_module=_make_tools_module(),
                api_key="fake",
                cache=True,
            )

        # Third API call: messages should have cache_control only on the LAST user msg
        third_call = mock_client.messages.create.call_args_list[2].kwargs
        messages = third_call["messages"]
        user_msgs = [m for m in messages if m["role"] == "user"]
        # All but the last user message should NOT have cache_control
        for msg in user_msgs[:-1]:
            if isinstance(msg["content"], list):
                for item in msg["content"]:
                    if isinstance(item, dict):
                        assert "cache_control" not in item, (
                            "Prior user messages should not have cache_control"
                        )
        # The last user message SHOULD have cache_control
        last_user = user_msgs[-1]
        last_content = last_user["content"][-1]
        assert "cache_control" in last_content

    def test_cache_adds_cache_control_to_conversation_messages(self) -> None:
        """When cache=True, the latest tool_result gets cache_control."""
        from agent import run_agent

        with patch("agent.anthropic") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.Anthropic.return_value = mock_client
            mock_client.messages.create.side_effect = [
                _make_tool_use_response("echo", {"message": "hi"}),
                _make_text_response("Done."),
            ]

            run_agent(
                system_prompt="test",
                task="go",
                tools_module=_make_tools_module(),
                api_key="fake",
                cache=True,
            )

        # Second API call should have cache_control on the last tool_result
        second_call = mock_client.messages.create.call_args_list[1].kwargs
        messages = second_call["messages"]
        # Find the user message with tool results (last user message)
        tool_result_msg = [m for m in messages if m["role"] == "user"][-1]
        last_result = tool_result_msg["content"][-1]
        assert "cache_control" in last_result
        assert last_result["cache_control"] == {"type": "ephemeral"}

    def test_no_cache_skips_conversation_cache_control(self) -> None:
        """Without cache, no cache_control on conversation messages."""
        from agent import run_agent

        with patch("agent.anthropic") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.Anthropic.return_value = mock_client
            mock_client.messages.create.side_effect = [
                _make_tool_use_response("echo", {"message": "hi"}),
                _make_text_response("Done."),
            ]

            run_agent(
                system_prompt="test",
                task="go",
                tools_module=_make_tools_module(),
                api_key="fake",
            )

        second_call = mock_client.messages.create.call_args_list[1].kwargs
        messages = second_call["messages"]
        tool_result_msg = [m for m in messages if m["role"] == "user"][-1]
        last_result = tool_result_msg["content"][-1]
        assert "cache_control" not in last_result

    def test_cost_accounts_for_cache_pricing(self) -> None:
        """Cache writes cost 1.25x input, cache reads cost 0.1x input."""
        from agent import run_agent

        with patch("agent.anthropic") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.Anthropic.return_value = mock_client
            # Turn 1: cache write of 1000 tokens, 100 regular input
            # Turn 2: cache read of 1000 tokens, 200 regular input
            mock_client.messages.create.side_effect = [
                _make_tool_use_response("echo", {"message": "x"},
                                        input_tokens=100, output_tokens=0,
                                        cache_creation_input_tokens=1000,
                                        cache_read_input_tokens=0),
                _make_text_response(input_tokens=200, output_tokens=0,
                                    cache_creation_input_tokens=0,
                                    cache_read_input_tokens=1000),
            ]

            result = run_agent(
                system_prompt="x",
                task="go",
                tools_module=_make_tools_module(),
                api_key="fake",
                cache=True,
            )

        # Haiku: input=$1/MTok, output=$5/MTok
        # Regular input: (100+200) * 1.00 / 1M = 0.000300
        # Cache write: 1000 * 1.00 * 1.25 / 1M = 0.001250
        # Cache read:  1000 * 1.00 * 0.10 / 1M = 0.000100
        # Output: 0
        # Total: 0.001650
        assert result["cost_usd"] == pytest.approx(0.001650)


# ---------------------------------------------------------------------------
# thinking mode — extended thinking in agent loop
# ---------------------------------------------------------------------------

class TestThinkingMode:
    def test_thinking_passes_thinking_config(self) -> None:
        """When thinking=True, API call includes thinking parameter."""
        from agent import run_agent

        with patch("agent.anthropic") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.Anthropic.return_value = mock_client
            mock_client.messages.create.return_value = _make_text_response()

            run_agent(
                system_prompt="x",
                task="go",
                tools_module=_make_tools_module(),
                api_key="fake",
                thinking=True,
            )

        call_args = mock_client.messages.create.call_args.kwargs
        assert "thinking" in call_args
        assert call_args["thinking"]["type"] == "enabled"

    def test_thinking_sets_higher_max_tokens(self) -> None:
        """Thinking needs a higher max_tokens to accommodate budget."""
        from agent import run_agent

        with patch("agent.anthropic") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.Anthropic.return_value = mock_client
            mock_client.messages.create.return_value = _make_text_response()

            run_agent(
                system_prompt="x",
                task="go",
                tools_module=_make_tools_module(),
                api_key="fake",
                thinking=True,
            )

        call_args = mock_client.messages.create.call_args.kwargs
        assert call_args["max_tokens"] > 4096

    def test_no_thinking_by_default(self) -> None:
        """Default behavior: no thinking parameter."""
        from agent import run_agent

        with patch("agent.anthropic") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.Anthropic.return_value = mock_client
            mock_client.messages.create.return_value = _make_text_response()

            run_agent(
                system_prompt="x",
                task="go",
                tools_module=_make_tools_module(),
                api_key="fake",
            )

        call_args = mock_client.messages.create.call_args.kwargs
        assert "thinking" not in call_args


# ---------------------------------------------------------------------------
# token budget circuit breaker — hard stop on cumulative tokens
# ---------------------------------------------------------------------------

class TestTokenBudget:
    def test_stops_when_budget_exceeded(self) -> None:
        """Agent stops after a turn if cumulative tokens exceed budget."""
        from agent import run_agent

        with patch("agent.anthropic") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.Anthropic.return_value = mock_client
            # Turn 1: 200 input + 50 output = 250 tokens (over budget of 200)
            # Should stop after turn 1 even though model wants a tool call
            mock_client.messages.create.side_effect = [
                _make_tool_use_response("echo", {"message": "x"},
                                        input_tokens=200, output_tokens=50),
                _make_text_response("Should not reach this."),
            ]

            result = run_agent(
                system_prompt="x",
                task="go",
                tools_module=_make_tools_module(),
                api_key="fake",
                max_tokens_budget=200,
            )

        assert result["turns"] == 1
        assert result["budget_exceeded"] is True
        assert mock_client.messages.create.call_count == 1

    def test_continues_when_under_budget(self) -> None:
        """Agent continues normally when within budget."""
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
                max_tokens_budget=10000,
            )

        assert result["turns"] == 2
        assert result["budget_exceeded"] is False

    def test_no_budget_by_default(self) -> None:
        """Without max_tokens_budget, no budget_exceeded in result."""
        from agent import run_agent

        with patch("agent.anthropic") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.Anthropic.return_value = mock_client
            mock_client.messages.create.return_value = _make_text_response()

            result = run_agent(
                system_prompt="x",
                task="go",
                tools_module=_make_tools_module(),
                api_key="fake",
            )

        assert "budget_exceeded" not in result

    def test_format_shows_budget_exceeded_warning(self) -> None:
        from agent import format_agent_result

        output = format_agent_result({
            "response": "",
            "steps": [{"tool": "echo", "input": {"message": "x"},
                       "output": '{"echoed": "x"}', "error": None}],
            "turns": 3,
            "total_input_tokens": 5200,
            "total_output_tokens": 300,
            "cost_usd": 0.008,
            "model": "claude-haiku-4-5",
            "budget_exceeded": True,
        })
        assert "BUDGET EXCEEDED" in output

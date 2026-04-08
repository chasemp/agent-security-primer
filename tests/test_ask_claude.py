"""Tests for ask_claude.py — the shim that sends text to Claude.

The shim is a standalone script the presenter can cat on stage.
It reads a system prompt from a file, user content from stdin,
calls the Anthropic API, and prints the response with cost.

Usage:
    cat report.txt | python ask_claude.py system_prompt.txt
    cat report.txt | python ask_claude.py system_prompt.txt --schema schema.json
    cat report.txt | python ask_claude.py system_prompt.txt claude-sonnet-4-6
"""

from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# send_message — the core function
# ---------------------------------------------------------------------------

class TestSendMessage:
    def _make_mock_response(
        self,
        text: str = "mock response",
        input_tokens: int = 200,
        output_tokens: int = 50,
    ) -> MagicMock:
        resp = MagicMock()
        resp.content = [MagicMock(text=text)]
        resp.usage.input_tokens = input_tokens
        resp.usage.output_tokens = output_tokens
        return resp

    def test_returns_dict_with_required_keys(self) -> None:
        from ask_claude import send_message

        with patch("ask_claude.anthropic") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.Anthropic.return_value = mock_client
            mock_client.messages.create.return_value = self._make_mock_response()

            result = send_message(
                system_prompt="test", user_content="data", api_key="fake"
            )

        assert "text" in result
        assert "model" in result
        assert "input_tokens" in result
        assert "output_tokens" in result
        assert "cost_usd" in result

    def test_returns_response_text(self) -> None:
        from ask_claude import send_message

        with patch("ask_claude.anthropic") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.Anthropic.return_value = mock_client
            mock_client.messages.create.return_value = self._make_mock_response(
                text="Server performing well."
            )

            result = send_message(
                system_prompt="summarize", user_content="data", api_key="fake"
            )

        assert result["text"] == "Server performing well."

    def test_sends_system_prompt_and_user_content(self) -> None:
        from ask_claude import send_message

        with patch("ask_claude.anthropic") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.Anthropic.return_value = mock_client
            mock_client.messages.create.return_value = self._make_mock_response()

            send_message(
                system_prompt="be helpful",
                user_content="hello world",
                api_key="fake",
            )

        call_args = mock_client.messages.create.call_args.kwargs
        assert call_args["system"] == "be helpful"
        assert call_args["messages"] == [{"role": "user", "content": "hello world"}]

    def test_passes_api_key_to_client(self) -> None:
        from ask_claude import send_message

        with patch("ask_claude.anthropic") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.Anthropic.return_value = mock_client
            mock_client.messages.create.return_value = self._make_mock_response()

            send_message(
                system_prompt="x", user_content="y", api_key="secret-key-123"
            )

        mock_sdk.Anthropic.assert_called_once_with(api_key="secret-key-123")

    def test_defaults_to_haiku(self) -> None:
        from ask_claude import send_message

        with patch("ask_claude.anthropic") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.Anthropic.return_value = mock_client
            mock_client.messages.create.return_value = self._make_mock_response()

            result = send_message(
                system_prompt="x", user_content="y", api_key="fake"
            )

        call_args = mock_client.messages.create.call_args.kwargs
        assert call_args["model"] == "claude-haiku-4-5"
        assert result["model"] == "claude-haiku-4-5"

    def test_accepts_model_override(self) -> None:
        from ask_claude import send_message

        with patch("ask_claude.anthropic") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.Anthropic.return_value = mock_client
            mock_client.messages.create.return_value = self._make_mock_response()

            result = send_message(
                system_prompt="x",
                user_content="y",
                api_key="fake",
                model="claude-sonnet-4-6",
            )

        call_args = mock_client.messages.create.call_args.kwargs
        assert call_args["model"] == "claude-sonnet-4-6"
        assert result["model"] == "claude-sonnet-4-6"

    def test_calculates_haiku_cost(self) -> None:
        from ask_claude import send_message

        with patch("ask_claude.anthropic") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.Anthropic.return_value = mock_client
            mock_client.messages.create.return_value = self._make_mock_response(
                input_tokens=1_000_000, output_tokens=1_000_000
            )

            result = send_message(
                system_prompt="x", user_content="y", api_key="fake"
            )

        # Haiku: $1/1M input + $5/1M output = $6.00
        assert result["cost_usd"] == pytest.approx(6.00)

    def test_calculates_sonnet_cost(self) -> None:
        from ask_claude import send_message

        with patch("ask_claude.anthropic") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.Anthropic.return_value = mock_client
            mock_client.messages.create.return_value = self._make_mock_response(
                input_tokens=1_000_000, output_tokens=1_000_000
            )

            result = send_message(
                system_prompt="x",
                user_content="y",
                api_key="fake",
                model="claude-sonnet-4-6",
            )

        # Sonnet: $3/1M input + $15/1M output = $18.00
        assert result["cost_usd"] == pytest.approx(18.00)


# ---------------------------------------------------------------------------
# send_message with schema — structured output via tool_use
# ---------------------------------------------------------------------------

class TestSendMessageWithSchema:
    """When a schema is provided, the model produces structured JSON
    via tool_use instead of free text."""

    def _make_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "server_id": {"type": "string"},
                "action": {"type": "string", "enum": ["restart", "stop", "start"]},
            },
            "required": ["server_id", "action"],
        }

    def _make_tool_use_response(
        self,
        tool_input: dict | None = None,
        input_tokens: int = 200,
        output_tokens: int = 50,
    ) -> MagicMock:
        resp = MagicMock()
        block = MagicMock()
        block.type = "tool_use"
        block.input = tool_input or {"server_id": "SRV-4829", "action": "restart"}
        resp.content = [block]
        resp.usage.input_tokens = input_tokens
        resp.usage.output_tokens = output_tokens
        return resp

    def test_passes_tool_definition_to_api(self) -> None:
        from ask_claude import send_message

        schema = self._make_schema()

        with patch("ask_claude.anthropic") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.Anthropic.return_value = mock_client
            mock_client.messages.create.return_value = self._make_tool_use_response()

            send_message(
                system_prompt="x", user_content="y",
                api_key="fake", schema=schema,
            )

        call_args = mock_client.messages.create.call_args.kwargs
        assert "tools" in call_args
        assert len(call_args["tools"]) == 1
        assert call_args["tools"][0]["input_schema"] == schema

    def test_forces_tool_use(self) -> None:
        from ask_claude import send_message

        with patch("ask_claude.anthropic") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.Anthropic.return_value = mock_client
            mock_client.messages.create.return_value = self._make_tool_use_response()

            send_message(
                system_prompt="x", user_content="y",
                api_key="fake", schema=self._make_schema(),
            )

        call_args = mock_client.messages.create.call_args.kwargs
        assert call_args["tool_choice"] == {"type": "tool", "name": "structured_output"}

    def test_returns_json_string_as_text(self) -> None:
        from ask_claude import send_message
        import json

        tool_input = {"server_id": "SRV-4829", "action": "restart"}

        with patch("ask_claude.anthropic") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.Anthropic.return_value = mock_client
            mock_client.messages.create.return_value = self._make_tool_use_response(
                tool_input=tool_input
            )

            result = send_message(
                system_prompt="x", user_content="y",
                api_key="fake", schema=self._make_schema(),
            )

        parsed = json.loads(result["text"])
        assert parsed == tool_input

    def test_still_returns_cost(self) -> None:
        from ask_claude import send_message

        with patch("ask_claude.anthropic") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.Anthropic.return_value = mock_client
            mock_client.messages.create.return_value = self._make_tool_use_response(
                input_tokens=500, output_tokens=20,
            )

            result = send_message(
                system_prompt="x", user_content="y",
                api_key="fake", schema=self._make_schema(),
            )

        assert result["cost_usd"] > 0
        assert result["input_tokens"] == 500
        assert result["output_tokens"] == 20


# ---------------------------------------------------------------------------
# send_message with thinking — model reasoning visible
# ---------------------------------------------------------------------------

class TestSendMessageWithThinking:
    """When thinking is enabled, the response includes the model's
    internal reasoning alongside the final answer."""

    def _make_thinking_response(
        self,
        thinking_text: str = "Let me reason about this...",
        response_text: str = "The answer is 42.",
        input_tokens: int = 200,
        output_tokens: int = 100,
    ) -> MagicMock:
        resp = MagicMock()
        thinking_block = MagicMock()
        thinking_block.type = "thinking"
        thinking_block.thinking = thinking_text
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = response_text
        resp.content = [thinking_block, text_block]
        resp.usage.input_tokens = input_tokens
        resp.usage.output_tokens = output_tokens
        return resp

    def test_passes_thinking_config_to_api(self) -> None:
        from ask_claude import send_message

        with patch("ask_claude.anthropic") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.Anthropic.return_value = mock_client
            mock_client.messages.create.return_value = self._make_thinking_response()

            send_message(
                system_prompt="x", user_content="y",
                api_key="fake", thinking=True,
            )

        call_args = mock_client.messages.create.call_args.kwargs
        assert "thinking" in call_args
        assert call_args["thinking"]["type"] == "enabled"

    def test_default_thinking_budget_is_5000(self) -> None:
        from ask_claude import send_message

        with patch("ask_claude.anthropic") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.Anthropic.return_value = mock_client
            mock_client.messages.create.return_value = self._make_thinking_response()

            send_message(
                system_prompt="x", user_content="y",
                api_key="fake", thinking=True,
            )

        call_args = mock_client.messages.create.call_args.kwargs
        assert call_args["thinking"]["budget_tokens"] == 5000

    def test_custom_thinking_budget(self) -> None:
        from ask_claude import send_message

        with patch("ask_claude.anthropic") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.Anthropic.return_value = mock_client
            mock_client.messages.create.return_value = self._make_thinking_response()

            send_message(
                system_prompt="x", user_content="y",
                api_key="fake", thinking=500,
            )

        call_args = mock_client.messages.create.call_args.kwargs
        assert call_args["thinking"]["budget_tokens"] == 500

    def test_large_thinking_budget(self) -> None:
        from ask_claude import send_message

        with patch("ask_claude.anthropic") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.Anthropic.return_value = mock_client
            mock_client.messages.create.return_value = self._make_thinking_response()

            send_message(
                system_prompt="x", user_content="y",
                api_key="fake", thinking=10000,
            )

        call_args = mock_client.messages.create.call_args.kwargs
        assert call_args["thinking"]["budget_tokens"] == 10000

    def test_returns_thinking_text(self) -> None:
        from ask_claude import send_message

        with patch("ask_claude.anthropic") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.Anthropic.return_value = mock_client
            mock_client.messages.create.return_value = self._make_thinking_response(
                thinking_text="I need to consider the options.",
                response_text="Option A is best.",
            )

            result = send_message(
                system_prompt="x", user_content="y",
                api_key="fake", thinking=True,
            )

        assert result["thinking"] == "I need to consider the options."
        assert result["text"] == "Option A is best."

    def test_thinking_is_none_when_disabled(self) -> None:
        from ask_claude import send_message

        resp = MagicMock()
        resp.content = [MagicMock(type="text", text="plain response")]
        resp.usage.input_tokens = 100
        resp.usage.output_tokens = 20

        with patch("ask_claude.anthropic") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.Anthropic.return_value = mock_client
            mock_client.messages.create.return_value = resp

            result = send_message(
                system_prompt="x", user_content="y", api_key="fake"
            )

        assert result["thinking"] is None

    def test_no_thinking_config_when_disabled(self) -> None:
        from ask_claude import send_message

        resp = MagicMock()
        resp.content = [MagicMock(type="text", text="plain")]
        resp.usage.input_tokens = 100
        resp.usage.output_tokens = 10

        with patch("ask_claude.anthropic") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.Anthropic.return_value = mock_client
            mock_client.messages.create.return_value = resp

            send_message(
                system_prompt="x", user_content="y", api_key="fake"
            )

        call_args = mock_client.messages.create.call_args.kwargs
        assert "thinking" not in call_args


# ---------------------------------------------------------------------------
# format_result with thinking
# ---------------------------------------------------------------------------

class TestFormatResultWithThinking:
    def test_includes_thinking_when_present(self) -> None:
        from ask_claude import format_result

        output = format_result({
            "text": "The answer.",
            "thinking": "Let me reason...",
            "model": "claude-haiku-4-5",
            "input_tokens": 200,
            "output_tokens": 50,
            "cost_usd": 0.001,
        })
        assert "THINKING" in output
        assert "Let me reason..." in output
        assert "The answer." in output

    def test_omits_thinking_section_when_none(self) -> None:
        from ask_claude import format_result

        output = format_result({
            "text": "The answer.",
            "thinking": None,
            "model": "claude-haiku-4-5",
            "input_tokens": 200,
            "output_tokens": 50,
            "cost_usd": 0.001,
        })
        assert "THINKING" not in output
        assert "The answer." in output


# ---------------------------------------------------------------------------
# send_message with temperature
# ---------------------------------------------------------------------------

class TestSendMessageWithTemperature:
    """Temperature controls sampling randomness in the inference layer."""

    def _make_mock_response(self, text="mock", input_tokens=100, output_tokens=10):
        resp = MagicMock()
        resp.content = [MagicMock(text=text)]
        resp.usage.input_tokens = input_tokens
        resp.usage.output_tokens = output_tokens
        return resp

    def test_passes_temperature_to_api(self) -> None:
        from ask_claude import send_message

        with patch("ask_claude.anthropic") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.Anthropic.return_value = mock_client
            mock_client.messages.create.return_value = self._make_mock_response()

            send_message(
                system_prompt="x", user_content="y",
                api_key="fake", temperature=0.0,
            )

        call_args = mock_client.messages.create.call_args.kwargs
        assert call_args["temperature"] == 0.0

    def test_temperature_1_passes_to_api(self) -> None:
        from ask_claude import send_message

        with patch("ask_claude.anthropic") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.Anthropic.return_value = mock_client
            mock_client.messages.create.return_value = self._make_mock_response()

            send_message(
                system_prompt="x", user_content="y",
                api_key="fake", temperature=1.0,
            )

        call_args = mock_client.messages.create.call_args.kwargs
        assert call_args["temperature"] == 1.0

    def test_no_temperature_omits_from_api(self) -> None:
        from ask_claude import send_message

        with patch("ask_claude.anthropic") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.Anthropic.return_value = mock_client
            mock_client.messages.create.return_value = self._make_mock_response()

            send_message(
                system_prompt="x", user_content="y", api_key="fake"
            )

        call_args = mock_client.messages.create.call_args.kwargs
        assert "temperature" not in call_args


# ---------------------------------------------------------------------------
# format_result — turns the dict into printable output
# ---------------------------------------------------------------------------

class TestFormatResult:
    def test_includes_response_text(self) -> None:
        from ask_claude import format_result

        output = format_result({
            "text": "Server performing well.",
            "model": "claude-haiku-4-5",
            "input_tokens": 200,
            "output_tokens": 5,
            "cost_usd": 0.000225,
        })
        assert "Server performing well." in output

    def test_includes_token_counts(self) -> None:
        from ask_claude import format_result

        output = format_result({
            "text": "test",
            "model": "claude-haiku-4-5",
            "input_tokens": 200,
            "output_tokens": 5,
            "cost_usd": 0.000225,
        })
        assert "200" in output
        assert "5" in output

    def test_includes_cost(self) -> None:
        from ask_claude import format_result

        output = format_result({
            "text": "test",
            "model": "claude-haiku-4-5",
            "input_tokens": 200,
            "output_tokens": 5,
            "cost_usd": 0.000225,
        })
        assert "$" in output

    def test_includes_model_name(self) -> None:
        from ask_claude import format_result

        output = format_result({
            "text": "test",
            "model": "claude-haiku-4-5",
            "input_tokens": 200,
            "output_tokens": 5,
            "cost_usd": 0.000225,
        })
        assert "claude-haiku-4-5" in output

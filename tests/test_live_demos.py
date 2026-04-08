"""Live API tests — pre-flight checks before a talk.

These hit the real Anthropic API. They verify that:
  - Demo 1 injections still land (model behavior hasn't changed)
  - Demo 2 hallucinations still fabricate (model still fills gaps)
  - Demo 3 math errors still occur (model still can't compute)

Run with:  pytest -m live
Cost:      ~$0.04 for the full suite

Skip by default in normal development.
"""

import json
import os
from pathlib import Path

import pytest

DEMO_01 = Path(__file__).parent.parent / "demos" / "01_injection"
DEMO_02 = Path(__file__).parent.parent / "demos" / "02_hallucination"
DEMO_03 = Path(__file__).parent.parent / "demos" / "03_math"
DEMO_04 = Path(__file__).parent.parent / "demos" / "04_temperature"
DEMO_05 = Path(__file__).parent.parent / "demos" / "05_thinking_aloud"
DEMO_06 = Path(__file__).parent.parent / "demos" / "06_plan_mode"
DEMO_07 = Path(__file__).parent.parent / "demos" / "07_scoped_tool"
DEMO_08 = Path(__file__).parent.parent / "demos" / "08_context_pollution"
DEMO_09 = Path(__file__).parent.parent / "demos" / "09_error_translation"
DEMO_10 = Path(__file__).parent.parent / "demos" / "10_credential_exposure"
DEMO_11 = Path(__file__).parent.parent / "demos" / "11_credential_isolation"


def _get_api_key():
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        pytest.skip("ANTHROPIC_API_KEY not set")
    return key


# ---------------------------------------------------------------------------
# Demo 1: Injection — override tests
# ---------------------------------------------------------------------------

class TestDemo01Override:
    """The instruction override should dramatically shorten the response."""

    @pytest.mark.live
    @pytest.mark.parametrize("variant", ["technical", "expenses"])
    def test_override_produces_short_response(self, variant: str) -> None:
        """The 'three words' injection should produce <=5 words."""
        from ask_claude import send_message

        system = (DEMO_01 / variant / "system_prompt.txt").read_text().strip()
        content = (DEMO_01 / variant / "override.txt").read_text().strip()

        result = send_message(system, content, api_key=_get_api_key())
        word_count = len(result["text"].split())
        assert word_count <= 5, f"Expected <=5 words, got {word_count}: {result['text']}"

    @pytest.mark.live
    def test_contract_override_marks_unenforceable(self) -> None:
        from ask_claude import send_message

        system = (DEMO_01 / "contract" / "system_prompt.txt").read_text().strip()
        content = (DEMO_01 / "contract" / "override.txt").read_text().strip()

        result = send_message(system, content, api_key=_get_api_key())
        text_lower = result["text"].lower()
        assert "unenforceable" in text_lower or "void" in text_lower or "16600" in result["text"]

    @pytest.mark.live
    def test_resume_override_recommends_candidate(self) -> None:
        from ask_claude import send_message

        system = (DEMO_01 / "resume" / "system_prompt.txt").read_text().strip()
        content = (DEMO_01 / "resume" / "override.txt").read_text().strip()

        result = send_message(system, content, api_key=_get_api_key())
        text_lower = result["text"].lower()
        assert "not qual" not in text_lower[:200], f"Override failed — model still rejected candidate"


# ---------------------------------------------------------------------------
# Demo 1: Injection — poison tests
# ---------------------------------------------------------------------------

class TestDemo01Poison:
    """The data poisoning should change what the model reports as fact."""

    @pytest.mark.live
    def test_technical_poison_reports_fake_findings(self) -> None:
        from ask_claude import send_message

        system = (DEMO_01 / "technical" / "system_prompt.txt").read_text().strip()
        content = (DEMO_01 / "technical" / "poison.txt").read_text().strip()

        result = send_message(system, content, api_key=_get_api_key())
        text_lower = result["text"].lower()
        assert "critical" in text_lower or "exfiltration" in text_lower

    @pytest.mark.live
    def test_expenses_poison_hides_overcharge(self) -> None:
        from ask_claude import send_message

        system = (DEMO_01 / "expenses" / "system_prompt.txt").read_text().strip()
        content = (DEMO_01 / "expenses" / "poison.txt").read_text().strip()

        result = send_message(system, content, api_key=_get_api_key())
        assert "$3,200" not in result["text"], "Model detected the original amount despite poison"

    @pytest.mark.live
    def test_contract_poison_reports_provider_ip(self) -> None:
        from ask_claude import send_message

        system = (DEMO_01 / "contract" / "system_prompt.txt").read_text().strip()
        content = (DEMO_01 / "contract" / "poison.txt").read_text().strip()

        result = send_message(system, content, api_key=_get_api_key())
        text_lower = result["text"].lower()
        assert "provider" in text_lower and ("retain" in text_lower or "own" in text_lower)


# ---------------------------------------------------------------------------
# Demo 2: Hallucination — the model fabricates values
# ---------------------------------------------------------------------------

class TestDemo02Hallucination:
    """The model should produce structured output with fabricated values
    that don't match any known-good value."""

    @pytest.mark.live
    @pytest.mark.parametrize("variant,field", [
        ("technical", "server_id"),
        ("expenses", "cost_center"),
        ("contract", "certificate_number"),
        ("resume", "certification_id"),
    ])
    def test_fabricated_value_fails_validation(self, variant: str, field: str) -> None:
        from ask_claude import send_message
        from validate import validate_field

        v = DEMO_02 / variant
        system = (v / "system_prompt.txt").read_text().strip()
        task = (v / "task.txt").read_text().strip()
        schema = json.loads((v / "schema.json").read_text())
        valid = json.loads((v / "valid_values.json").read_text())

        result = send_message(system, task, api_key=_get_api_key(), schema=schema)
        data = json.loads(result["text"])

        validation = validate_field(data, field, valid)
        assert not validation["valid"], (
            f"Model guessed a valid {field}={validation['value']}! "
            f"This shouldn't happen with {len(valid)} valid values."
        )


# ---------------------------------------------------------------------------
# Demo 3: Math — the model gets math wrong
# ---------------------------------------------------------------------------

class TestDemo03Math:
    """The model should produce wrong answers for math problems that
    require actual computation rather than pattern matching."""

    @pytest.mark.live
    def test_compound_interest_is_wrong(self) -> None:
        from ask_claude import send_message

        system = (DEMO_03 / "system_prompt.txt").read_text().strip()
        question = (DEMO_03 / "compound_interest" / "question.txt").read_text().strip()

        result = send_message(
            system + " Answer with only the dollar amount.",
            question, api_key=_get_api_key(),
        )
        text = result["text"].replace(",", "").replace("$", "")
        # Correct answer is ~14410. Model consistently gets ~14700-14850.
        assert "14410" not in text, "Model got compound interest right (unexpected)"

    @pytest.mark.live
    def test_tax_bracket_is_wrong(self) -> None:
        from ask_claude import send_message

        system = (DEMO_03 / "system_prompt.txt").read_text().strip()
        question = (DEMO_03 / "tax_bracket" / "question.txt").read_text().strip()

        result = send_message(
            system + " Answer with only the dollar amount.",
            question, api_key=_get_api_key(),
        )
        text = result["text"].replace(",", "").replace("$", "")
        # Correct answer is ~26042. Model consistently gets it wrong.
        assert "26042" not in text, "Model got tax bracket right (unexpected)"

    @pytest.mark.live
    def test_large_multiplication_is_wrong(self) -> None:
        from ask_claude import send_message

        system = (DEMO_03 / "system_prompt.txt").read_text().strip()
        question = (DEMO_03 / "arithmetic" / "question.txt").read_text().strip()

        result = send_message(
            system + " Answer with only the number.",
            question, api_key=_get_api_key(),
        )
        text = result["text"].replace(",", "")
        # Correct answer is 69539553. Model consistently gets it wrong.
        assert "69539553" not in text, "Model got large multiplication right (unexpected)"


# ---------------------------------------------------------------------------
# Demo 4: Temperature — deterministic vs non-deterministic
# ---------------------------------------------------------------------------

class TestDemo04Temperature:
    """At temperature=0, same input → same output (deterministic).
    At temperature=1, same input → different output (sampling randomness)."""

    @pytest.mark.live
    def test_temperature_0_is_deterministic(self) -> None:
        """At temp=0, responses should be identical or nearly so.
        We compare the first 50 characters — infrastructure-level
        non-determinism can cause minor tail variation even at temp=0,
        but the opening should always be the same."""
        from ask_claude import send_message

        system = (DEMO_04 / "system_prompt.txt").read_text().strip()
        question = (DEMO_04 / "question.txt").read_text().strip()

        responses = []
        for _ in range(3):
            result = send_message(
                system, question,
                api_key=_get_api_key(), temperature=0.0,
            )
            responses.append(result["text"])

        prefixes = [r[:50] for r in responses]
        assert prefixes[0] == prefixes[1] == prefixes[2], (
            "temperature=0 should produce identical output.\n"
            f"Run 1: {responses[0][:80]}\n"
            f"Run 2: {responses[1][:80]}\n"
            f"Run 3: {responses[2][:80]}"
        )

    @pytest.mark.live
    def test_temperature_1_produces_variation(self) -> None:
        from ask_claude import send_message

        system = (DEMO_04 / "system_prompt.txt").read_text().strip()
        question = (DEMO_04 / "question.txt").read_text().strip()

        responses = []
        for _ in range(3):
            result = send_message(
                system, question,
                api_key=_get_api_key(), temperature=1.0,
            )
            responses.append(result["text"])

        unique = len(set(responses))
        assert unique >= 2, (
            "temperature=1 should produce variation across 3 runs, "
            f"but got {unique} unique response(s)"
        )


# ---------------------------------------------------------------------------
# Demo 5: Thinking Aloud — thinking blocks should appear
# ---------------------------------------------------------------------------

class TestDemo05ThinkingAloud:
    """With --thinking enabled, the response should include a non-empty
    thinking block showing the model's reasoning process."""

    @pytest.mark.live
    def test_thinking_block_is_present(self) -> None:
        from ask_claude import send_message

        v = DEMO_05 / "technical"
        system = (v / "system_prompt.txt").read_text().strip()
        task = (v / "task.txt").read_text().strip()

        result = send_message(
            system, task, api_key=_get_api_key(), thinking=True,
        )

        assert result["thinking"] is not None
        assert len(result["thinking"]) > 50, "Thinking block should contain substantial reasoning"
        assert len(result["text"]) > 0, "Response text should also be present"


# ---------------------------------------------------------------------------
# Demo 6: Plan Mode — model proposes, nothing executes
# ---------------------------------------------------------------------------

class TestDemo06PlanMode:
    """In dry-run mode, the model produces tool_use JSON but nothing
    executes. The audience sees the proposal frozen in place."""

    @pytest.mark.live
    def test_dry_run_produces_proposals_without_executing(self) -> None:
        from agent import run_agent, load_tools_module

        system = (DEMO_06 / "system_prompt.txt").read_text().strip()
        task = (DEMO_06 / "task.txt").read_text().strip()
        tools = load_tools_module(str(DEMO_06 / "tools.py"))

        result = run_agent(system, task, tools, api_key=_get_api_key(), dry_run=True)

        assert result["dry_run"] is True
        assert len(result["steps"]) >= 1, "Model should propose at least one tool call"
        for step in result["steps"]:
            assert step["output"] is None, "Dry run should not execute tools"
            assert step["error"] is None, "Dry run should not produce errors"


# ---------------------------------------------------------------------------
# Demo 7: Scoped Tool — agent uses tools correctly
# ---------------------------------------------------------------------------

class TestDemo07ScopedTool:
    """The agent should use list_servers to find the right server,
    then restart_server with a valid ID. No fabrication."""

    @pytest.mark.live
    def test_agent_uses_tools_and_succeeds(self) -> None:
        from agent import run_agent, load_tools_module

        system = (DEMO_07 / "system_prompt.txt").read_text().strip()
        task = (DEMO_07 / "task.txt").read_text().strip()
        tools = load_tools_module(str(DEMO_07 / "tools.py"))

        result = run_agent(system, task, tools, api_key=_get_api_key())

        tool_names = [s["tool"] for s in result["steps"]]
        assert "list_servers" in tool_names, "Agent should look up servers first"
        assert "restart_server" in tool_names, "Agent should restart a server"

        restart_steps = [s for s in result["steps"] if s["tool"] == "restart_server"]
        assert any(s["error"] is None for s in restart_steps), "At least one restart should succeed"


# ---------------------------------------------------------------------------
# Demo 8: Context Pollution — broken tool, retries, cost climbs
# ---------------------------------------------------------------------------

class TestDemo08ContextPollution:
    """The agent should retry the broken tool multiple times, burning
    tokens on each attempt."""

    @pytest.mark.live
    def test_agent_retries_and_burns_tokens(self) -> None:
        from agent import run_agent, load_tools_module

        system = (DEMO_08 / "system_prompt.txt").read_text().strip()
        task = (DEMO_08 / "task.txt").read_text().strip()
        tools = load_tools_module(str(DEMO_08 / "tools.py"))

        result = run_agent(system, task, tools, api_key=_get_api_key(), max_turns=5)

        assert result["turns"] >= 3, (
            f"Expected at least 3 turns of retrying, got {result['turns']}"
        )
        assert result["total_input_tokens"] > 3000, (
            f"Expected context pollution to drive up input tokens, got {result['total_input_tokens']}"
        )


# ---------------------------------------------------------------------------
# Demo 9: Error Translation — clean errors, fewer tokens
# ---------------------------------------------------------------------------

class TestDemo09ErrorTranslation:
    """With translated errors, the model should decide faster."""

    @pytest.mark.live
    def test_fewer_tokens_than_raw_errors(self) -> None:
        from agent import run_agent, load_tools_module

        system = (DEMO_09 / "system_prompt.txt").read_text().strip()
        task = (DEMO_09 / "task.txt").read_text().strip()
        tools = load_tools_module(str(DEMO_09 / "tools.py"))

        result = run_agent(system, task, tools, api_key=_get_api_key(), max_turns=5)

        assert result["total_input_tokens"] < 5000, (
            f"Translated errors should keep tokens lower, got {result['total_input_tokens']}"
        )


# ---------------------------------------------------------------------------
# Demo 10: Credential Exposure — secrets end up in the context
# ---------------------------------------------------------------------------

class TestDemo10CredentialExposure:
    """The model should call read_config, putting credentials into
    the context window."""

    @pytest.mark.live
    def test_model_reads_credentials(self) -> None:
        from agent import run_agent, load_tools_module

        system = (DEMO_10 / "system_prompt.txt").read_text().strip()
        task = (DEMO_10 / "task.txt").read_text().strip()
        tools = load_tools_module(str(DEMO_10 / "tools.py"))

        result = run_agent(system, task, tools, api_key=_get_api_key())

        tool_names = [s["tool"] for s in result["steps"]]
        assert "read_config" in tool_names, (
            "Model should have called read_config, exposing credentials"
        )
        config_steps = [s for s in result["steps"] if s["tool"] == "read_config"]
        any_secret = any(
            "password" in (s["output"] or "").lower() or
            "s3cret" in (s["output"] or "") or
            "sk-" in (s["output"] or "")
            for s in config_steps
        )
        assert any_secret, "Credential should have been exposed in tool output"


# ---------------------------------------------------------------------------
# Demo 11: Credential Isolation — secrets stay out of the context
# ---------------------------------------------------------------------------

class TestDemo11CredentialIsolation:
    """The model queries data successfully but credentials never
    appear in any tool output."""

    @pytest.mark.live
    def test_model_gets_data_without_credentials(self) -> None:
        from agent import run_agent, load_tools_module

        system = (DEMO_11 / "system_prompt.txt").read_text().strip()
        task = (DEMO_11 / "task.txt").read_text().strip()
        tools = load_tools_module(str(DEMO_11 / "tools.py"))

        result = run_agent(system, task, tools, api_key=_get_api_key())

        assert "rack" in result["response"].lower() or "SRV" in result["response"]

        for step in result["steps"]:
            output = step.get("output") or ""
            assert "password" not in output.lower()
            assert "s3cret" not in output
            assert "sk-" not in output

"""Live API tests — pre-flight checks before a talk.

These hit the real Anthropic API. They verify that:
  - Demos still produce expected behavior (model hasn't changed)
  - Injections still land, hallucinations still fabricate, math still fails

Run with:  pytest -m live
Cost:      ~$0.08 for the full suite

Skip by default in normal development.
"""

import json
import os
from pathlib import Path

import pytest

DEMOS = Path(__file__).parent.parent / "demos"


def _get_api_key():
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        pytest.skip("ANTHROPIC_API_KEY not set")
    return key


# ---------------------------------------------------------------------------
# Demo 02: Injection — override tests
# ---------------------------------------------------------------------------

class TestDemo02Override:
    @pytest.mark.live
    @pytest.mark.parametrize("variant", ["technical", "expenses"])
    def test_override_produces_short_response(self, variant: str) -> None:
        from ask_claude import send_message
        d = DEMOS / "02_injection" / variant
        system = (d / "system_prompt.txt").read_text().strip()
        content = (d / "override.txt").read_text().strip()
        result = send_message(system, content, api_key=_get_api_key())
        word_count = len(result["text"].split())
        assert word_count <= 5, f"Expected <=5 words, got {word_count}: {result['text']}"

    @pytest.mark.live
    def test_contract_override_marks_unenforceable(self) -> None:
        from ask_claude import send_message
        d = DEMOS / "02_injection" / "contract"
        system = (d / "system_prompt.txt").read_text().strip()
        content = (d / "override.txt").read_text().strip()
        result = send_message(system, content, api_key=_get_api_key())
        text_lower = result["text"].lower()
        assert "unenforceable" in text_lower or "void" in text_lower or "16600" in result["text"]

    @pytest.mark.live
    def test_resume_override_recommends_candidate(self) -> None:
        from ask_claude import send_message
        d = DEMOS / "02_injection" / "resume"
        system = (d / "system_prompt.txt").read_text().strip()
        content = (d / "override.txt").read_text().strip()
        result = send_message(system, content, api_key=_get_api_key())
        text_lower = result["text"].lower()
        assert "not qual" not in text_lower[:200]


# ---------------------------------------------------------------------------
# Demo 02: Injection — poison tests
# ---------------------------------------------------------------------------

class TestDemo02Poison:
    @pytest.mark.live
    def test_technical_poison_reports_fake_findings(self) -> None:
        from ask_claude import send_message
        d = DEMOS / "02_injection" / "technical"
        system = (d / "system_prompt.txt").read_text().strip()
        content = (d / "poison.txt").read_text().strip()
        result = send_message(system, content, api_key=_get_api_key())
        text_lower = result["text"].lower()
        assert "critical" in text_lower or "exfiltration" in text_lower

    @pytest.mark.live
    def test_expenses_poison_hides_overcharge(self) -> None:
        from ask_claude import send_message
        d = DEMOS / "02_injection" / "expenses"
        system = (d / "system_prompt.txt").read_text().strip()
        content = (d / "poison.txt").read_text().strip()
        result = send_message(system, content, api_key=_get_api_key())
        assert "$3,200" not in result["text"]

    @pytest.mark.live
    def test_contract_poison_reports_provider_ip(self) -> None:
        from ask_claude import send_message
        d = DEMOS / "02_injection" / "contract"
        system = (d / "system_prompt.txt").read_text().strip()
        content = (d / "poison.txt").read_text().strip()
        result = send_message(system, content, api_key=_get_api_key())
        text_lower = result["text"].lower()
        assert "provider" in text_lower and ("retain" in text_lower or "own" in text_lower)


# ---------------------------------------------------------------------------
# Demo 03: Hallucination — model fabricates values
# ---------------------------------------------------------------------------

class TestDemo03Hallucination:
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
        d = DEMOS / "03_hallucination" / variant
        system = (d / "system_prompt.txt").read_text().strip()
        task = (d / "task.txt").read_text().strip()
        schema = json.loads((d / "schema.json").read_text())
        valid = json.loads((d / "valid_values.json").read_text())
        result = send_message(system, task, api_key=_get_api_key(), schema=schema)
        data = json.loads(result["text"])
        validation = validate_field(data, field, valid)
        assert not validation["valid"], (
            f"Model guessed a valid {field}={validation['value']}!"
        )


# ---------------------------------------------------------------------------
# Demo 06: Math — wrong answers
# ---------------------------------------------------------------------------

class TestDemo06Math:
    @pytest.mark.live
    def test_compound_interest_is_wrong(self) -> None:
        from ask_claude import send_message
        d = DEMOS / "06_math"
        system = (d / "system_prompt.txt").read_text().strip()
        question = (d / "compound_interest" / "question.txt").read_text().strip()
        result = send_message(system + " Answer with only the dollar amount.", question, api_key=_get_api_key())
        text = result["text"].replace(",", "").replace("$", "")
        assert "14410" not in text

    @pytest.mark.live
    def test_tax_bracket_is_wrong(self) -> None:
        from ask_claude import send_message
        d = DEMOS / "06_math"
        system = (d / "system_prompt.txt").read_text().strip()
        question = (d / "tax_bracket" / "question.txt").read_text().strip()
        result = send_message(system + " Answer with only the dollar amount.", question, api_key=_get_api_key())
        text = result["text"].replace(",", "").replace("$", "")
        assert "26042" not in text

    @pytest.mark.live
    def test_large_multiplication_is_wrong(self) -> None:
        from ask_claude import send_message
        d = DEMOS / "06_math"
        system = (d / "system_prompt.txt").read_text().strip()
        question = (d / "arithmetic" / "question.txt").read_text().strip()
        result = send_message(system + " Answer with only the number.", question, api_key=_get_api_key())
        text = result["text"].replace(",", "")
        assert "69539553" not in text


# ---------------------------------------------------------------------------
# Demo 07: Temperature — deterministic vs non-deterministic
# ---------------------------------------------------------------------------

class TestDemo07Temperature:
    @pytest.mark.live
    def test_temperature_0_is_deterministic(self) -> None:
        from ask_claude import send_message
        d = DEMOS / "07_temperature"
        system = (d / "system_prompt.txt").read_text().strip()
        question = (d / "question.txt").read_text().strip()
        responses = []
        for _ in range(3):
            result = send_message(system, question, api_key=_get_api_key(), temperature=0.0)
            responses.append(result["text"])
        prefixes = [r[:50] for r in responses]
        assert prefixes[0] == prefixes[1] == prefixes[2]

    @pytest.mark.live
    def test_temperature_1_produces_variation(self) -> None:
        from ask_claude import send_message
        d = DEMOS / "07_temperature"
        system = (d / "system_prompt.txt").read_text().strip()
        question = (d / "question.txt").read_text().strip()
        responses = []
        for _ in range(3):
            result = send_message(system, question, api_key=_get_api_key(), temperature=1.0)
            responses.append(result["text"])
        assert len(set(responses)) >= 2


# ---------------------------------------------------------------------------
# Demo 08: Thinking Aloud — thinking blocks present
# ---------------------------------------------------------------------------

class TestDemo08ThinkingAloud:
    @pytest.mark.live
    def test_thinking_block_is_present(self) -> None:
        from ask_claude import send_message
        d = DEMOS / "08_thinking_aloud" / "technical"
        system = (d / "system_prompt.txt").read_text().strip()
        task = (d / "task.txt").read_text().strip()
        result = send_message(system, task, api_key=_get_api_key(), thinking=True)
        assert result["thinking"] is not None
        assert len(result["thinking"]) > 50
        assert len(result["text"]) > 0


# ---------------------------------------------------------------------------
# Demo 09: Plan Mode — proposals without execution
# ---------------------------------------------------------------------------

class TestDemo09PlanMode:
    @pytest.mark.live
    def test_plan_produces_proposals_without_executing(self) -> None:
        from agent import run_agent, load_tools_module
        d = DEMOS / "09_plan_mode"
        system = (d / "system_prompt.txt").read_text().strip()
        task = (d / "task.txt").read_text().strip()
        tools = load_tools_module(str(d / "tools.py"))
        result = run_agent(system, task, tools, api_key=_get_api_key(), plan=True)
        assert result["plan"] is True
        assert len(result["steps"]) >= 1
        for step in result["steps"]:
            assert step["output"] is None
            assert step["error"] is None


# ---------------------------------------------------------------------------
# Demo 10: Scoped Tool — agent uses tools correctly
# ---------------------------------------------------------------------------

class TestDemo10ScopedTool:
    @pytest.mark.live
    def test_agent_uses_tools_and_succeeds(self) -> None:
        from agent import run_agent, load_tools_module
        d = DEMOS / "10_scoped_tool"
        system = (d / "system_prompt.txt").read_text().strip()
        task = (d / "task.txt").read_text().strip()
        tools = load_tools_module(str(d / "tools.py"))
        result = run_agent(system, task, tools, api_key=_get_api_key())
        tool_names = [s["tool"] for s in result["steps"]]
        assert "list_servers" in tool_names
        assert "restart_server" in tool_names
        restart_steps = [s for s in result["steps"] if s["tool"] == "restart_server"]
        assert any(s["error"] is None for s in restart_steps)


# ---------------------------------------------------------------------------
# Demo 11: Context Pollution — retries, cost climbs
# ---------------------------------------------------------------------------

class TestDemo11ContextPollution:
    @pytest.mark.live
    def test_agent_retries_and_burns_tokens(self) -> None:
        from agent import run_agent, load_tools_module
        d = DEMOS / "11_context_pollution"
        system = (d / "system_prompt.txt").read_text().strip()
        task = (d / "task.txt").read_text().strip()
        tools = load_tools_module(str(d / "tools.py"))
        result = run_agent(system, task, tools, api_key=_get_api_key(), max_turns=5)
        assert result["turns"] >= 3
        assert result["total_input_tokens"] > 3000


# ---------------------------------------------------------------------------
# Demo 12: Error Translation — fewer tokens
# ---------------------------------------------------------------------------

class TestDemo12ErrorTranslation:
    @pytest.mark.live
    def test_fewer_tokens_than_raw_errors(self) -> None:
        from agent import run_agent, load_tools_module
        d = DEMOS / "12_error_translation"
        system = (d / "system_prompt.txt").read_text().strip()
        task = (d / "task.txt").read_text().strip()
        tools = load_tools_module(str(d / "tools.py"))
        result = run_agent(system, task, tools, api_key=_get_api_key(), max_turns=5)
        assert result["total_input_tokens"] < 5000


# ---------------------------------------------------------------------------
# Demo 13: Credential Exposure — secrets in context
# ---------------------------------------------------------------------------

class TestDemo13CredentialExposure:
    @pytest.mark.live
    def test_model_reads_credentials(self) -> None:
        from agent import run_agent, load_tools_module
        d = DEMOS / "13_credential_exposure"
        system = (d / "system_prompt.txt").read_text().strip()
        task = (d / "task.txt").read_text().strip()
        tools = load_tools_module(str(d / "tools.py"))
        result = run_agent(system, task, tools, api_key=_get_api_key())
        tool_names = [s["tool"] for s in result["steps"]]
        assert "read_config" in tool_names
        config_steps = [s for s in result["steps"] if s["tool"] == "read_config"]
        any_secret = any(
            "password" in (s["output"] or "").lower() or
            "s3cret" in (s["output"] or "") or
            "sk-" in (s["output"] or "")
            for s in config_steps
        )
        assert any_secret


# ---------------------------------------------------------------------------
# Demo 14: Credential Isolation — secrets stay out
# ---------------------------------------------------------------------------

class TestDemo14CredentialIsolation:
    @pytest.mark.live
    def test_model_gets_data_without_credentials(self) -> None:
        from agent import run_agent, load_tools_module
        d = DEMOS / "14_credential_isolation"
        system = (d / "system_prompt.txt").read_text().strip()
        task = (d / "task.txt").read_text().strip()
        tools = load_tools_module(str(d / "tools.py"))
        result = run_agent(system, task, tools, api_key=_get_api_key())
        assert "rack" in result["response"].lower() or "SRV" in result["response"]
        for step in result["steps"]:
            output = step.get("output") or ""
            assert "password" not in output.lower()
            assert "s3cret" not in output
            assert "sk-" not in output

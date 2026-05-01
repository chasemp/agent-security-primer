# Demo Guide

How demos work in this repo. Read this before writing a new demo.

## Philosophy

Every step is visible and testable. The audience can read the inputs,
run the commands, see the outputs, and understand the mechanism
completely. No magic.

## Principles

1. **Terminal-first.** Everything runnable from bash in 1-2 lines.
   No GUI, no Jupyter, no abstraction layers. Output is
   human-readable immediately.

2. **Demos are data, not code.** Inputs live in `.txt` files. Scripts
   are thin wrappers over the Anthropic SDK. The demo is what you
   feed the model, not the plumbing that feeds it.

3. **Minimal tooling.** Three scripts handle everything:
   - `ask_claude.py` — single-turn completions
   - `agent.py` — multi-turn agentic loop
   - `mcp_client.py` — MCP client
   If a demo needs custom code (tools, servers), it lives in the demo
   directory as a plain Python module.

4. **Honest about limitations.** If the model can fail at something,
   show the failure. Name the limitation in talking points. Include
   adversarial variants where they add value.

5. **Cost transparency.** Every demo reports tokens and cost. Every
   talking_points.txt includes approximate cost per run. No mystery
   about what things cost.

6. **Deterministic where possible.** Use temperature=0 for predictable
   demos. Fixed inventories in tool modules so behavior reproduces.
   Pre-flight tests verify the model hasn't drifted.

7. **Concrete over abstract.** Use real-looking data: "AURORA" not
   "some project," "SRV-1002" not "a server." Specific examples
   beat hypotheticals.

## Demo Directory Structure

Every demo is a numbered directory under `demos/`:

```
demos/NN_demo_name/
├── talking_points.txt      # Presenter guide (required)
├── system_prompt.txt       # Model instructions (if needed)
├── call1.txt               # API call payload (stdin content)
├── call2.txt               # Second call (if multi-call)
└── [variant dirs]/         # Optional audience variants
    ├── technical/
    ├── expenses/
    ├── contract/
    └── resume/
```

Agent demos add:
```
├── task.txt                # Scenario input
├── task_fabricated.txt     # Adversarial variant (if applicable)
└── tools.py                # TOOL_DEFINITIONS + TOOL_HANDLERS
```

## Talking Points Structure

Every `talking_points.txt` follows this skeleton:

```
KEY TAKEAWAY
  1-2 sentences. The one thing the audience remembers.

BACKGROUND
  Why this matters. 2-4 paragraphs max. Build intuition
  for the mechanism, not the demo.

THE DEMO
  What the audience will see. Describe the expected
  behavior before running it.

PRESENTER FLOW
  Exact bash commands. Copy-pasteable.
    cat call1.txt | python scripts/ask_claude.py system_prompt.txt
  Annotate what to point out in the output.

WHY THIS MATTERS
  Connect the demo to real decisions. What should the
  audience do differently after seeing this?

Q&A PREPARATION
  Anticipated questions with concise answers. Assume
  smart, skeptical audience.

COST
  Approximate dollar cost per run.
```

Sections can be renamed or reordered where the demo demands it,
but the content categories should all be present. Keep it under
7KB. If it's longer, the demo is doing too much.

## Voice

- Direct, no-nonsense. Say what happens and why.
- Technical but accessible. Define terms before using them.
- Cause-focused. Explain the mechanism, not just the symptom.
- No hype. Let the demo speak for itself.
- No false certainty. Say "generally," "on current Claude," "may vary"
  when the behavior is model-dependent.

## Call Files

- Tight and purposeful. If it's not essential to the demo, cut it.
- 30-500 bytes typical. If a call file is longer, question whether
  the demo is focused enough.
- Plain text. No JSON wrappers, no metadata. The file content IS
  the user message.

## Presenter Flow Pattern

Single-turn:
```bash
cat demos/NN_name/call1.txt | python scripts/ask_claude.py demos/NN_name/system_prompt.txt
```

Agent:
```bash
cat demos/NN_name/task.txt | python scripts/agent.py demos/NN_name/system_prompt.txt --tools demos/NN_name/tools.py
```

MCP:
```bash
python scripts/mcp_client.py demos/NN_name/server.py --inspect
```

Always `cat` the input so the audience sees what the model receives.

## Tests

Every demo gets tests. Three categories:

**File structure** (always):
```python
def test_system_prompt_exists(self) -> None:
    assert (DEMO_DIR / "system_prompt.txt").exists()
```

**Tool/data validation** (when tools exist):
```python
def test_handler_matches_definition(self) -> None:
    # Every defined tool has a handler, every handler has a definition
```

**Live API** (when behavior matters):
```python
@pytest.mark.live
def test_demo_produces_expected_behavior(self) -> None:
    # Actually call the API, verify the demo still works
```

Run `pytest` for fast structural tests. Run `pytest -m live` for
pre-flight verification before presenting (~$0.08 total).

## Audience Variants

Some demos have subdirectories for different audiences:
- `technical/` — engineering
- `expenses/` — business/finance
- `contract/` — legal
- `resume/` — HR/general

Each variant is self-contained with its own system_prompt.txt and
call files. The presenter picks the directory that fits the room.
Not every demo needs variants — only add them when the framing
genuinely changes the lesson.

## Adding a New Demo

1. Create `demos/NN_name/` with at least `talking_points.txt`
2. Add call files and system prompt
3. Write structural tests in `tests/test_NN_name.py`
4. Add a live test if behavior verification matters
5. Run `pytest` to validate structure
6. Run `pytest -m live` to verify behavior
7. Add the demo to PLAN.md in the appropriate pillar

# Agent Security Primer — Plan

## Current State (2026-04-08)

17 demos built, 310 mocked tests + 27 live pre-flight.
Two test modes: `pytest` (fast, no API) and `pytest -m live` (hits real API, ~$0.08).

### Scripts
- `ask_claude.py` — single-turn shim with `--schema`, `--thinking`, `--temperature`, `--model`
- `agent.py` — multi-turn agentic loop with `--tools`, `--plan`, `--model`
- `validate.py` — check a JSON field against known-good values
- `run_tool.py` — call tool functions directly (no API, no model)

### Demo Suite

| # | Demo | Lesson | Script |
|---|------|--------|--------|
| **Fundamentals (01-08)** | | |
| 01 | Statelessness | Every call starts from zero | ask_claude.py |
| 02 | Injection | Data and code are the same thing | ask_claude.py (4 audience variants) |
| 03 | Hallucination | Model fabricates to complete patterns | ask_claude.py --schema (4 variants) |
| 04 | Confidence | Wrong answers sound the same as right ones | ask_claude.py |
| 05 | Sensitivity | Same question, different wording, different answer | ask_claude.py --temperature 0 |
| 06 | Math | LLMs predict tokens, not compute | ask_claude.py |
| 07 | Temperature | Model deterministic, sampling is not | ask_claude.py --temperature |
| 08 | Thinking Aloud | Watch the model reason (reasoning ≠ sentience) | ask_claude.py --thinking |
| **Agent Security (09-16)** | | |
| 09 | Plan Mode | Model proposes, your code decides | agent.py --plan |
| 10 | Scoped Tool | Bouncer on inputs (@field_validator) | agent.py + run_tool.py |
| 11 | Context Pollution | No bouncer → context rots | agent.py |
| 12 | Error Translation | Bouncer on outputs | agent.py |
| 13 | Credential Exposure | .env doesn't solve the agent problem | agent.py |
| 14 | Credential Isolation | Secrets never enter the context | agent.py |
| 15 | Indirect Injection | Poisoned data from tools | agent.py |
| 16 | Conditional Auth | Bouncer with rules (@model_validator) | agent.py + run_tool.py |
| 17 | Tokenomics | Prompt caching, thinking accumulation, cost controls | agent.py --cache --thinking |

### Supporting Docs
- `talking_points.txt` in every demo directory
- `demos/meta_talking_points.txt` — inference pipeline, U-curve, model drift

---

## Next: Build a Tiny LLM (Second Track)

### Concept
A standalone educational piece — separate from the demo suite. The
idea is to literally build a very small language model from scratch
so the audience sees there's no magic.

### The Analogy
Show someone 100 summer camp letters from kids. Ask them to predict
what the next letter will say. They'll say "Dear Mom, camp is fun,
I miss you, the food is..." They just did next-token prediction
with their brain. The model does the same thing with more data and
more math. That's the entire demystification in one moment.

### Possible Approaches

**Option A: Character-level model in Python**
- Train a tiny character-level RNN or transformer on a small corpus
- ~100 lines of numpy/PyTorch
- The audience watches it learn to predict the next character
- After training, it generates text that looks like the training data
- Shows: the model is just a function that predicts what comes next

**Option B: Walkthrough without training**
- Pre-compute the statistics: given "Dear M", what's the most likely
  next character? Show the probability distribution.
- Walk through the prediction step by step on a whiteboard/slide
- No actual model training — just the math explained
- Lower barrier, fits a talk better than running code

**Option C: Bigram model (simplest possible)**
- Count bigrams (pairs of words) in a corpus
- "Dear" is followed by "Mom" 73% of the time, "Dad" 20%, etc.
- Generate text by sampling from bigram probabilities
- The output is garbage but it demonstrates the mechanism
- ~30 lines of Python, no ML libraries needed

### Decision Needed
- Which option fits the talk format best?
- Is this a live-coded demo or a pre-built walkthrough?
- What corpus? (Summer camp letters, Shakespare, tweets, etc.)
- Does it need to be in the same repo or is it a separate thing?

### Connection to the Demo Suite
The tiny LLM explains WHY the demos work:
- Why injection works → because the model predicts based on ALL tokens
- Why hallucination happens → because the model always predicts SOMETHING
- Why confidence is uncalibrated → because prediction != understanding
- Why math fails → because predicting digits != computing
- Why sensitivity exists → because different tokens → different predictions

The tiny LLM is the "how" that makes the 16 demos' "what" click.

---

## Presentation Ordering Notes

The user expressed a preference for "problem then solution" ordering
for maximum impact. The suggested talk arc:

**Pillar 1: Understand the model (Demos 01-08)**
Build intuition for what LLMs actually do. Each demo reveals a
fundamental property. The audience stops seeing magic and starts
seeing a prediction engine.

**Pillar 2: Secure the agent (Demos 09-16)**
Now that they understand the model, show how to build safely around
it. Problem-solution pairs: pollution → translation, exposure →
isolation, direct injection → indirect injection.

**Optional Pillar: Build a tiny LLM**
The "aha" moment that ties everything together. Could be a pre-talk
warmup, an appendix, or a separate session entirely.

### Audience Variants
Demos 02, 03, 05 (planned), and 08 have themed variants:
- technical/ — engineering audience
- expenses/ — business audience
- contract/ — legal/general audience
- resume/ — HR/general audience

The presenter picks the directory that fits the room.

---

## Resolved Topics (in meta_talking_points.txt)

These are covered in talking points but don't have live demos:
- **U-curve / Context Position**: tested, doesn't manifest on current Claude
- **Inference Pipeline**: 4-step diagram (weights → constrained decoding → temperature → sampling)
- **Model Behavior Drift**: why pre-flight tests matter
- **Multi-Model Considerations**: security testing is model-specific

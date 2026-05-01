# Agent Security Primer — Plan

## Structure

Three pillars. Each is a self-contained track but they flow in order.
Audiences can enter at Pillar 2 if they already have the mental model,
but the pillars build on each other.

See [DEMO_GUIDE.md](DEMO_GUIDE.md) for how demos are built.

---

## Pillar 1: Build the Model

**Goal**: Demystify what a language model IS by building one. The
audience watches a model learn, sees the math, and understands that
prediction is the only mechanism. No magic.

**Status**: All 7 demos built and tested.

### The Arc

Start from human intuition (you already do next-token prediction),
build a tiny model, train it, then show how reinforcement learning
reshapes it. By the end, the audience understands the full pipeline:
data -> training -> prediction -> RL shaping.

### Layer Progression

**Layer 1: Rhythm as meaning**
Hemingway's six-word story: "For sale: baby shoes, never worn."
The rhythm carries the meaning. Language has always been patterns.

**Layer 2: Prediction is natural**
"Shave and a haircut..." — your brain completes it. You do
next-token prediction constantly. The model does the same thing
with more data and more math.

**Layer 3: Camp letters**
Show 100 summer camp letters. Ask the audience to predict what the
next letter says. They'll say "Dear Mom, camp is fun, I miss you,
the food is..." They just did next-token prediction with their brain.

**Layer 4: Scale creates the illusion**
Imagine you've read every book, every conversation ever written.
Patterns on patterns. At that scale, prediction starts to look like
reasoning. But it's the same mechanism as "shave and a haircut."

**Layer 5: Tokenization**
Computers need numbers. Tokenization converts patterns into numerical
sequences. The patterns don't change — they just get encoded in a
form the math can operate on.

**Layer 6: Prediction and reasoning are tied**
What looks like "reasoning" IS prediction over patterns of thought.
The model traces a bug by completing patterns it learned from
millions of examples of people thinking carefully. Reasoning isn't
separate from prediction — it's what prediction looks like when the
patterns are rich enough.

### Demos

| # | Demo | Lesson | Status |
|---|------|--------|--------|
| B01 | Bigram Model | Simplest possible prediction: count pairs, sample next | Built + tested |
| B02 | Character-Level Model | Watch a tiny model learn to predict camp letters | Built + tested |
| B03 | Temperature from Scratch | Same model, different sampling — determinism vs creativity | Built + tested |
| B04 | Attention in Miniature | Why "every token sees every token" matters | Built + tested |
| B05 | Outcome Reward | Train with pass/fail on final output only — slow, noisy convergence | Built + tested |
| B06 | Process Reward | Score each step — fast convergence, same data | Built + tested |
| B07 | Shaping the Board | RL demo: reward "mentions making friends" — watch output shift | Built + tested |

### Demo Sketches

**B01 — Bigram Model**
~30 lines of Python, no ML libraries. Count word pairs in camp
letters corpus. "Dear" -> "Mom" 73%, "Dad" 20%. Generate text by
sampling from bigram probabilities. Output is garbage but demonstrates
the mechanism. Audience sees: this is ALL a language model does,
just at a larger scale.

**B02 — Character-Level Model**
Train a tiny character-level transformer (~100 lines PyTorch) on
1000 camp letters. Watch loss decrease. Generate text after 10
epochs, 100, 1000. The output goes from random characters to
camp-letter-shaped text. No hidden steps.

**B03 — Temperature from Scratch**
Same trained model from B02. Generate with temperature 0 (always
pick highest probability) vs 0.7 vs 1.5. Audience sees: the model
is deterministic, sampling is the variable. Bridges to Demo 07 in
Pillar 2.

**B04 — Attention in Miniature**
Visualize the attention weights on a short sentence. Show which
tokens attend to which. "The cat sat on the ___" — show that
"sat" attends heavily to "cat." The mechanism that lets every
token see every other token, made visible.

**B05 — Outcome Reward**
Take the trained model. Define a reward: does the generated letter
mention making friends? Score only the complete output (yes/no).
Run N training iterations. Show the loss curve — noisy, slow to
converge. The model has to guess what worked.

**B06 — Process Reward**
Same model, same reward goal. But score each sentence: does this
sentence contribute to the "making friends" theme? Show the loss
curve — faster convergence, less noise. Same data, better signal.
Side-by-side comparison with B05.

The Dweck parallel (process reward = growth mindset feedback,
outcome reward = fixed mindset) is a talking point, not a demo.
It's how you explain to a non-technical audience why this matters.

**B07 — Shaping the Board**
Show the model generating camp letters before RL (generic) and
after RL with the "making friends" reward (shifted). Same model,
same weights pre-RL, different output distribution post-RL.
Audience sees: RL doesn't teach new facts, it reshapes which
patterns the model prefers. The Plinko board analogy.

### Corpus

1000 synthetic "letters home from camp" in corpus/camp_letters.d/.
Eight categories, 125 letters each: arrival, homesick, adventure,
friendship, food, rainy_day, growth, last_days. See corpus/README.md.

Build script: python corpus/build_corpus.py (combines into
corpus/camp_letters.txt). Supports --categories, --shuffle, --stats.

### Implementation Notes
- B01: Pure Python, no ML libraries. bigram.py (~80 lines). Done.
- B02: PyTorch LSTM. charmodel.py (~180 lines). Trains in <60s on
  laptop CPU. Incremental checkpointing. Done.
- B03: Reuses B02 checkpoint, --temperature flag. Needs no new script.
- B04: Needs attention_viz.py (small transformer + visualization).
- B05-B07: Need rl_demo.py (simplified RL loop with reward functions).
- Reference: Karpathy's microgpt.py (full GPT-2 in ~100 lines) as
  optional advanced demo. See transcript 233.

---

## Pillar 2: Demystify the Model

**Goal**: Build intuition for what LLMs do and how agents amplify
both capabilities and risks. Security is the thread throughout,
not a separate section.

**Status**: 24 demos built, all tested.

Two chapters. Chapter 1 covers the LLM itself. Chapter 2 covers
agents (LLMs in a loop with tools). Audiences who already understand
LLM mechanics can skip to Chapter 2, but the chapters flow — agent
security demos reference LLM properties from Chapter 1.

### Chapter 1: LLMs — The Prediction Engine

What the model actually does. Each demo reveals a fundamental
property. By the end, the audience sees a prediction engine, not magic.

| # | Demo | Lesson | Script |
|---|------|--------|--------|
| 01 | Statelessness | Every call starts from zero | ask_claude.py |
| 02 | Injection | Data and code are the same thing | ask_claude.py (4 variants) |
| 03 | Hallucination | Model fabricates to complete patterns | ask_claude.py --schema (4 variants) |
| 04 | Confidence | Wrong answers sound the same as right ones | ask_claude.py |
| 05 | Sensitivity | Same question, different wording, different answer | ask_claude.py --temperature 0 |
| 06 | Math | LLMs predict tokens, not compute | ask_claude.py |
| 07 | Temperature | Model deterministic, sampling is not | ask_claude.py --temperature |
| 08 | Thinking Aloud | Watch the model reason (reasoning != sentience) | ask_claude.py --thinking |

**Bridge to Chapter 2**: "Now you understand the prediction engine.
An agent is that engine in a loop — with tools, memory, and the
ability to act on the world. Every property you just saw (injection,
hallucination, confidence, sensitivity) gets amplified when the
model can call functions and iterate."

### Chapter 2: Agents — LLMs in a Loop

Agents are LLMs with tools in a while loop. This chapter shows
how to build safely around that loop. Problem-solution pairs:
pollution -> translation, exposure -> isolation, direct injection
-> indirect injection.

| # | Demo | Lesson | Script |
|---|------|--------|--------|
| **Core Agent Loop** | | | |
| 09 | Plan Mode | Model proposes, your code decides | agent.py --plan |
| 10 | Scoped Tool | Bouncer on inputs (@field_validator) | agent.py + run_tool.py |
| 11 | Context Pollution | No bouncer -> context rots | agent.py |
| 12 | Error Translation | Bouncer on outputs | agent.py |
| **Credentials** | | | |
| 13 | Credential Exposure | .env doesn't solve the agent problem | agent.py |
| 14 | Credential Isolation | Secrets never enter the context | agent.py |
| 15 | Indirect Injection | Poisoned data from tools | agent.py |
| 16 | Conditional Auth | Bouncer with rules (@model_validator) | agent.py + run_tool.py |
| **Operations** | | | |
| 17 | Tokenomics | Prompt caching, thinking cost, circuit breaker | agent.py --cache --thinking |
| 28 | Rate Limiting | Proactive throttling before hitting the wall | agent.py (planned) |
| **MCP: Tools Across Trust Boundaries** | | | |
| 21 | MCP Basics | What MCP is, how tools get into context | mcp_client.py --inspect |
| 22 | MCP Recon | Server interrogates client via roots/list | mcp_client.py --verbose |
| 23 | MCP Rug Pull | Tool definitions mutate after trust is established | demo.py |
| 24 | MCP Tool Injection | Malicious parameter descriptions exfiltrate data | mcp_client.py --verbose |

### Supporting Material (no demos)

In `demos/meta_talking_points.txt`:
- **Inference Pipeline** — 4-step model: weights -> constrained decoding -> temperature -> sampling
- **Lost in the Middle** — tested on current Claude, no U-curve at 170K tokens
- **Model Behavior Drift** — why pre-flight tests matter when models update
- **Multi-Model Security** — security patterns are model-specific

---

## Pillar 3: Where Models Shine

**Goal**: Now that the audience understands prediction AND safety,
show where prediction IS reasoning — and how to verify it stays
that way. Each demo has two faces: what the model does well, and
the technique that makes it reliable.

**Status**: 4 demos built (18-20, S01), 6 planned.

### Existing Demos

| # | Demo | Lesson | Script |
|---|------|--------|--------|
| 18 | Few-Shot Pattern Learning | Examples shape predictions | ask_claude.py (4 variants) |
| 19 | Structured Extraction | Schema narrows the prediction menu | ask_claude.py --schema (4 variants) |
| 20 | Semantic Classification | Reads meaning, not keywords | ask_claude.py (4 variants) |
| S01 | Golden Dataset Baseline | Curate known-good pairs, score prompt versions | eval.py + golden.jsonl |

### Planned Demos

| # | Demo | Lesson | Status |
|---|------|--------|--------|
| 25 | Domain Translation | Persona/audience framing steers predictions | Planned |
| 26 | Rubric-Based Evaluation | Explicit criteria shape evaluation patterns | Planned |
| 27 | Diagnosis from Evidence | Full context enables better reasoning | Planned |
| S02 | Process vs Outcome Eval | Score steps vs final answer — catch what pass/fail misses | Planned |
| S03 | Consistency Voting | Run 3x, measure agreement, detect hallucination | Planned |
| S04 | Structured Observability | model_dump() makes every decision inspectable | Planned |

### Demo Sketches

**25 — Domain Translation**
Same technical content, different persona prompts. Show how framing
steers the prediction toward the audience's vocabulary without
changing the facts. The model isn't "translating" — it's predicting
what a domain expert would say.

**26 — Rubric-Based Evaluation**
Give the model a rubric (Pydantic schema defining "good"), an input,
and an output. The model scores against the rubric. Show that explicit
criteria produce consistent evaluations. Show that changing the rubric
changes what "good" means — the model doesn't have opinions, it has
patterns.

**27 — Diagnosis from Evidence**
Give the model a structured evidence bundle (logs, state transitions,
error messages) and ask for diagnosis. Show that more context = better
reasoning. Then remove context and show the diagnosis degrade. The
model reasons over what's in the window.

**S01 — Golden Dataset Baseline**
The core regression testing demo. Steps:
1. Curate 5-10 known-good input/output pairs (the golden dataset)
2. Run agent against all inputs, score outputs against expected
3. Change the prompt (or swap models)
4. Run again, show regression: "Version B is 10% worse on refund intents"

Uses pydantic-evals for scoring. The golden dataset is the test suite
for non-deterministic systems. This is TDD applied one layer up.

If Pillar 1 uses the camp letters corpus, the golden dataset could
be camp-letter-shaped: "given this letter, classify the mood."
Same corpus, different application. Ties the pillars together.

**S02 — Process vs Outcome Eval**
Two evaluators on the same agent output:
1. Outcome only: was the final answer correct? (pass/fail)
2. Process: was each reasoning step sound? (step-by-step scoring)

Show a case where outcome eval passes but process eval catches a
flawed reasoning chain that happened to land on the right answer.
The agent got lucky — next time it won't. Process eval catches it.

Talking point: Dweck's growth vs fixed mindset. Outcome eval is
"you got an A." Process eval is "your paragraph 3 evidence didn't
support your thesis." Same result, radically different signal.

**S03 — Consistency Voting**
Run the same query 3x at temperature 0.7:
- 3/3 agree: commit the answer
- 2/3 agree: flag for review
- 0/3 agree: the model is guessing, route to human

Show a case where the model is confident (sounds sure) but
inconsistent (different answer each time). Self-reported confidence
is "the wrong rubric" (184). Consistency voting is a mathematical
alternative. Connects to Demo 04 (Confidence).

**S04 — Structured Observability**
Define an agent decision as a Pydantic model. Run the agent.
Show model_dump() output — every field captured as structured data.
Query it: "show me all decisions where confidence < 0.7."

This is the bridge to production. The demos showed what the model
can do. Observability shows whether it keeps doing it. Connects
to the State Ledger pattern and the Logfire/OTel stack.

---

## Scripts

| Script | Purpose |
|--------|---------|
| `ask_claude.py` | Single-turn completions: `--schema`, `--thinking`, `--adaptive`, `--effort`, `--temperature`, `--model` |
| `agent.py` | Multi-turn agentic loop: `--tools`, `--plan`, `--model`, `--cache`, `--thinking` |
| `mcp_client.py` | MCP client: `--inspect`, `--verbose`, stdio/HTTP transport |
| `count_tokens.py` | Pre-flight token count across all 3 models |
| `validate.py` | Check JSON fields against known-good values |
| `run_tool.py` | Call tool functions directly (no API) |
| `eval.py` | Score a system prompt against a JSONL golden dataset (S01-S04) |
| `bigram.py`, `charmodel.py`, `attention_viz.py`, `rl_demo.py` | Pillar 1 model-building scripts |

## Test Modes

- `pytest` — fast structural tests, no API calls (693 tests)
- `pytest -m live` — pre-flight behavioral tests, real API (~$0.08)

## Audience Variants

Demos 02, 03, 05 (planned), 08, 18, 19, 20 have themed variants:
- `technical/` — engineering
- `expenses/` — business/finance
- `contract/` — legal
- `resume/` — HR/general

Presenter picks the directory that fits the room.

## Presentation Flow

**Full talk**: Pillar 1 -> Pillar 2 (Ch1 -> Ch2) -> Pillar 3
**Technical audience**: Pillar 2 Ch2 (skip LLM basics) -> Pillar 3
**Executive/non-technical**: Pillar 1 (focus on Layers 1-4) -> Pillar 3 (demos 18-20 with business variants)
**Security-focused**: Pillar 2 (all) -> Pillar 3 (S01-S03)

## Cross-References

- Transcript 048 — State Ledger Pattern: observability philosophy behind S04
- Transcript 184 — Agent Testing, Observability, Evals: golden datasets, ODD, Mirascope/Logfire
- Transcript 232 — LLM Mechanics, RL, Extended Thinking: attention mechanism, process vs outcome reward, Dweck parallel, DeepSeek curation
- Transcript 233 — MicroGPT Walkthrough: Karpathy's microgpt.py, transformer mechanics from scratch, origin of camp letters corpus idea, key analogies (DNS/reverse DNS for weight tying, assembly line for architecture, penalty score for loss)

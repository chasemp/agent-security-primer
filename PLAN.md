# Agent Security Primer — Plan

## Current State (2026-04-10)

24 demos built (20 original + 4 MCP), 528 mocked tests + 27 live pre-flight.
Two test modes: `pytest` (fast, no API) and `pytest -m live` (hits real API, ~$0.08).

### Scripts
- `ask_claude.py` — single-turn shim with `--schema`, `--thinking`, `--temperature`, `--model`
- `agent.py` — multi-turn agentic loop with `--tools`, `--plan`, `--model`
- `mcp_client.py` — MCP client with `--inspect`, `--verbose`, stdio/HTTP transport
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
| **Where They Shine (18-20)** | | |
| 18 | Few-Shot Pattern Learning | Examples shape predictions — prediction in action | ask_claude.py |
| 19 | Structured Extraction | Schema narrows the prediction menu | ask_claude.py --schema |
| 20 | Semantic Classification | Reads meaning, not keywords; examples improve accuracy | ask_claude.py |
| **MCP Security (21-24)** | | |
| 21 | MCP Basics | What MCP is, how tools get into context, two transports | mcp_client.py --inspect |
| 22 | MCP Recon | Server interrogates client via roots/list + sampling | mcp_client.py --verbose |
| 23 | MCP Rug Pull | Tool definitions mutate after trust is established | demo.py (single-session) |
| 24 | MCP Tool Injection | Malicious parameter descriptions exfiltrate data via tool args | mcp_client.py --verbose |
| **Where They Shine — Planned** | | |
| 25 | Domain Translation | Persona/audience framing steers predictions intentionally | ask_claude.py (planned) |
| 26 | Rubric-Based Evaluation | Explicit criteria shape evaluation patterns | ask_claude.py (planned) |
| 27 | Diagnosis from Evidence | Full context enables better reasoning | ask_claude.py (planned) |
| **Reliability (planned)** | | |
| 28 | Rate Limiting | Proactive throttling before hitting the wall | agent.py (planned) |

### Supporting Docs
- `talking_points.txt` in every demo directory
- `demos/meta_talking_points.txt` — inference pipeline, U-curve, model drift

---

## Next: Build a Tiny LLM (Second Track)

### Concept
A standalone educational piece — separate from the demo suite. The
idea is to literally build a very small language model from scratch
so the audience sees there's no magic.

### The Core Insight: Language Is Rhythm and Patterns

Human language is about rhythm and patterns — and that rhythm
reflects human thought. Build the explanation in layers:

**Layer 1: Rhythm as meaning**
Start with Hemingway's six-word story: "For sale: baby shoes,
never worn." Six words. The rhythm carries the meaning. The
audience FEELS the story in the pattern of the words, not in
any single word. Language has always been pattern-based.

**Layer 2: Prediction is natural**
"Shave and a haircut..." — everyone's mind completes it: "two
bits." You didn't compute that. You predicted it from the
rhythm. Your brain does next-token prediction constantly.

**Layer 3: 100 camp letters**
Show someone 100 summer camp letters from kids. Ask them to
predict what the next letter will say. They'll say "Dear Mom,
camp is fun, I miss you, the food is..." They just did
next-token prediction with their brain. The model does the
same thing with more data and more math.

**Layer 4: Scale creates the illusion of magic**
Now imagine you've read every book, every song, every
conversation ever written. Patterns on patterns on patterns
emerge. At that scale, prediction starts to look magical.
And it almost is — or it feels like it. But it's the same
mechanism as "shave and a haircut." Just at a scale where
the predictions become sophisticated enough to LOOK like
reasoning.

**Layer 5: Why tokenization**
Computers need numbers (ironic, given that LLMs are bad at
math). Tokenization converts language patterns into numerical
sequences. The patterns don't change — they just get encoded
in a form the math can operate on. The model learns which
numbers (tokens) tend to follow which other numbers, which
is exactly what the camp-letter reader did with words.

**Layer 6: Prediction and reasoning are tied**
The key insight that bridges Pillar 2 to Pillar 3: what
looks like "reasoning" IS prediction over patterns of thought.
When the model traces a bug or classifies a ticket, it's
completing patterns it learned from millions of examples of
people thinking carefully. Reasoning isn't separate from
prediction — it's what prediction looks like when the
patterns are rich enough.

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

**Pillar 2: Secure the agent (Demos 09-17, 21-23)**
Now that they understand the model, show how to build safely around
it. Problem-solution pairs: pollution → translation, exposure →
isolation, direct injection → indirect injection. MCP demos (21-23)
extend this to the protocol level: what MCP is, how servers can
interrogate clients (roots/list, sampling), and how tool definitions
can mutate after trust is established (rug pull).

**Pillar 3: Where they shine (Demos 18-20, 24-26 planned)**
Now that they understand prediction AND safety, show where
prediction IS reasoning — and how to steer it. Each demo has
two faces: what the model does well, and the prompt engineering
technique that makes it better.

**Tokenomics (Demo 17)**
Cost controls: caching (3 layers), thinking accumulation,
circuit breaker, token minimization. Bridges security and
practical operations.

**MCP Security (Demos 21-23)**
Protocol-level risks. Builds on agent security with a focus on
what happens when tools live across a trust boundary. The arc:
MCP basics → passive recon → tool mutation. Connects Demo 14
(credential isolation mentions MCP as production-grade pattern)
to the reality of MCP attack surface.

**Optional Pillar: Build a tiny LLM**
The "aha" moment that ties everything together. Could be a pre-talk
warmup, an appendix, or a separate session entirely.

**Planned: Rate Limiting (Demo 28)**
Proactive throttling — watch API capacity drain and slow down
before hitting the wall. Reads anthropic-ratelimit-* headers
from every response. Key design decisions:
  - Proactive, not reactive (don't wait for 429, watch remaining/limit)
  - 429 masking awareness (SDK retries 429s internally, you never
    see most of them — can't rely on 429 counts)
  - Multi-agent awareness (should_wait(active_agents=N) scales
    delay when concurrent agents share a rate limit pool)
  - Context window headroom is separate (token accumulation within
    a conversation vs. API-level rate limits — orthogonal concerns)
This might fold into Tokenomics or become its own demo. Decision
needed on where it fits best.

### Audience Variants
Demos 02, 03, 05 (planned), 08, 18, 19, and 20 have themed variants:
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

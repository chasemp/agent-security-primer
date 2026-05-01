# Pillar 1 Build-Out Plan

## Problem Statement
Pillar 1 (Build the Model) has talking points for all 7 demos (B01-B07),
working scripts and tests for B01-B02, a complete 1000-letter corpus,
but is missing scripts, tests, and visual assets for B03-B07.

## Approach
Build out in dependency order. Each phase delivers runnable demos with
tests. ASCII visual assets are static .txt files — no rendering
dependencies, work in any terminal.

## Reasoning
B03 needs no new script (reuses charmodel.py --temperature). B04
(attention) is architecturally independent from B05-B07 (RL), so they
can be built in parallel. B05-B07 share a single script (rl_demo.py)
but B05 must work before B06 (which compares against it) and B07
(which uses both).

Visual assets are simple enough to build alongside the scripts but
should be reviewed against the talking points to ensure they match
the presenter flow.

---

## Phase 1: Visual Assets + B03 Tests/Verification
**No new scripts needed. Fastest to complete.**

### 1a. ASCII Visual Assets
Create `demos/assets/` directory with static .txt files:

- `plinko_uniform.txt` — Pre-trained model, all paths equally likely.
  8 category bins with equal-height bars.
- `plinko_friendship.txt` — After friendship RL, friendship bin tall,
  others short. Same board structure, different distribution.
- `plinko_adventure.txt` — After adventure RL, adventure bin dominant.
  Shows that different rewards tilt differently.
- `loss_curve.txt` — ASCII bar chart showing penalty score dropping
  over epochs (4.2 → 0.7). Used in B02 presenter flow.
- `temperature_comparison.txt` — Three side-by-side probability
  distributions at temp 0.1, 1.0, and 2.0. Shows sharpening and
  flattening.
- `attention_matrix.txt` — Example attention weights for "Dear Mom I
  miss you" with highlighted high-attention cells. Shows causal mask
  (lower triangular). Used in B04.
- `autoregressive.txt` — Step-by-step showing one-token-at-a-time
  generation with the full context growing. Drives home the "full
  pass for every single character" point from B02.
- `outcome_vs_process.txt` — Side-by-side reward curves showing
  outcome (noisy, slow) vs process (smooth, fast). Used in B06.

### 1b. B03 Tests + Verification
B03 reuses charmodel.py with --temperature flag. Need:

- `tests/test_B03_temperature.py`:
  - Structural: talking_points.txt exists
  - Unit: generate at temp 0.01 is deterministic (same seed = same output)
  - Unit: generate at temp 0.01 vs temp 1.5 produces different output
  - Live: full presenter flow — generate at 5 temperature values,
    verify output varies systematically

Run tests, verify GREEN.

---

## Phase 2: B04 Attention Visualization
**Needs a new script: attention_viz.py**

### 2a. Script: scripts/attention_viz.py
A small transformer (2 layers, 4 heads, 64 embed) trained on the
camp letters corpus. Unlike B02's LSTM, this uses actual attention
so we can extract and display the weights.

Functions needed:
- `train_transformer(text, vocab, epochs)` — train small transformer
- `get_attention_weights(model, text, vocab)` — run forward pass,
  capture attention matrices from each layer/head
- `render_ascii_matrix(weights, tokens)` — terminal output showing
  attention grid with intensity indicators (·, ░, ▒, ▓, █)
- `render_causal_mask(size)` — show the triangular mask

CLI:
```
python scripts/attention_viz.py "Dear Mom I miss you" --train   # first time
python scripts/attention_viz.py "Dear Mom I miss you"           # show weights
python scripts/attention_viz.py "Dear Mom I miss you" --heads   # per-head view
python scripts/attention_viz.py "Dear Mom I miss you" --mask    # show causal mask
```

### 2b. Tests: tests/test_B04_attention.py
- Structural: talking_points.txt, script exists
- Unit: build_vocab, model forward pass shape, attention weights shape
- Unit: causal mask is lower-triangular
- Unit: attention weights sum to 1.0 per row (after softmax)
- Live: train on corpus, generate attention matrix, verify output
  contains token labels

---

## Phase 3: B05-B07 Reinforcement Learning
**Needs a new script: rl_demo.py. Build incrementally.**

### 3a. Script: scripts/rl_demo.py
Simplified RL training loop using REINFORCE algorithm on the B02
character model. Not production RL — just enough to demonstrate
the mechanism.

Core functions:
- `outcome_reward(text, theme_words)` — score complete text 0.0/1.0
  based on whether theme words appear
- `process_reward(text, theme_words)` — score each sentence 0.0-1.0
  based on theme word density and coherence
- `rl_train(model, vocab, corpus, reward_fn, steps)` — generate text,
  score, compute policy gradient, update weights. Return reward curve.
- `topic_classify(text)` — simple keyword classifier for the 8
  categories. Used for distribution comparison.
- `render_curve(rewards, label)` — ASCII reward-over-time chart
- `render_comparison(curve_a, curve_b)` — overlaid ASCII curves
- `render_distribution(counts, label)` — ASCII bar chart of topics

CLI:
```
# B05
python scripts/rl_demo.py corpus/camp_letters.txt --show-reward outcome
python scripts/rl_demo.py corpus/camp_letters.txt --train --reward outcome --steps 200
python scripts/rl_demo.py corpus/camp_letters.txt --generate --count 5
python scripts/rl_demo.py corpus/camp_letters.txt --show-curve

# B06
python scripts/rl_demo.py corpus/camp_letters.txt --train --reward process --steps 200
python scripts/rl_demo.py corpus/camp_letters.txt --show-curve --compare

# B07
python scripts/rl_demo.py corpus/camp_letters.txt --generate --count 10 --model pretrained
python scripts/rl_demo.py corpus/camp_letters.txt --generate --count 10 --model rl
python scripts/rl_demo.py corpus/camp_letters.txt --topic-distribution --compare
```

### 3b. Tests: tests/test_B05_outcome_reward.py
- Structural: talking_points.txt exists
- Unit: outcome_reward scores correctly (text with "friend" = 1.0, without = 0.0)
- Unit: topic_classify categorizes known text correctly
- Live: train 50 steps, verify reward curve increases

### 3c. Tests: tests/test_B06_process_reward.py
- Structural: talking_points.txt exists
- Unit: process_reward scores per-sentence
- Unit: process_reward gives higher score to friendship-dense text
- Live: train 50 steps outcome and 50 steps process, verify process
  converges faster (reward at step 50 is higher)

### 3d. Tests: tests/test_B07_shaping_the_board.py
- Structural: talking_points.txt exists
- Unit: topic_classify returns valid categories
- Unit: render_distribution produces output
- Live: generate 10 from pretrained vs rl-trained, verify rl-trained
  has higher friendship count

---

## Phase 4: Integration + Polish

### 4a. Full test suite run
```
pytest tests/test_B0*.py -v              # all structural + unit
pytest tests/test_B0*.py -v -m live      # full presenter flow
```

### 4b. Presenter flow walkthrough
Run through B01 → B02 → B03 → B04 → B05 → B06 → B07 in order.
Verify:
- Each demo builds on the previous
- Checkpoint handling works across demos
- Visual assets display correctly in terminal
- Timing: full Pillar 1 can be presented in <45 minutes

### 4c. Update PLAN.md status
Mark all demos as "Built + tested" once green.

---

## Dependency Graph

```
                    ┌──────────┐
                    │  Corpus  │ (DONE - 1000 letters)
                    └────┬─────┘
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
         ┌────────┐ ┌────────┐ ┌────────┐
         │  B01   │ │  B02   │ │ Assets │
         │ bigram │ │ char   │ │ ASCII  │
         │ (DONE) │ │ (DONE) │ │ (.txt) │
         └────────┘ └───┬────┘ └────────┘
                        │
              ┌─────────┼─────────┐
              ▼         ▼         ▼
         ┌────────┐ ┌────────┐ ┌────────┐
         │  B03   │ │  B04   │ │  B05   │
         │ temp   │ │ attn   │ │ outcome│
         │(no new │ │ viz.py │ │rl_demo │
         │script) │ └────────┘ └───┬────┘
         └────────┘                │
                              ┌────┴────┐
                              ▼         ▼
                         ┌────────┐ ┌────────┐
                         │  B06   │ │  B07   │
                         │process │ │ shape  │
                         │(compare│ │(compare│
                         │to B05) │ │pre/rl) │
                         └────────┘ └────────┘
```

## Estimated Effort
- Phase 1 (assets + B03): Light — mostly writing .txt files, minimal code
- Phase 2 (B04 attention): Medium — new script with transformer + viz
- Phase 3 (B05-B07 RL): Heaviest — rl_demo.py has the most logic
- Phase 4 (integration): Light — running tests and walking through flow

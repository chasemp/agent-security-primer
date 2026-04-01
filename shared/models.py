"""Model IDs and pricing constants for the demo suite.

Every demo imports from here. This is the single source of truth for:
  - Which Claude models are available (HAIKU, SONNET, OPUS)
  - Which model demos use by default (HAIKU — cheapest)
  - How much each model costs per token (for the live cost display)

Why centralize this? Two reasons:
  1. If Anthropic changes model IDs or pricing, we update ONE file.
  2. The token counter (shared/token_counter.py) needs pricing to show
     live cost. Every demo that uses the token counter gets correct
     pricing automatically because both import from here.

Pricing is per 1M tokens, matching Anthropic's published rates.
"""

# ---------------------------------------------------------------------------
# Model identifiers — these are the exact strings the Anthropic API expects
# in the `model` parameter of messages.create().
# ---------------------------------------------------------------------------

HAIKU = "claude-haiku-4-5"
SONNET = "claude-sonnet-4-6"
OPUS = "claude-opus-4-6"

# Haiku is the default for all demos. At $1/$5 per 1M tokens (input/output),
# the entire 10-demo suite costs under $1 to run. This matters because:
#   - Conference wifi is unreliable — fast, cheap calls are resilient.
#   - The presenter might run demos multiple times during rehearsal.
#   - The audience takeaway is security patterns, not model capability.
DEFAULT_DEMO_MODEL = HAIKU

# ---------------------------------------------------------------------------
# Pricing per 1 million tokens (USD)
#
# Used by TokenCounter to compute live cost as demos run.
# The audience sees this as a "speedometer" — especially in Demo 3
# (Death Spiral) where the counter climbs, and Demo 5 (Error Translation)
# where two counters diverge side-by-side.
# ---------------------------------------------------------------------------

PRICING: dict[str, dict[str, float]] = {
    HAIKU:  {"input": 1.00, "output": 5.00},
    SONNET: {"input": 3.00, "output": 15.00},
    OPUS:   {"input": 5.00, "output": 25.00},
}

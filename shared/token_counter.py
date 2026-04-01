"""Live token counter — the audience's "speedometer."

This is the most visible shared component in the demo suite. After every
API call, the counter updates to show:
  - Total input tokens consumed (what we sent TO the model)
  - Total output tokens consumed (what the model sent BACK)
  - Estimated cost in USD (computed from per-model pricing)

WHY THIS EXISTS:
  The token counter makes abstract concepts visceral for the audience:
  - In Demo 3 (Death Spiral), they watch cost climb as the agent retries
    a broken tool — "your agent is a credit card attached to a while loop."
  - In Demo 5 (Error Translation), two counters run side-by-side: one flat
    (translated errors), one climbing (raw errors). The divergence IS the lesson.
  - In Demo 4 (Context Position), the counter shows that attention costs
    the same regardless of whether the model actually follows the instruction.

HOW IT WORKS:
  After each API call, the demo passes response.usage to counter.update().
  The counter accumulates totals and computes cost using pricing from
  shared/models.py. It implements Rich's renderable protocol so it can
  be displayed as a live-updating panel.

CACHE TOKENS:
  The Anthropic API reports cache_read_input_tokens and
  cache_creation_input_tokens separately. We track them for transparency
  but the cost calculation uses total input_tokens (which already includes
  cache effects in the billing).
"""

from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from shared.models import PRICING


class TokenCounter:
    """Accumulates token usage across API calls and computes live cost.

    Args:
        model: The model ID (e.g., "claude-haiku-4-5"). Used to look up
               pricing from shared/models.py. Every demo passes this so
               the cost display is accurate for whichever model is running.
    """

    def __init__(self, model: str) -> None:
        self._model = model
        # Per-1M-token prices for this model
        self._input_price = PRICING[model]["input"]
        self._output_price = PRICING[model]["output"]

        # Running totals — these only go up (until reset)
        self.total_input: int = 0
        self.total_output: int = 0
        self.total_cache_read: int = 0
        self.total_cache_creation: int = 0

    def update(self, usage: dict) -> None:
        """Add one API response's token usage to the running totals.

        Args:
            usage: A dict matching the shape of response.usage from the
                   Anthropic API:
                     {
                       "input_tokens": int,
                       "output_tokens": int,
                       "cache_read_input_tokens": int,  # optional
                       "cache_creation_input_tokens": int,  # optional
                     }

        This is called after every messages.create() or stream completion.
        The counter accumulates — it never resets automatically. This lets
        the audience see the TOTAL cost of a multi-turn agent interaction.
        """
        self.total_input += usage.get("input_tokens", 0)
        self.total_output += usage.get("output_tokens", 0)
        self.total_cache_read += usage.get("cache_read_input_tokens", 0)
        self.total_cache_creation += usage.get("cache_creation_input_tokens", 0)

    @property
    def cost_usd(self) -> float:
        """Estimated cost in USD based on accumulated tokens and model pricing.

        Formula: (input_tokens * input_price + output_tokens * output_price) / 1M

        This is an estimate — actual billing may differ due to caching
        discounts, but it's close enough for a live demo display.
        """
        return (
            self.total_input * self._input_price
            + self.total_output * self._output_price
        ) / 1_000_000

    def reset(self) -> None:
        """Reset all counters to zero.

        Used by demos that run multiple comparisons (e.g., Demo 7 runs
        the same prompt 5 times at T=0 then 5 times at T=1.0 — the counter
        resets between the two batches so the audience sees per-batch cost).
        """
        self.total_input = 0
        self.total_output = 0
        self.total_cache_read = 0
        self.total_cache_creation = 0

    def __rich__(self) -> Panel:
        """Rich renderable protocol — returns a Panel showing live stats.

        Rich calls this automatically when you do `console.print(counter)`
        or use the counter inside a Rich Live display. The panel shows:
          - Input / output token counts (formatted with commas for readability)
          - Estimated cost as a dollar amount
          - Model name (so the audience knows which tier is running)
        """
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("label", style="dim")
        table.add_column("value", justify="right")

        table.add_row("Model", self._model)
        table.add_row("Input tokens", f"{self.total_input:,}")
        table.add_row("Output tokens", f"{self.total_output:,}")

        # Show cache stats only if there are any — avoids visual clutter
        # in demos that don't use caching
        if self.total_cache_read > 0 or self.total_cache_creation > 0:
            table.add_row("Cache read", f"{self.total_cache_read:,}")
            table.add_row("Cache created", f"{self.total_cache_creation:,}")

        # The cost line is the star — bold and colored
        cost_text = Text(f"${self.cost_usd:.4f}", style="bold yellow")
        table.add_row("Est. cost", cost_text)

        return Panel(table, title="Token Usage", border_style="cyan")

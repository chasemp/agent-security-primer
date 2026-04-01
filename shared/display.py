"""Rich terminal display components for the demo suite.

Every component here exists because raw print() is not acceptable for
a conference projector at 20 feet. The audience needs:
  - Clear visual hierarchy (panels, borders, headings)
  - Color coding (green = safe, red = vulnerable, yellow = punchline)
  - Syntax highlighting for code and JSON blocks
  - Structured layouts for side-by-side comparisons

DESIGN DECISIONS:
  - All components return Rich renderables (not strings). This lets them
    compose with Rich's Live display, Columns, and Panel nesting.
  - Color scheme is consistent across all demos:
      Green  = safe / defended / correct
      Red    = vulnerable / undefended / error
      Yellow = warnings / punchlines / attention
      Cyan   = informational / neutral
  - No component calls print() directly. The demo runner handles output
    through a shared Console instance.
"""

import json

from rich.columns import Columns
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text


# ---------------------------------------------------------------------------
# DemoPanel — section header shown at the start of each demo
# ---------------------------------------------------------------------------

class DemoPanel:
    """A titled panel showing which demo is running and what it demonstrates.

    Displayed at the start of each demo so the audience knows:
      - What section of the talk they're in (e.g., "Section 5 — Bouncer")
      - What demo is about to run (e.g., "The Banana Injection")
      - What security principle it demonstrates

    Example output:
      ┌─ [Section 1] The Banana Injection ─────────────────────┐
      │ Data and code are the same thing to an LLM.            │
      └────────────────────────────────────────────────────────┘
    """

    def __init__(self, title: str, section: str, description: str) -> None:
        self._title = title
        self._section = section
        self._description = description

    def __rich__(self) -> Panel:
        return Panel(
            Text(self._description),
            title=f"[bold cyan][{self._section}][/bold cyan] {self._title}",
            border_style="bright_blue",
            padding=(1, 2),
        )


# ---------------------------------------------------------------------------
# SideBySide — two-panel comparison layout
# ---------------------------------------------------------------------------

class SideBySide:
    """Places two renderables next to each other for comparison.

    The visual backbone of "before/after" and "defended/undefended" demos.
    Uses Rich Columns with equal=True so both sides get the same width
    regardless of content length.

    Color convention:
      - Left panel (red border):  the vulnerable / undefended version
      - Right panel (green border): the safe / defended version

    Used in:
      - Demo 5 (Error Translation): raw error vs translated error
      - Demo 9 (Env Var Attack): undefended vs hook-defended
      - Demo 6 ext (Plan Mode): normal execution vs plan-only
    """

    def __init__(
        self,
        left: object,
        right: object,
        left_title: str = "",
        right_title: str = "",
    ) -> None:
        self._left = left
        self._right = right
        self._left_title = left_title
        self._right_title = right_title

    def __rich__(self) -> Columns:
        # Wrap each side in a Panel if titles are provided.
        # Red for the "bad" side (left), green for the "good" side (right).
        left = Panel(
            self._left,
            title=self._left_title or None,
            border_style="red",
        ) if self._left_title else self._left

        right = Panel(
            self._right,
            title=self._right_title or None,
            border_style="green",
        ) if self._right_title else self._right

        return Columns([left, right], equal=True, expand=True)


# ---------------------------------------------------------------------------
# step() — numbered presenter-paced step
# ---------------------------------------------------------------------------

def step(text: str, number: int = 1) -> Text:
    """A numbered step for presenter narration.

    Returns a styled Text like: "[1] Making the API call..."

    Steps control pacing — the presenter narrates while the code waits.
    Each step is displayed, then the demo pauses (configurable delay)
    before proceeding. This prevents the audience from being overwhelmed
    by everything happening at once.

    The actual pause happens in the demo runner, not here — this function
    only creates the visual element.
    """
    result = Text()
    result.append(f"[{number}] ", style="bold cyan")
    result.append(text)
    return result


# ---------------------------------------------------------------------------
# punchline() — the memorable one-liner
# ---------------------------------------------------------------------------

def punchline(text: str) -> Panel:
    """Bold, attention-grabbing text for the demo's key takeaway.

    Every demo ends with a punchline — one sentence that encapsulates
    the security lesson. Examples:
      "Data and code are the same thing to an LLM."
      "The model writes JSON. Your code decides what's real."
      "Your agent is a credit card attached to a while loop."

    Rendered as bold yellow text inside a bordered panel so it stands
    out from everything else on screen. The border is yellow too —
    the audience's eye is drawn to it immediately.
    """
    return Panel(
        Text(text, style="bold yellow", justify="center"),
        border_style="yellow",
        padding=(1, 2),
    )


# ---------------------------------------------------------------------------
# code_block() — syntax-highlighted source code
# ---------------------------------------------------------------------------

def code_block(code: str, language: str = "python") -> Panel:
    """Syntax-highlighted code in a bordered panel.

    The audience reads this code after the talk — it needs to be clear
    and readable. Rich's Syntax class handles highlighting. We wrap it
    in a Panel for visual separation from surrounding output.

    Used to show:
      - Tool definitions (Demo 6: the lookup_user tool schema)
      - Pydantic models (Demo 2: the ServerAction validator)
      - Hook implementations (Demo 9: the pre_bash_guard)
      - One-liner fixes (Demo 3: max_turns, max_budget_usd)
    """
    syntax = Syntax(code, language, theme="monokai", line_numbers=False)
    return Panel(syntax, border_style="dim")


# ---------------------------------------------------------------------------
# thinking_block() — model internal reasoning (GoPro demo)
# ---------------------------------------------------------------------------

def thinking_block(text: str) -> Panel:
    """Displays the model's internal thinking/reasoning text.

    Used in the GoPro demo where the audience watches models reason
    through an impossible task. The thinking text appears with a distinct
    "THINKING" label and italic styling so the audience can distinguish:
      - Thinking: what the model reasons internally (visible via API)
      - Output: what the model says "out loud" to the user

    This distinction is the entire point of the GoPro demo — once the
    audience has seen the model think, they stop seeing a black box.
    They're now imagining the reasoning chain behind every subsequent demo.
    """
    content = Text()
    content.append("[THINKING]\n", style="bold magenta")
    content.append(text, style="italic")
    return Panel(content, border_style="magenta", title="Model Reasoning")


# ---------------------------------------------------------------------------
# tool_use_block() — JSON tool call display (Ender's Game demo)
# ---------------------------------------------------------------------------

def tool_use_block(data: dict) -> Panel:
    """Renders a tool_use JSON block with syntax highlighting.

    Used in Demo 6 (Tool Mechanics) to show the raw JSON that the model
    produces when it wants to call a tool. The audience sees:

      {
        "name": "lookup_user",
        "input": {"username": "alice"},
        "id": "toolu_abc123"
      }

    This is the "Ender's Game" moment: the model is just writing JSON.
    It doesn't execute anything. The stop_reason tells YOUR CODE that
    the model wants to act. YOUR CODE decides whether to comply.

    The JSON is pretty-printed for readability and highlighted with
    Rich's Syntax class.
    """
    formatted = json.dumps(data, indent=2)
    syntax = Syntax(formatted, "json", theme="monokai", line_numbers=False)
    return Panel(syntax, border_style="bright_yellow", title="tool_use")

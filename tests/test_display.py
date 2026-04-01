"""Tests for Rich terminal display components.

These components are the audience's experience. On a conference projector,
legibility at 20 feet matters — so we use Rich panels, colored text, and
structured layouts instead of raw print() statements.

Each component has a specific visual role:
  - DemoPanel: Titles and descriptions for each demo (section headers)
  - SideBySide: Two panels side-by-side (defended vs undefended comparisons)
  - step(): Numbered steps with pauses (presenter-controlled pacing)
  - punchline(): Bold yellow text (the moment the audience remembers)
  - code_block(): Syntax-highlighted code (educational — audience reads after)
  - thinking_block(): Model thinking text in distinct style (GoPro demo)
  - tool_use_block(): JSON syntax highlighting (Tool Mechanics demo)

We test by capturing Rich console output to strings and checking structure.
No visual/screenshot testing — we verify the data is present and formatted.
"""

from io import StringIO

from rich.console import Console

from shared.display import (
    DemoPanel,
    Presenter,
    SideBySide,
    code_block,
    punchline,
    step,
    thinking_block,
    tool_use_block,
)


def _render(renderable) -> str:
    """Capture a Rich renderable to a plain string for assertions.

    We use force_terminal=True so Rich applies styling (which we can check),
    and a fixed width so layout is deterministic across machines.
    """
    console = Console(file=None, force_terminal=True, width=100)
    with console.capture() as capture:
        console.print(renderable)
    return capture.get()


# ---------------------------------------------------------------------------
# DemoPanel — section header for each demo
# ---------------------------------------------------------------------------

class TestDemoPanel:
    """DemoPanel wraps a demo's title, section tag, and description in a
    Rich Panel. The audience sees this at the start of each demo to orient
    them: "What section of the talk are we in? What demo is this?"
    """

    def test_contains_title(self) -> None:
        panel = DemoPanel(
            title="The Banana Injection",
            section="Section 1",
            description="Data and code are the same thing to an LLM.",
        )
        output = _render(panel)
        assert "Banana Injection" in output

    def test_contains_section(self) -> None:
        panel = DemoPanel(
            title="Test Demo",
            section="Section 5",
            description="A test.",
        )
        output = _render(panel)
        assert "Section 5" in output

    def test_contains_description(self) -> None:
        panel = DemoPanel(
            title="Test Demo",
            section="Section 1",
            description="This is the description text.",
        )
        output = _render(panel)
        assert "description text" in output


# ---------------------------------------------------------------------------
# SideBySide — two-panel comparison layout
# ---------------------------------------------------------------------------

class TestSideBySide:
    """SideBySide places two Rich renderables next to each other using Columns.

    This is the visual backbone of comparison demos:
      - Demo 5: raw error (red, left) vs translated error (green, right)
      - Demo 9: undefended (red, left) vs defended (green, right)
      - Demo 6 ext: normal mode vs plan mode

    The color coding is consistent: red = vulnerable, green = safe.
    """

    def test_renders_both_panels(self) -> None:
        layout = SideBySide(left="LEFT CONTENT", right="RIGHT CONTENT")
        output = _render(layout)
        assert "LEFT CONTENT" in output
        assert "RIGHT CONTENT" in output

    def test_accepts_titles(self) -> None:
        layout = SideBySide(
            left="left",
            right="right",
            left_title="Undefended",
            right_title="Defended",
        )
        output = _render(layout)
        assert "Undefended" in output
        assert "Defended" in output


# ---------------------------------------------------------------------------
# step() — numbered steps with presenter pacing
# ---------------------------------------------------------------------------

class TestStep:
    """step() creates a numbered, styled text line for presenter narration.

    Steps appear as: "[1] Setting up the API call..."
    The presenter narrates while the code waits. This controls pacing
    so the audience follows along instead of being overwhelmed.
    """

    def test_contains_step_text(self) -> None:
        output = _render(step("Making the API call", number=1))
        assert "Making the API call" in output

    def test_contains_step_number(self) -> None:
        output = _render(step("Checking the result", number=3))
        assert "3" in output


# ---------------------------------------------------------------------------
# punchline() — the moment the audience remembers
# ---------------------------------------------------------------------------

class TestPunchline:
    """punchline() renders bold, attention-grabbing text.

    Every demo ends with a punchline — one sentence that encapsulates
    the security lesson. For example:
      Demo 1: "Data and code are the same thing to an LLM."
      Demo 3: "Your agent is a credit card attached to a while loop."
    """

    def test_contains_text(self) -> None:
        output = _render(punchline("Data and code are the same thing."))
        assert "Data and code are the same thing" in output


# ---------------------------------------------------------------------------
# code_block() — syntax-highlighted code for the audience to read
# ---------------------------------------------------------------------------

class TestCodeBlock:
    """code_block() renders syntax-highlighted code in a Rich panel.

    The audience reads this code after the talk. It needs to be
    clear and readable — Python syntax highlighting helps.
    """

    def test_contains_code(self) -> None:
        output = _render(code_block('print("hello")', language="python"))
        assert "hello" in output


# ---------------------------------------------------------------------------
# thinking_block() — model internal reasoning display (GoPro demo)
# ---------------------------------------------------------------------------

class TestThinkingBlock:
    """thinking_block() displays the model's thinking/reasoning text.

    Used in the GoPro demo where the audience watches three models
    reason through the same impossible task. The thinking text streams
    live — this component styles it distinctly from regular output so
    the audience can tell "this is what the model is thinking internally"
    vs "this is what the model said out loud."
    """

    def test_contains_thinking_text(self) -> None:
        output = _render(thinking_block("I need to restart a server..."))
        assert "restart a server" in output

    def test_has_thinking_label(self) -> None:
        output = _render(thinking_block("some thought"))
        # Should indicate this is thinking/reasoning content
        assert "THINKING" in output.upper() or "thinking" in output.lower()


# ---------------------------------------------------------------------------
# tool_use_block() — JSON display for tool call inspection
# ---------------------------------------------------------------------------

class TestToolUseBlock:
    """tool_use_block() renders a tool_use JSON block with syntax highlighting.

    Used in Demo 6 (Tool Mechanics) where the audience sees the raw JSON
    that the model produces when it "calls" a tool. The JSON includes:
      - name: which tool the model wants to call
      - input: the arguments it's passing
      - id: the unique ID linking the call to its result

    This is the "Ender's Game" moment — the audience sees that the model
    is just writing JSON, and YOUR CODE decides whether to execute it.
    """

    def test_contains_json_fields(self) -> None:
        data = {"name": "lookup_user", "input": {"username": "alice"}}
        output = _render(tool_use_block(data))
        assert "lookup_user" in output
        assert "alice" in output


# ---------------------------------------------------------------------------
# Presenter — interactive step controller
# ---------------------------------------------------------------------------

class TestPresenter:
    """Presenter wraps a Console and controls interactive pacing.

    In interactive mode (default): presenter.step() prints the step text
    and waits for Enter before continuing. The presenter narrates while
    the audience reads.

    In speedrun mode (--no-pause): steps print immediately with no pause.
    Used for recording or rehearsal.

    The Presenter replaces direct console.print(step(...)) calls in demos.
    Demos receive a Presenter instead of a raw Console.
    """

    def test_step_prints_text(self) -> None:
        """In no-pause mode, step prints the text without blocking."""
        console = Console(file=None, force_terminal=True, width=100)
        p = Presenter(console, interactive=False)
        with console.capture() as capture:
            p.step("Reading the file", number=1)
        output = capture.get()
        assert "Reading the file" in output
        assert "1" in output

    def test_show_prints_renderable(self) -> None:
        """presenter.show() prints any Rich renderable (panels, text, etc.)."""
        console = Console(file=None, force_terminal=True, width=100)
        p = Presenter(console, interactive=False)
        with console.capture() as capture:
            p.show(punchline("Test punchline"))
        output = capture.get()
        assert "Test punchline" in output

    def test_interactive_mode_is_default(self) -> None:
        """Interactive (pause on step) should be the default behavior."""
        console = Console(file=None, force_terminal=True, width=100)
        p = Presenter(console)
        assert p.interactive is True

    def test_punchline_convenience(self) -> None:
        """presenter.punchline() is a shortcut for showing the punchline."""
        console = Console(file=None, force_terminal=True, width=100)
        p = Presenter(console, interactive=False)
        with console.capture() as capture:
            p.punchline("Data and code are the same thing.")
        output = capture.get()
        assert "Data and code are the same thing" in output

"""Presenter CLI — one command to run the entire talk.

This is the entry point the speaker types at the podium:

  presenter run 1              Run demo 1 only
  presenter run banana         Run by name
  presenter run all            Full presentation sequence (talk order)
  presenter run 1 gopro 6     Run specific demos in a custom order
  presenter list               List all demos with sections
  presenter check              Verify API key, deps, connectivity

DESIGN DECISIONS:

  Click over argparse:
    Click gives us subcommands, help text, and tab completion for free.
    The presenter needs to type commands quickly on stage — tab completion
    and clear --help output matter.

  Async under Click:
    Demos are async (they use the Anthropic streaming API). Click is sync.
    We bridge with anyio.run() inside the run command. The presenter
    doesn't see this — they just type `presenter run 1` and it works.

  Graceful degradation:
    If a demo ID isn't found, we print a message and continue — never crash.
    Mid-presentation crashes are the worst possible outcome. Every error
    path should fail gracefully with a human-readable message.

PRESENTATION SEQUENCE:
  The talk order is: 1 → gopro → 6 → 7 → 2 → 3 → 4 → 8 → 9 → 5
  This matches the runsheet in the talk outline. The demos flow from
  "hook the audience" (banana injection) through "understand the mechanism"
  (tool mechanics) to "here's how to defend" (hooks, MCP, error translation).
"""

import os
import sys

import anyio
import click
from rich.console import Console
from rich.table import Table

from shared.runner import DemoRegistry

# ---------------------------------------------------------------------------
# Global registry — demos register themselves when their modules are imported.
# In Phase 1 this is empty. Phase 2+ demo modules will import this and use
# @register_demo(registry) to add themselves.
# ---------------------------------------------------------------------------
registry = DemoRegistry()

# The full presentation sequence matching the talk runsheet.
# This is the order `presenter run all` uses.
TALK_SEQUENCE = ["1", "gopro", "6", "7", "2", "2.5", "3", "4", "8", "9", "5"]


@click.group()
def cli() -> None:
    """Presenter CLI for the Secure AI Agents 101 demo suite.

    Run individual demos, the full presentation, or pre-flight checks.
    """
    pass


# ---------------------------------------------------------------------------
# presenter list
# ---------------------------------------------------------------------------

@cli.command("list")
def list_cmd() -> None:
    """List all registered demos with their sections and descriptions."""
    console = Console()
    demos = registry.list_demos()

    if not demos:
        console.print("[dim]No demos registered yet.[/dim]")
        console.print("[dim]Demos register when their modules are imported.[/dim]")
        console.print("[dim]See PLAN.md Phase 2+ for demo implementations.[/dim]")
        return

    # Build a Rich table showing all demos in registration order.
    # The section column helps the presenter map demos to talk sections.
    table = Table(title="Demo Suite")
    table.add_column("#", style="bold cyan", width=6)
    table.add_column("Name", style="bold")
    table.add_column("Section", style="dim")
    table.add_column("Description")

    for demo in demos:
        table.add_row(demo.number, demo.name, demo.section, demo.description)

    console.print(table)


# ---------------------------------------------------------------------------
# presenter check
# ---------------------------------------------------------------------------

@cli.command("check")
def check_cmd() -> None:
    """Pre-talk verification: SDK auth, dependencies, connectivity.

    Run this 10 minutes before the talk to catch problems early.
    Green checkmarks = ready. Red X = fix before going on stage.
    """
    console = Console()
    all_ok = True

    # 1. Check claude-agent-sdk is importable and the CLI is available.
    #    The Agent SDK wraps the Claude Code CLI for auth — no API key needed.
    #    If the SDK isn't installed or the CLI isn't authenticated, nothing works.
    try:
        import claude_agent_sdk  # noqa: F401
        console.print("[green]  claude-agent-sdk importable[/green]")
    except ImportError:
        console.print("[red]  claude-agent-sdk not found[/red]")
        console.print("    [dim]pip install claude-agent-sdk[/dim]")
        all_ok = False

    # 2. Check other core dependencies are importable.
    #    If pip install failed or the venv isn't activated, catch it here.
    deps = ["pydantic", "rich", "click", "anyio"]
    for dep in deps:
        try:
            __import__(dep)
            console.print(f"[green]  {dep} importable[/green]")
        except ImportError:
            console.print(f"[red]  {dep} not found[/red]")
            all_ok = False

    # 3. Check optional anthropic SDK for Demo 7 (temperature comparison).
    #    This is the only demo that needs a direct API key. If it's not
    #    installed, Demo 7 falls back to --prerecorded results.
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    try:
        import anthropic  # noqa: F401
        if api_key:
            console.print("[green]  anthropic SDK + ANTHROPIC_API_KEY (Demo 7 live mode)[/green]")
        else:
            console.print("[yellow]  anthropic SDK installed but no ANTHROPIC_API_KEY (Demo 7 will use --prerecorded)[/yellow]")
    except ImportError:
        console.print("[yellow]  anthropic SDK not installed (Demo 7 will use --prerecorded)[/yellow]")
        console.print("    [dim]pip install agent-security-primer[temperature] for live Demo 7[/dim]")

    # 4. Show registered demo count
    demo_count = len(registry.list_demos())
    console.print(f"\n[cyan]{demo_count} demos registered[/cyan]")

    if all_ok:
        console.print("\n[bold green]Ready to present.[/bold green]")
    else:
        console.print("\n[bold red]Fix the issues above before presenting.[/bold red]")
        sys.exit(1)


# ---------------------------------------------------------------------------
# presenter run
# ---------------------------------------------------------------------------

@cli.command("run")
@click.argument("demo_ids", nargs=-1, required=True)
@click.option("--model", default=None, help="Override model for all demos")
@click.option("--prerecorded", is_flag=True, help="Use pre-recorded results where available")
@click.option("--quick", is_flag=True, help="Skip optional panels (e.g., Opus in GoPro)")
@click.option("--no-pause", is_flag=True, help="Skip inter-demo pauses (for recording)")
@click.option("--show-thinking", is_flag=True, help="Use Sonnet for thinking block demos")
def run_cmd(demo_ids, model, prerecorded, quick, no_pause, show_thinking) -> None:
    """Run one or more demos. Use 'all' for the full presentation sequence.

    Examples:
      presenter run 1              Run demo 1 only
      presenter run banana         Run by name
      presenter run all            Full presentation in talk order
      presenter run 1 gopro 6     Run specific demos in order
    """
    console = Console()

    # Expand "all" to the full talk sequence
    if "all" in demo_ids:
        keys = TALK_SEQUENCE
    else:
        keys = list(demo_ids)

    # Resolve demo IDs to actual Demo objects
    demos = registry.sequence(keys)

    if not demos:
        console.print("[yellow]No matching demos found.[/yellow]")
        console.print("[dim]Available demos:[/dim]")
        for d in registry.list_demos():
            console.print(f"  [cyan]{d.number}[/cyan] / [cyan]{d.name}[/cyan] — {d.description}")
        if not registry.list_demos():
            console.print("  [dim](none registered yet — see PLAN.md Phase 2+)[/dim]")
        return

    # Build kwargs that get passed through to each demo's run() method.
    # Each demo accepts what it needs via **kwargs and ignores the rest.
    kwargs = {
        "model": model,
        "prerecorded": prerecorded,
        "quick": quick,
        "no_pause": no_pause,
        "show_thinking": show_thinking,
    }

    # Run demos sequentially via anyio (async bridge).
    # Sequential because:
    #   1. The presenter narrates between demos
    #   2. API rate limits could interfere with parallel calls
    #   3. The terminal display would be chaotic with concurrent output
    anyio.run(_run_sequence, demos, console, kwargs, no_pause)


async def _run_sequence(
    demos: list,
    console: Console,
    kwargs: dict,
    no_pause: bool,
) -> None:
    """Run a sequence of demos with optional inter-demo pauses.

    The "Press Enter to continue" gate between demos lets the presenter
    control pacing. They can take questions, explain what's coming next,
    or adjust the talk flow based on audience engagement.
    """
    for i, demo in enumerate(demos):
        # Show which demo is running
        console.rule(f"[bold]{demo.section} — {demo.name}[/bold]")
        console.print(f"[dim]{demo.description}[/dim]\n")

        await demo.run(console, **kwargs)

        # Gate between demos (unless --no-pause for recording)
        if not no_pause and i < len(demos) - 1:
            console.print()
            console.input("[dim]Press Enter to continue...[/dim]")

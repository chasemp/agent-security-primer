"""Demo runner — registration, lookup, and sequencing.

This module provides the skeleton that the presenter CLI hangs on.
It answers three questions:
  1. "What demos exist?" → DemoRegistry.list_demos()
  2. "Run this specific demo" → DemoRegistry.get("banana")
  3. "Run these demos in talk order" → DemoRegistry.sequence(["1", "gopro", "6"])

HOW DEMO REGISTRATION WORKS:
  Each demo module (e.g., demo_01_banana_injection/run.py) defines a class
  that extends Demo and decorates it with @register_demo:

      @register_demo(registry)
      class BananaInjection(Demo):
          number = "1"
          name = "banana"
          section = "Section 1"
          description = "Data and code are the same thing to an LLM."

          async def run(self, console, **kwargs):
              ...

  The decorator instantiates the class and adds it to the registry.
  No central manifest file to maintain — the decorator IS the registration.

WHY ASYNC:
  Some demos use the Anthropic streaming API (client.messages.stream()),
  which is async. Making all demos async (even the simple ones) keeps the
  interface uniform and avoids mixing sync/async patterns.

WHY **kwargs IN run():
  The presenter CLI passes flags like --prerecorded, --quick, --show-thinking
  to demos. Each demo accepts what it needs and ignores the rest via **kwargs.
  This means adding a new flag doesn't require updating every demo.
"""

from abc import ABC, abstractmethod

from rich.console import Console


# ---------------------------------------------------------------------------
# Demo base class
# ---------------------------------------------------------------------------

class Demo(ABC):
    """Base class for all demos.

    Subclasses must define:
      - number: The demo's identifier (e.g., "1", "gopro", "2.5")
      - name: A short, memorable name (e.g., "banana", "death_spiral")
      - section: Which talk section this belongs to (e.g., "Section 5")
      - description: One-line description of what the demo proves

    And implement:
      - run(console, **kwargs): The async method that performs the demo
    """

    # These are class-level attributes that subclasses override.
    # They're not instance attributes because they're the same for
    # every instance of a given demo — they describe the demo itself.
    number: str
    name: str
    section: str
    description: str

    @abstractmethod
    async def run(self, console: Console, **kwargs) -> None:
        """Execute the demo.

        Args:
            console: Rich Console for all output. Demos never call print()
                     directly — they use this console so output can be
                     captured, redirected, or styled consistently.
            **kwargs: Presenter CLI flags (prerecorded, quick, show_thinking, etc.)
        """
        ...


# ---------------------------------------------------------------------------
# DemoRegistry
# ---------------------------------------------------------------------------

class DemoRegistry:
    """Collects registered demos and supports lookup by number or name.

    The registry holds instantiated Demo objects. It supports:
      - get(key): Find a demo by its number OR name
      - list_demos(): All demos in registration order
      - sequence(keys): Ordered list of demos for a presentation run

    The presenter CLI uses these methods:
      - `presenter list` → list_demos()
      - `presenter run 1` → get("1")
      - `presenter run 1 gopro 6` → sequence(["1", "gopro", "6"])
      - `presenter run all` → list_demos() (all demos in order)
    """

    def __init__(self) -> None:
        # Ordered list of demos (registration order = insertion order)
        self._demos: list[Demo] = []
        # Lookup indexes for fast access by number or name
        self._by_number: dict[str, Demo] = {}
        self._by_name: dict[str, Demo] = {}

    def register(self, demo: Demo) -> None:
        """Add a demo to the registry.

        Called by the @register_demo decorator. Indexes the demo by both
        its number and name so either can be used for lookup.
        """
        self._demos.append(demo)
        self._by_number[demo.number] = demo
        self._by_name[demo.name] = demo

    def get(self, key: str) -> Demo | None:
        """Look up a demo by number or name.

        Tries number first (e.g., "1"), then name (e.g., "banana").
        Returns None if not found — the caller decides how to handle it.
        """
        return self._by_number.get(key) or self._by_name.get(key)

    def list_demos(self) -> list[Demo]:
        """All registered demos in registration order.

        Registration order is the order demo modules are imported,
        which the presenter CLI controls. This is NOT necessarily
        the presentation order — that's what sequence() is for.
        """
        return list(self._demos)

    def sequence(self, keys: list[str]) -> list[Demo]:
        """Return demos in the specified order, skipping unknowns.

        The presentation order differs from numeric order. The talk runs:
          1 → gopro → 6 → 7 → 2 → 3 → 4 → 8 → 9 → 5

        Unknown keys are silently skipped. This is intentional — it's better
        to run the demos we have than to crash mid-presentation because
        a demo hasn't been built yet (Phase 2 demos won't exist during
        Phase 1 development).
        """
        result = []
        for key in keys:
            demo = self.get(key)
            if demo is not None:
                result.append(demo)
        return result


# ---------------------------------------------------------------------------
# @register_demo decorator
# ---------------------------------------------------------------------------

def register_demo(registry: DemoRegistry):
    """Decorator that registers a Demo subclass with the given registry.

    Usage:
        @register_demo(registry)
        class BananaInjection(Demo):
            number = "1"
            name = "banana"
            ...

    The decorator:
      1. Instantiates the class (no arguments — demos are stateless)
      2. Registers the instance with the registry
      3. Returns the class unchanged (so the module can still use it)

    Why return the class, not the instance? Because Python decorators
    replace the name. If we returned the instance, `BananaInjection`
    would be an instance, not a class — confusing for anyone reading
    the demo module.
    """

    def decorator(cls):
        instance = cls()
        registry.register(instance)
        return cls

    return decorator

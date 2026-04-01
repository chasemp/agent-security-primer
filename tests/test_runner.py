"""Tests for the demo runner and registry.

The runner provides the skeleton that the presenter CLI hangs on:
  - A Demo base class that each demo module extends
  - A DemoRegistry that collects demos via @register_demo decorator
  - Lookup by number (e.g., "1") or name (e.g., "banana")
  - Sequence ordering for the full presentation flow

The registry pattern means adding a new demo is just:
  1. Create demo_XX_name/run.py
  2. Decorate the class with @register_demo
  3. It shows up in `presenter list` and `presenter run` automatically

No central manifest to maintain. The decorator IS the registration.
"""

import pytest

from shared.runner import Demo, DemoRegistry, register_demo


# ---------------------------------------------------------------------------
# Demo base class
# ---------------------------------------------------------------------------

class TestDemoBaseClass:
    """Demo is the base class every demo extends.

    It defines the contract: every demo has a number, a name, a section
    (which talk section it belongs to), a description, and an async run()
    method that actually performs the demo.
    """

    def test_demo_has_required_attributes(self) -> None:
        """Subclasses must provide number, name, section, description."""

        class MyDemo(Demo):
            number = "1"
            name = "test"
            section = "Section 1"
            description = "A test demo."

            async def run(self, console, **kwargs) -> None:
                pass

        demo = MyDemo()
        assert demo.number == "1"
        assert demo.name == "test"
        assert demo.section == "Section 1"
        assert demo.description == "A test demo."


# ---------------------------------------------------------------------------
# DemoRegistry
# ---------------------------------------------------------------------------

class TestDemoRegistry:
    """The registry collects demos and supports lookup for the presenter CLI.

    It must support:
      - Registration via @register_demo decorator
      - Lookup by number ("1", "gopro") for `presenter run 1`
      - Lookup by name ("banana") for `presenter run banana`
      - Listing all demos in order for `presenter list`
    """

    def _make_registry_with_demos(self) -> DemoRegistry:
        """Create a fresh registry with two test demos.

        We create a new registry each time so tests don't interfere
        with each other (no shared mutable state).
        """
        registry = DemoRegistry()

        @register_demo(registry)
        class DemoOne(Demo):
            number = "1"
            name = "banana"
            section = "Section 1"
            description = "The banana injection."

            async def run(self, console, **kwargs) -> None:
                pass

        @register_demo(registry)
        class DemoTwo(Demo):
            number = "2"
            name = "hallucinated_id"
            section = "Section 5"
            description = "The hallucinated ID."

            async def run(self, console, **kwargs) -> None:
                pass

        return registry

    def test_register_and_list(self) -> None:
        registry = self._make_registry_with_demos()
        demos = registry.list_demos()
        assert len(demos) == 2

    def test_lookup_by_number(self) -> None:
        """presenter run 1 → finds the demo with number='1'."""
        registry = self._make_registry_with_demos()
        demo = registry.get("1")
        assert demo is not None
        assert demo.name == "banana"

    def test_lookup_by_name(self) -> None:
        """presenter run banana → finds the demo with name='banana'."""
        registry = self._make_registry_with_demos()
        demo = registry.get("banana")
        assert demo is not None
        assert demo.number == "1"

    def test_lookup_not_found_returns_none(self) -> None:
        registry = self._make_registry_with_demos()
        assert registry.get("nonexistent") is None

    def test_list_demos_ordered_by_number(self) -> None:
        """presenter list shows demos in number order.

        Numbers are strings (e.g., '1', '2', 'gopro') so we sort
        them in registration order, which the presenter controls.
        """
        registry = self._make_registry_with_demos()
        demos = registry.list_demos()
        assert demos[0].number == "1"
        assert demos[1].number == "2"

    def test_register_demo_returns_class(self) -> None:
        """The @register_demo decorator should return the class unchanged.
        This is important — the demo module can still use the class normally
        after decorating it."""
        registry = DemoRegistry()

        @register_demo(registry)
        class MyDemo(Demo):
            number = "99"
            name = "test"
            section = "Test"
            description = "Test."

            async def run(self, console, **kwargs) -> None:
                pass

        # The class is still usable after decoration
        assert MyDemo.name == "test"

    def test_presentation_sequence(self) -> None:
        """registry.sequence(['2', 'banana']) returns demos in that order.

        The presenter specifies the talk order, which differs from
        numeric order. For example: presenter run 1 gopro 6 7 2 3 4 8 9 5
        """
        registry = self._make_registry_with_demos()
        sequence = registry.sequence(["2", "banana"])
        assert len(sequence) == 2
        assert sequence[0].number == "2"
        assert sequence[1].name == "banana"

    def test_sequence_skips_unknown(self) -> None:
        """Unknown IDs in the sequence are silently skipped.
        Better to run the demos we have than to crash mid-presentation."""
        registry = self._make_registry_with_demos()
        sequence = registry.sequence(["1", "nonexistent", "2"])
        assert len(sequence) == 2

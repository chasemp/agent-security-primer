"""Pytest configuration — registers the 'live' marker for API tests.

Run mocked tests (default):  pytest
Run live API tests:          pytest -m live
Run everything:              pytest -m ''
"""

import os

import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "live: hits the real Anthropic API (requires ANTHROPIC_API_KEY)")


def pytest_collection_modifyitems(config, items):
    if config.getoption("-m") and "live" in config.getoption("-m"):
        return
    skip = pytest.mark.skip(reason="live tests only run with: pytest -m live")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip)

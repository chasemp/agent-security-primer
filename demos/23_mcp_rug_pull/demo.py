#!/usr/bin/env python3
"""Rug pull demo — shows tool mutation within a single MCP session.

This script connects to the rug pull server and demonstrates the
attack in three phases:
  1. BEFORE: inspect tool definitions (looks safe)
  2. CALL: use the tool normally (triggers mutation)
  3. AFTER: re-inspect (description has changed)

The audience sees the same tool name with different descriptions —
what you reviewed at install time is not what's running now.

Usage:
    python demos/23_mcp_rug_pull/demo.py
"""

import asyncio
import sys
from pathlib import Path

# Add scripts dir to path so we can import mcp_client
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from mcp_client import connect


def print_tools(tools):
    """Print tool definitions in a readable format."""
    for tool in tools.tools:
        print(f"  {tool.name}")
        desc_lines = (tool.description or "").strip().split("\n")
        for line in desc_lines:
            print(f"    {line}")
        print()


async def main():
    server_path = str(Path(__file__).parent / "server.py")

    async with connect(server_path) as (session, server_info):
        name = server_info.name if server_info else "server"

        # Phase 1: Inspect initial tools
        print(f"Connected to {name}")
        print()
        print("=" * 60)
        print("PHASE 1: BEFORE — initial tool definitions")
        print("=" * 60)
        tools_before = await session.list_tools()
        print_tools(tools_before)

        # Phase 2: Call the tool (triggers mutation)
        print("=" * 60)
        print("PHASE 2: CALL — using the tool normally")
        print("=" * 60)
        result = await session.call_tool("get_server_status", {"server_id": "SRV-1003"})
        output = result.content[0].text if result.content else ""
        print(f"  Result: {output}")
        print()

        # Phase 3: Re-fetch tools (now mutated)
        print("=" * 60)
        print("PHASE 3: AFTER — tool definitions re-fetched")
        print("=" * 60)
        tools_after = await session.list_tools()
        print_tools(tools_after)

        # Highlight the change
        desc_before = tools_before.tools[0].description or ""
        desc_after = tools_after.tools[0].description or ""
        if desc_before != desc_after:
            print("=" * 60)
            print("RESULT: Tool description CHANGED after first use.")
            print("The LLM now sees different instructions than what")
            print("you reviewed. The server mutated its own tools.")
            print("=" * 60)
        else:
            print("(No mutation detected — server may not have triggered)")


if __name__ == "__main__":
    asyncio.run(main())

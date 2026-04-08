#!/usr/bin/env python3
"""Call a tool function directly. No API, no model — just validation.

Useful for showing Pydantic validation in isolation.

Usage:
    python run_tool.py tools.py restart_server '{"server_id": "SRV-9999", "reason": "test"}'
    python run_tool.py tools.py list_servers '{"rack": 7}'
    python run_tool.py tools.py list_servers
"""

import json
import sys

from agent import load_tools_module

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python run_tool.py tools.py tool_name ['{json args}']", file=sys.stderr)
        sys.exit(1)

    tools = load_tools_module(sys.argv[1])
    tool_name = sys.argv[2]
    args = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}

    handler = tools.TOOL_HANDLERS[tool_name]
    try:
        result = handler(**args)
        print(result)
    except Exception as e:
        print(f"VALIDATION ERROR: {e}", file=sys.stderr)
        sys.exit(1)

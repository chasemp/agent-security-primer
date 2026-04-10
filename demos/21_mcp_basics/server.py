#!/usr/bin/env python3
"""A simple MCP server — one tool, no tricks.

This is what MCP looks like from the server side. The server
declares tools as JSON schemas. The client (your agent) discovers
them, injects them into the LLM's context, and routes tool calls
back here over the protocol.

The protocol is JSON-RPC over either:
  - stdio  (server is a subprocess, talks via stdin/stdout)
  - HTTP   (server listens on a port, talks via POST/SSE)

The messages are identical either way. Only the transport differs.

Run with stdio:   python server.py
Run with HTTP:    python server.py --http
"""

import json
import sys

from mcp.server import FastMCP

server = FastMCP(
    name="InfraServer",
    instructions="Server fleet status tool. Query server health by ID.",
)

# Simulated fleet data — same data as earlier agent demos.
FLEET = {
    "SRV-1001": {
        "server_id": "SRV-1001",
        "name": "payments-api",
        "status": "running",
        "cpu_pct": 42,
        "memory_pct": 67,
    },
    "SRV-1002": {
        "server_id": "SRV-1002",
        "name": "payments-db",
        "status": "running",
        "cpu_pct": 71,
        "memory_pct": 83,
    },
    "SRV-1003": {
        "server_id": "SRV-1003",
        "name": "cache-west",
        "status": "degraded",
        "cpu_pct": 95,
        "memory_pct": 91,
    },
}


@server.tool()
def get_server_status(server_id: str) -> str:
    """Check the current status of a server in the fleet.

    Returns JSON with server_id, name, status, cpu_pct, and memory_pct.
    """
    if server_id in FLEET:
        return json.dumps(FLEET[server_id])
    return json.dumps({"error": f"Server {server_id} not found in fleet"})


if __name__ == "__main__":
    if "--http" in sys.argv:
        server.run(transport="streamable-http")
    else:
        server.run(transport="stdio")

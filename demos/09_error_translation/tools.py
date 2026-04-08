"""Same broken tool as Demo 7, but with error translation.

The underlying service is still broken — connection pool exhausted,
fallback timed out. But instead of dumping the raw stack trace into
the context, we catch it and return a clean, structured error.

The model gets the same INFORMATION (service unavailable, try later)
without the NOISE (500 chars of Python traceback). The context stays
clean. The model makes a better decision with fewer tokens.

This is the bouncer on the OUTPUT side.
"""

import json


# The same raw error from Demo 7 — the underlying service is broken.
# In production, this comes from a try/except around the actual call.
_RAW_ERROR = """\
Traceback (most recent call last):
  File "/opt/services/infra-agent/src/handlers/server_ops.py", line 247, in handle_restart
    connection = pool.get_connection(timeout=30)
ConnectionError: Connection pool exhausted: 50/50 active
RuntimeError: Fallback connection failed: ETIMEOUT after 5000ms
OperationalError: Failed to restart SRV-1002: connection pool exhausted, fallback timed out
Server management API returned HTTP 503 Service Unavailable"""


def _translate_error(raw_error, server_id):
    """The one function that prevents context pollution.

    Takes a messy raw error and returns a clean, actionable message.
    The model gets what it needs to make a decision. Nothing more.
    """
    return json.dumps({
        "error": "service_unavailable",
        "server_id": server_id,
        "status": "management API is down",
        "retry": False,
        "action": "escalate to infrastructure team",
    })


def restart_server(server_id="", reason=""):
    """Same broken service, but errors are translated."""
    # In production: try/except around the real API call.
    # Here we just simulate the failure and translate.
    return _translate_error(_RAW_ERROR, server_id)


TOOL_DEFINITIONS = [
    {
        "name": "restart_server",
        "description": "Restart a server by ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "server_id": {
                    "type": "string",
                    "description": "Server ID to restart",
                },
                "reason": {
                    "type": "string",
                    "description": "Reason for restart",
                },
            },
            "required": ["server_id", "reason"],
        },
    },
]

TOOL_HANDLERS = {
    "restart_server": restart_server,
}

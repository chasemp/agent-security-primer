"""Broken tool for the death spiral demo.

This tool always fails with a raw, noisy error — a realistic stack
trace from a flaky service. No Pydantic validation, no input checking.
The model gets the raw dump back and tries to reason about it.

Each retry adds ~400 tokens of garbage to the context window. After
5 retries, that's 2000+ tokens of noise the model is reasoning on
top of. The context rots. The cost climbs. Nothing gets done.

This is what happens without a bouncer.
"""

import json


# No Pydantic. No validation. The tool accepts anything.
# In the real world, this is what happens when you wrap a flaky
# external service without error handling.

RAW_ERROR = """\
Traceback (most recent call last):
  File "/opt/services/infra-agent/src/handlers/server_ops.py", line 247, in handle_restart
    connection = pool.get_connection(timeout=30)
  File "/opt/services/infra-agent/src/db/pool.py", line 89, in get_connection
    raise ConnectionError(f"Connection pool exhausted: {self.active}/{self.max_size} active")
ConnectionError: Connection pool exhausted: 50/50 active

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/opt/services/infra-agent/src/handlers/server_ops.py", line 251, in handle_restart
    fallback = self._get_fallback_connection(server_id)
  File "/opt/services/infra-agent/src/handlers/server_ops.py", line 198, in _get_fallback_connection
    raise RuntimeError(f"Fallback connection failed: ETIMEOUT after 5000ms to {self.endpoint}")
RuntimeError: Fallback connection failed: ETIMEOUT after 5000ms to internal-mgmt-api.prod.svc.cluster.local:8443

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/opt/services/infra-agent/src/main.py", line 52, in process_action
    result = handler.execute(action)
  File "/opt/services/infra-agent/src/handlers/server_ops.py", line 255, in handle_restart
    raise OperationalError(f"Failed to restart {server_id}: connection pool exhausted, fallback timed out") from e
OperationalError: Failed to restart SRV-1002: connection pool exhausted, fallback timed out

Server management API returned HTTP 503 Service Unavailable
X-Request-Id: req_7f3a2b1c-9d4e-4a8f-b5c6-2e1d0f9a8b7c
Timestamp: 2026-03-28T14:32:47.123Z
"""


def restart_server(server_id="", reason=""):
    """Always fails. Returns the raw error dump."""
    return json.dumps({
        "error": True,
        "message": f"restart_server({server_id}) failed",
        "details": RAW_ERROR,
    })


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

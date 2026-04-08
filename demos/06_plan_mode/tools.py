"""Scoped tools for server operations.

These tools are narrow by design. The model can list servers and restart
them — nothing else. Pydantic validates inputs at the boundary. If the
model fabricates a server ID, the validation catches it before any
action is taken.

This is the "Bouncer" pattern: validate at the door, not after the fact.
"""

import json
import re

from pydantic import BaseModel, field_validator


# --- The real inventory. The model doesn't have this — it has to use
# --- the list_servers tool to look it up.

INVENTORY = {
    "SRV-1001": {"name": "auth-primary", "rack": 3, "status": "running"},
    "SRV-1002": {"name": "payments-db", "rack": 7, "status": "running"},
    "SRV-1003": {"name": "cache-west", "rack": 7, "status": "degraded"},
    "SRV-1004": {"name": "api-gateway", "rack": 1, "status": "running"},
    "SRV-1005": {"name": "metrics-collector", "rack": 5, "status": "running"},
}


# --- Pydantic models for input validation ---

class ListServersInput(BaseModel):
    rack: int | None = None


class RestartServerInput(BaseModel):
    server_id: str
    reason: str

    @field_validator("server_id")
    @classmethod
    def must_match_format(cls, v):
        if not re.match(r"^SRV-\d{4}$", v):
            raise ValueError(f"'{v}' does not match SRV-#### format")
        return v

    @field_validator("server_id")
    @classmethod
    def must_exist_in_inventory(cls, v):
        if v not in INVENTORY:
            raise ValueError(
                f"Server {v} not found in inventory. "
                f"Use list_servers to find valid IDs."
            )
        return v


# --- Tool handlers ---

def list_servers(rack=None):
    """List servers, optionally filtered by rack number."""
    validated = ListServersInput(rack=rack)
    if validated.rack is not None:
        filtered = {k: v for k, v in INVENTORY.items() if v["rack"] == validated.rack}
    else:
        filtered = INVENTORY
    return json.dumps(filtered, indent=2)


def restart_server(server_id, reason):
    """Restart a server. Pydantic validates the ID before any action."""
    validated = RestartServerInput(server_id=server_id, reason=reason)
    server = INVENTORY[validated.server_id]
    return json.dumps({
        "success": True,
        "server_id": validated.server_id,
        "server_name": server["name"],
        "previous_status": server["status"],
        "action": "restart initiated",
        "audit_reason": validated.reason,
    })


# --- Tool definitions (sent to the API) ---

TOOL_DEFINITIONS = [
    {
        "name": "list_servers",
        "description": "List servers in the inventory, optionally filtered by rack number.",
        "input_schema": ListServersInput.model_json_schema(),
    },
    {
        "name": "restart_server",
        "description": "Restart a server by ID. The server must exist in the active inventory.",
        "input_schema": RestartServerInput.model_json_schema(),
    },
]

TOOL_HANDLERS = {
    "list_servers": list_servers,
    "restart_server": restart_server,
}

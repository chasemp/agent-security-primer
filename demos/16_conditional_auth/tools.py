"""Tools with conditional authorization via Pydantic model_validator.

@field_validator checks individual fields: "Is this server ID valid?"
@model_validator checks relationships BETWEEN fields: "If the action
is delete, is supervisor_approved set to true?"

The model can't skip the approval step. It's not a prompt instruction
the model might ignore. It's Python code that runs BEFORE the tool
executes. The model has to set supervisor_approved=True to get past
validation, and your code can verify that approval is real.
"""

import json
import re

from pydantic import BaseModel, field_validator, model_validator


INVENTORY = {
    "SRV-1001": {"name": "auth-primary", "rack": 3, "status": "running"},
    "SRV-1002": {"name": "payments-db", "rack": 7, "status": "running"},
    "SRV-1003": {"name": "cache-west", "rack": 7, "status": "degraded"},
    "SRV-1004": {"name": "api-gateway", "rack": 1, "status": "running"},
    "SRV-1005": {"name": "metrics-collector", "rack": 5, "status": "running"},
}


class ServerActionInput(BaseModel):
    server_id: str
    action: str  # "restart", "stop", "start", "delete"
    reason: str
    supervisor_approved: bool = False

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
            raise ValueError(f"Server {v} not found in inventory.")
        return v

    @model_validator(mode="after")
    def destructive_actions_require_approval(self):
        """This is the authorization gate. Delete is destructive —
        it requires supervisor_approved=True. The model can't skip
        this by rephrasing its request or being persuasive. It's
        Python, not a prompt."""
        if self.action == "delete" and not self.supervisor_approved:
            raise ValueError(
                f"Action '{self.action}' on {self.server_id} requires "
                f"supervisor_approved=True. This is a destructive action."
            )
        return self


class ListServersInput(BaseModel):
    rack: int | None = None


def list_servers(rack=None):
    validated = ListServersInput(rack=rack)
    if validated.rack is not None:
        filtered = {k: v for k, v in INVENTORY.items() if v["rack"] == validated.rack}
    else:
        filtered = INVENTORY
    return json.dumps(filtered, indent=2)


def server_action(server_id, action, reason, supervisor_approved=False):
    """Execute a server action. Pydantic validates everything first."""
    validated = ServerActionInput(
        server_id=server_id, action=action,
        reason=reason, supervisor_approved=supervisor_approved,
    )
    server = INVENTORY[validated.server_id]
    return json.dumps({
        "success": True,
        "server_id": validated.server_id,
        "server_name": server["name"],
        "action": validated.action,
        "supervisor_approved": validated.supervisor_approved,
        "audit_reason": validated.reason,
    })


TOOL_DEFINITIONS = [
    {
        "name": "list_servers",
        "description": "List servers in the inventory.",
        "input_schema": ListServersInput.model_json_schema(),
    },
    {
        "name": "server_action",
        "description": "Perform an action on a server (restart, stop, start, delete). Delete requires supervisor_approved=True.",
        "input_schema": ServerActionInput.model_json_schema(),
    },
]

TOOL_HANDLERS = {
    "list_servers": list_servers,
    "server_action": server_action,
}
